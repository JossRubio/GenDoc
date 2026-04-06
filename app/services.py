"""
services.py — Business logic layer.

The main entry point is ``generate_documentation_stream()``, a generator
that yields SSE-ready event dicts as work progresses.  Routes consume it
via Flask's ``stream_with_context``.
"""

from __future__ import annotations

import os
import tkinter as tk
from pathlib import Path
from tkinter import filedialog

from . import md_to_docx
from .generators import DEFAULT_DOC_TYPE, get_generator
from .repo_reader import scan


# ── SSE event constructors ────────────────────────────────────────────

def _log(message: str, level: str = "info") -> dict:
    return {"type": "log", "message": message, "level": level}


def _progress(pct: int) -> dict:
    return {"type": "progress", "pct": pct}


def _done(markdown: str, output_path: str) -> dict:
    return {"type": "done", "markdown": markdown, "output_path": output_path}


def _ready(output_path: str, filename: str) -> dict:
    return {"type": "ready", "output_path": output_path, "filename": filename}


def _error(message: str) -> dict:
    return {"type": "error", "message": message}


# ── Dialog helpers ────────────────────────────────────────────────────

def _get_tk_root():
    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    return root


def browse_folder() -> str | None:
    root = _get_tk_root()
    path = filedialog.askdirectory(title="Seleccionar repositorio")
    root.destroy()
    return path or None


def browse_file() -> str | None:
    root = _get_tk_root()
    path = filedialog.askopenfilename(
        title="Seleccionar plantilla",
        filetypes=[
            ("Todos los archivos", "*.*"),
            ("Texto", "*.txt"),
            ("Markdown", "*.md"),
            ("Word", "*.docx"),
            ("PDF", "*.pdf"),
            ("PowerPoint", "*.pptx"),
        ],
    )
    root.destroy()
    return path or None


# ── Template section extractor ────────────────────────────────────────

def extract_template_sections(template_path: str) -> tuple[list[str], str | None]:
    """
    Read *template_path* and return a list of detected section headings.

    Returns (sections, error_message).  On success error_message is None.
    Sections are returned in document order; duplicates are removed while
    preserving order.

    Supported formats
    -----------------
    .md / .txt  — Markdown headings (lines starting with one or more '#')
    .docx       — Paragraphs whose Word style name begins with "Heading"
    .pdf        — Lines that match a heading pattern extracted via pypdf
    .pptx       — Slide title placeholder text extracted via python-pptx
    """
    p = Path(template_path)

    if not p.exists() or not p.is_file():
        return [], f"No se encontró el archivo: {template_path}"

    ext = p.suffix.lower()

    if ext == ".docx":
        try:
            from docx import Document as _Document
            wdoc = _Document(str(p))
            seen: list[str] = []
            for para in wdoc.paragraphs:
                style_name = (para.style.name or "").lower()
                text = para.text.strip()
                if style_name.startswith("heading") and text and text not in seen:
                    seen.append(text)
            return seen, None
        except Exception as exc:
            return [], f"No se pudo leer el archivo .docx: {exc}"

    if ext == ".pptx":
        try:
            from pptx import Presentation as _Prs
            from pptx.enum.shapes import PP_PLACEHOLDER
            prs  = _Prs(str(p))
            seen_set: set[str] = set()
            sections: list[str] = []
            for slide in prs.slides:
                for shape in slide.placeholders:
                    ph_type = shape.placeholder_format.type
                    if ph_type in (PP_PLACEHOLDER.TITLE, PP_PLACEHOLDER.CENTER_TITLE):
                        title = shape.text.strip()
                        if title and title not in seen_set:
                            seen_set.add(title)
                            sections.append(title)
                        break
            return sections, None
        except ImportError:
            return [], "python-pptx no está instalado. Ejecuta: pip install python-pptx"
        except Exception as exc:
            return [], f"No se pudo leer el archivo .pptx: {exc}"

    if ext == ".pdf":
        try:
            from pypdf import PdfReader
            reader   = PdfReader(str(p))
            raw_text = "\n".join(
                (page.extract_text() or "") for page in reader.pages
            )
        except ImportError:
            return [], "pypdf no está instalado. Ejecuta: pip install pypdf"
        except Exception as exc:
            return [], f"No se pudo leer el archivo .pdf: {exc}"

        import re as _re
        heading_re = _re.compile(r"^#{1,4}\s+(.+)", _re.MULTILINE)
        seen_set_pdf: set[str] = set()
        sections_pdf: list[str] = []
        for m in heading_re.finditer(raw_text):
            title = m.group(1).strip()
            if title and title not in seen_set_pdf:
                seen_set_pdf.add(title)
                sections_pdf.append(title)

        # If no Markdown headings found, fall back to ALL-CAPS short lines as headings
        if not sections_pdf:
            for line in raw_text.splitlines():
                stripped = line.strip()
                if stripped and stripped.isupper() and 3 <= len(stripped) <= 80:
                    if stripped not in seen_set_pdf:
                        seen_set_pdf.add(stripped)
                        sections_pdf.append(stripped)

        return sections_pdf, None

    # .md / .txt — detect Markdown headings
    try:
        text = p.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        return [], f"No se pudo leer el archivo: {exc}"

    import re
    heading_re = re.compile(r"^#{1,4}\s+(.+)", re.MULTILINE)
    seen_set_md: set[str] = set()
    sections_md: list[str] = []
    for m in heading_re.finditer(text):
        title = m.group(1).strip()
        if title and title not in seen_set_md:
            seen_set_md.add(title)
            sections_md.append(title)

    return sections_md, None


