"""
md_to_pdf.py — Convert a Markdown string to a PDF document.

Strategy
--------
1. Generate a styled .docx using md_to_docx.convert() into a temp file.
2. Convert the .docx to .pdf using docx2pdf (Windows COM / Word automation).
3. Delete the temp .docx and return the .pdf path.

Requirements
------------
- Microsoft Word must be installed (used by docx2pdf via pywin32 COM).

Raises
------
RuntimeError — Word not installed, conversion failed, or directory missing.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path


def convert(
    markdown: str,
    output_path: str | Path,
    *,
    doc_type:        str = "technical",
    primary_color:   str | None = None,
    secondary_color: str | None = None,
) -> Path:
    """
    Convert *markdown* to a PDF file at *output_path*.

    Returns the resolved Path of the written PDF.
    """
    from . import md_to_docx  # local import to avoid circular deps

    out = Path(output_path)
    if not out.parent.exists():
        raise RuntimeError(
            f"El directorio de salida no existe: {out.parent}."
        )

    # ── Step 1: generate .docx into a temp file ──────────────────────
    tmp_fd, tmp_docx = tempfile.mkstemp(suffix=".docx", dir=out.parent)
    os.close(tmp_fd)
    tmp_docx_path = Path(tmp_docx)

    kwargs: dict = {"doc_type": doc_type}
    if primary_color:
        kwargs["primary_color"]   = primary_color
    if secondary_color:
        kwargs["secondary_color"] = secondary_color

    try:
        md_to_docx.convert(markdown, tmp_docx_path, **kwargs)
    except Exception as exc:
        tmp_docx_path.unlink(missing_ok=True)
        raise RuntimeError(f"Error al generar el documento intermedio: {exc}") from exc

    # ── Step 2: convert .docx → .pdf via Word COM ────────────────────
    try:
        from docx2pdf import convert as _d2p
    except ImportError:
        tmp_docx_path.unlink(missing_ok=True)
        raise RuntimeError(
            "El paquete 'docx2pdf' no está instalado. "
            "Ejecuta: pip install docx2pdf"
        )

    try:
        _d2p(str(tmp_docx_path), str(out))
    except Exception as exc:
        tmp_docx_path.unlink(missing_ok=True)
        raise RuntimeError(
            f"No se pudo convertir a PDF: {exc}. "
            "Asegúrate de tener Microsoft Word instalado y que el archivo no esté abierto."
        ) from exc

    # ── Step 3: clean up temp .docx ──────────────────────────────────
    tmp_docx_path.unlink(missing_ok=True)

    return out.resolve()
