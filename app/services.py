"""
services.py — Business logic layer.
All future document generation, analysis, and AI calls go here.
"""

import os
import tkinter as tk
from pathlib import Path
from tkinter import filedialog

from .generators import DEFAULT_DOC_TYPE, GENERATORS, get_generator
from .repo_reader import scan


def _get_tk_root():
    """Create a hidden Tk root window for dialogs."""
    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    return root


def browse_folder() -> str | None:
    """Open a native folder picker dialog and return the selected path."""
    root = _get_tk_root()
    path = filedialog.askdirectory(title="Seleccionar repositorio")
    root.destroy()
    return path or None


def browse_file() -> str | None:
    """Open a native file picker dialog and return the selected path."""
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


def generate_documentation(
    repo_path: str,
    template_path: str | None = None,
    doc_type: str = DEFAULT_DOC_TYPE,
) -> dict:
    """
    Phase 1: scan the repository and report found files.
    Returns a dict with keys: steps (list[str]), output_path (str | None), error (str | None).
    """
    steps: list[str] = []

    # ── 1. Validate inputs ───────────────────────────────────────────
    if not repo_path:
        return {"steps": ["Error: no se especificó ningún repositorio."], "error": "no_path"}

    try:
        generator = get_generator(doc_type)
    except ValueError as exc:
        return {"steps": [f"Error: {exc}"], "error": str(exc)}

    steps.append(f"Tipo de documento: {generator.DISPLAY_NAME}")
    steps.append(f"Analizando repositorio: {repo_path}")

    # ── 2. Scan ──────────────────────────────────────────────────────
    try:
        result = scan(repo_path)
    except ValueError as exc:
        steps.append(f"Error: {exc}")
        return {"steps": steps, "error": str(exc)}

    # ── 3. Build log lines ───────────────────────────────────────────
    if result.total_files == 0:
        steps.append("No se encontraron archivos de código fuente en el repositorio.")
        return {"steps": steps, "output_path": None}

    steps.append(f"Archivos encontrados ({result.total_files}):")
    for f in result.files:
        steps.append(f"  → {f.relative_path}  ({f.extension})")

    size_kb = result.total_bytes / 1024
    steps.append(
        f"Total: {result.total_files} archivo{'s' if result.total_files != 1 else ''}"
        f" | {size_kb:.1f} KB de código fuente"
    )

    if template_path:
        steps.append(f"Plantilla seleccionada: {template_path}")

    steps.append("Repositorio analizado. Listo para generar documentación.")

    # ── 4. Resolve output path ───────────────────────────────────────
    repo_name = Path(repo_path).resolve().name
    output_dir = os.getenv("OUTPUT_DIR") or repo_path
    output_path = str(generator.output_path(repo_name, output_dir))

    return {"steps": steps, "output_path": output_path, "error": None}