# ── Template reader ───────────────────────────────────────────────────

def _read_template(template_path: str) -> tuple[str | None, str | None]:
    """
    Read the template file and return (content, error_message).
    content is None when the file cannot be used; error_message explains why.
    """
    p = Path(template_path)

    if not p.exists():
        return None, f"El archivo de plantilla ya no existe: {template_path}"

    if not p.is_file():
        return None, f"La ruta de plantilla no apunta a un archivo: {template_path}"

    ext = p.suffix.lower()
    if ext == ".docx":
        return None, (
            "Las plantillas .docx no se pueden leer como texto plano todavía. "
            "Se usará la estructura predefinida."
        )

    try:
        content = p.read_text(encoding="utf-8", errors="strict")
        return content, None
    except UnicodeDecodeError:
        return None, (
            "La plantilla contiene caracteres que no se pueden leer como UTF-8. "
            "Se usará la estructura predefinida."
        )
    except PermissionError:
        return None, (
            f"Sin permisos para leer el archivo de plantilla: {template_path}. "
            "Se usará la estructura predefinida."
        )
    except OSError as exc:
        return None, (
            f"No se pudo leer el archivo de plantilla ({exc}). "
            "Se usará la estructura predefinida."
        )


# ── Main streaming generator ──────────────────────────────────────────

def generate_documentation_stream(
    repo_path: str,
    template_path: str | None = None,
    doc_type: str = DEFAULT_DOC_TYPE,
    primary_color: str | None = None,
    secondary_color: str | None = None,
    locked_sections: list[str] | None = None,
    api_key_override: str | None = None,
    model_override: str | None = None,
    provider_override: str | None = None,
):
    """
    Generator — yields SSE event dicts as work progresses.

    Sequence of events:
        log       — a line to display in the UI log area
        progress  — update the progress bar (0-100)
        done      — generation complete; carries markdown + output_path
        error     — fatal error; generation stops after this event
    """
    # Top-level guard: catch any bug we didn't anticipate so the stream
    # always closes cleanly instead of leaving the browser hanging.
    try:
        yield from _run(repo_path, template_path, doc_type, primary_color,
                        secondary_color, locked_sections,
                        api_key_override, model_override, provider_override)
    except Exception as exc:
        yield _error(
            f"Error interno inesperado: {exc}. "
            "Por favor reporta este problema."
        )


