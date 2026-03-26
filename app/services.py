"""
services.py — Business logic layer.
All future document generation, analysis, and AI calls go here.
"""

import tkinter as tk
from tkinter import filedialog


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


def generate_documentation(repo_path: str = None, template_path: str = None) -> dict:
    """
    Placeholder — will analyse the repository and produce a Word document.
    Returns a dict with keys: message, output_path, steps (list of log lines).
    """
    return {
        "message": "Funcionalidad pendiente de implementar",
        "output_path": None,
        "steps": ["Funcionalidad pendiente de implementar"],
    }
