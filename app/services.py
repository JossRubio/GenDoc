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

from . import ai_service
from .generators import DEFAULT_DOC_TYPE, get_generator
from .repo_reader import scan


# ── SSE event constructors ────────────────────────────────────────────

def _log(message: str, level: str = "info") -> dict:
    return {"type": "log", "message": message, "level": level}


def _progress(pct: int) -> dict:
    return {"type": "progress", "pct": pct}


def _done(markdown: str, output_path: str) -> dict:
    return {"type": "done", "markdown": markdown, "output_path": output_path}


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
        ],
    )
    root.destroy()
    return path or None


# ── Template reader ───────────────────────────────────────────────────

def _read_template(template_path: str) -> str | None:
    """Return the template's text content, or None if it can't be decoded."""
    ext = Path(template_path).suffix.lower()
    if ext == ".docx":
        return None  # docx export support comes in the next phase
    try:
        return Path(template_path).read_text(encoding="utf-8", errors="strict")
    except (UnicodeDecodeError, OSError):
        return None


# ── Main streaming generator ──────────────────────────────────────────

def generate_documentation_stream(
    repo_path: str,
    template_path: str | None = None,
    doc_type: str = DEFAULT_DOC_TYPE,
):
    """
    Generator — yields SSE event dicts as work progresses.

    Sequence of events:
        log       — a line to display in the UI log area
        progress  — update the progress bar (0-100)
        done      — generation complete; carries markdown + output_path
        error     — fatal error; generation stops after this event
    """

    # ── 1. Validate inputs ───────────────────────────────────────────
    if not repo_path:
        yield _error("No se especificó ningún repositorio.")
        return

    try:
        generator = get_generator(doc_type)
    except ValueError as exc:
        yield _error(str(exc))
        return

    yield _log(f"Tipo de documento: {generator.DISPLAY_NAME}")
    yield _progress(5)

    # ── 2. Scan repository ───────────────────────────────────────────
    yield _log(f"Analizando repositorio: {repo_path}")

    try:
        repo_scan = scan(repo_path)
    except ValueError as exc:
        yield _error(str(exc))
        return

    if repo_scan.total_files == 0:
        yield _error("No se encontraron archivos de código fuente en el repositorio.")
        return

    yield _log(f"Archivos encontrados ({repo_scan.total_files}):")
    for f in repo_scan.files:
        yield _log(f"  \u2192 {f.relative_path}  ({f.extension})")

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
        template_content = _read_template(template_path)
        if template_content is None:
            yield _log(
                "La plantilla no pudo leerse como texto plano — "
                "se usará la estructura predefinida.",
                level="warn",
            )
        else:
            yield _log("Plantilla cargada correctamente.", level="success")

    yield _progress(30)

    # ── 4. Call LLM ──────────────────────────────────────────────────
    model_name = os.getenv("LLM_MODEL", "gemini-2.5-flash")
    yield _log("Construyendo prompt...")
    yield _progress(40)
    yield _log(f"Llamando al modelo {model_name}...")

    try:
        markdown = ai_service.generate_documentation(
            repo_scan, doc_type, template_content
        )
    except (ValueError, RuntimeError) as exc:
        yield _error(str(exc))
        return
    except Exception as exc:
        yield _error(f"Error inesperado al llamar al modelo: {exc}")
        return

    yield _progress(90)

    # ── 5. Resolve output path ───────────────────────────────────────
    repo_name = Path(repo_path).resolve().name
    output_dir = os.getenv("OUTPUT_DIR") or repo_path
    output_path = str(generator.output_path(repo_name, output_dir))

    yield _log("Documentación generada. Listo para exportar.", level="success")
    yield _progress(100)
    yield _done(markdown=markdown, output_path=output_path)