def _run(repo_path: str, template_path: str | None, doc_type: str,
         primary_color: str | None, secondary_color: str | None,
         locked_sections: list[str] | None = None,
         api_key_override: str | None = None,
         model_override: str | None = None,
         provider_override: str | None = None):
    """Inner generator — all expected errors are handled here."""

    # ── 1. Validate inputs ───────────────────────────────────────────
    if not repo_path or not repo_path.strip():
        yield _error("No se especificó ningún repositorio.")
        return

    try:
        generator = get_generator(doc_type)
    except ValueError as exc:
        yield _error(f"Tipo de documento inválido: {exc}")
        return

    yield _log(f"Tipo de documento: {generator.DISPLAY_NAME}")
    yield _progress(5)

    # ── 2. Scan repository ───────────────────────────────────────────
    yield _log(f"Analizando repositorio: {repo_path}")

    try:
        repo_scan = scan(repo_path)
    except ValueError as exc:
        yield _error(f"No se pudo leer el repositorio. {exc}")
        return
    except Exception as exc:
        yield _error(
            f"Error inesperado al escanear el repositorio: {exc}"
        )
        return

    if repo_scan.total_files == 0:
        yield _error(
            "No se encontraron archivos de código fuente en el repositorio. "
            "Verifica que la carpeta seleccionada sea la raíz del proyecto y "
            "que contenga archivos con extensiones reconocidas (.py, .js, .ts, etc.)."
        )
        return

    yield _log(f"Archivos encontrados ({repo_scan.total_files}):")
    for f in repo_scan.files:
        yield _log(f"  \u2192 {f.relative_path}  ({f.extension})")

    if repo_scan.skipped:
        yield _log(
            f"  {len(repo_scan.skipped)} archivo(s) omitido(s) "
            "(sin permisos de lectura o demasiado grandes).",
            level="warn",
        )

    size_kb = repo_scan.total_bytes / 1024
    yield _log(
        f"Total: {repo_scan.total_files} archivo"
        f"{'s' if repo_scan.total_files != 1 else ''} | {size_kb:.1f} KB"
    )
    yield _progress(20)

    # ── 3. Load template ─────────────────────────────────────────────
    template_content: str | None = None
    if template_path:
        yield _log(f"Cargando plantilla: {template_path}")
        template_content, err_msg = _read_template(template_path)
        if err_msg:
            # Template errors are non-fatal: warn and continue without it
            yield _log(err_msg, level="warn")
        else:
            yield _log("Plantilla cargada correctamente.", level="success")

    yield _progress(30)

    # ── 4. Generate Markdown via LLM ─────────────────────────────────
    try:
        repo_name = Path(repo_path).resolve().name
    except OSError:
        repo_name = Path(repo_path).name

    active_provider = (provider_override or "").strip() or "google"
    active_model    = (model_override or "").strip() or os.getenv("LLM_MODEL", "gemini-3-flash-preview").strip()
    yield _log(f"LLM: {active_provider} / {active_model}")
    yield _progress(40)

    yield _log("Construyendo prompt...")
    yield _log("Generando documentación. Esto puede tardar unos segundos...")

    try:
        markdown = generator.generate(
            repo_scan, template_content, locked_sections,
            api_key_override=api_key_override,
            model_override=model_override,
            provider_override=provider_override,
        )
    except ValueError as exc:
        yield _error(f"Error de configuración: {exc}")
        return
    except RuntimeError as exc:
        yield _error(f"Error al generar la documentación: {exc}")
        return
    except Exception as exc:
        yield _error(f"Error inesperado al llamar al modelo: {exc}")
        return

    if not markdown or not markdown.strip():
        yield _error(
            "El modelo devolvió una respuesta vacía. "
            "Intenta de nuevo o revisa que el repositorio tenga contenido legible."
        )
        return

    yield _progress(90)

    # ── 5. Resolve output format + path ─────────────────────────────
    output_fmt = "docx"
    if template_path:
        _tpl_ext = Path(template_path).suffix.lower()
        if _tpl_ext == ".pdf":
            output_fmt = "pdf"
        elif _tpl_ext == ".pptx":
            output_fmt = "pptx"

    output_dir = (os.getenv("OUTPUT_DIR") or "").strip() or repo_path

    try:
        output_path = str(generator.output_path(repo_name, output_dir, fmt=output_fmt))
    except Exception as exc:
        yield _error(f"No se pudo determinar la ruta de salida: {exc}")
        return

    _fmt_labels = {"docx": "Word (.docx)", "pdf": "PDF (.pdf)", "pptx": "PowerPoint (.pptx)"}
    yield _log(
        f"Contenido generado. Convirtiendo a {_fmt_labels.get(output_fmt, output_fmt)}...",
        level="success",
    )
    yield _progress(93)

    # ── 6. Convert Markdown → output format ──────────────────────────
    import concurrent.futures as _cf

    _CONVERT_TIMEOUT = 60  # seconds

    kwargs: dict = {"doc_type": doc_type or "technical"}
    if primary_color:
        kwargs["primary_color"] = primary_color
    if secondary_color:
        kwargs["secondary_color"] = secondary_color

    if output_fmt == "pptx":
        from . import md_to_pptx
        _pptx_kwargs = {k: v for k, v in kwargs.items() if k in ("primary_color", "secondary_color")}
        _converter = lambda: md_to_pptx.convert(markdown, output_path, **_pptx_kwargs)  # noqa: E731
    elif output_fmt == "pdf":
        from . import md_to_pdf
        _converter = lambda: md_to_pdf.convert(markdown, output_path, **kwargs)  # noqa: E731
    else:
        _converter = lambda: md_to_docx.convert(markdown, output_path, **kwargs)  # noqa: E731

    try:
        with _cf.ThreadPoolExecutor(max_workers=1) as _pool:
            _future = _pool.submit(_converter)
            try:
                final_path = _future.result(timeout=_CONVERT_TIMEOUT)
            except _cf.TimeoutError:
                _future.cancel()
                yield _error(
                    f"La conversión superó el límite de {_CONVERT_TIMEOUT} segundos. "
                    "Intenta de nuevo o verifica que el repositorio no sea demasiado grande."
                )
                return
    except RuntimeError as exc:
        yield _error(f"Error al crear el documento: {exc}")
        return
    except Exception as exc:
        yield _error(f"Error inesperado al exportar el documento: {exc}")
        return

    filename = Path(output_path).name
    yield _log(f"Documento listo: {filename}", level="success")
    yield _progress(100)
    yield _ready(output_path=str(final_path), filename=filename)
