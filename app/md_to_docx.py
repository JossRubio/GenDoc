"""
md_to_docx.py — Converts a Markdown string to a Word (.docx) document.

Public API
----------
convert(markdown, output_path) -> Path
    Parse *markdown* and write a styled .docx to *output_path*.
    Returns the resolved Path of the written file.

Supported Markdown elements
---------------------------
  # H1          → Title style (once) then Heading 1
  ## H2         → Heading 2
  ### H3        → Heading 3
  #### H4+      → Heading 4
  Paragraph     → Normal
  - / * list    → List Bullet
  1. list       → List Number
  ``` code ```  → fenced code block → monospaced paragraph with shading
  | table |     → Word table with styled header row
  **bold**      → bold run
  *italic*      → italic run
  `inline code` → monospaced run
  blank lines   → paragraph separator (not extra blank paragraphs)

Raises
------
RuntimeError — if the output directory does not exist or cannot be written.
"""

from __future__ import annotations

import re
from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
from docx.shared import Pt, RGBColor, Inches


# ── Colour palette ────────────────────────────────────────────────────

_COLOR_HEADING1  = RGBColor(0x2D, 0x3A, 0x8C)   # dark indigo
_COLOR_HEADING2  = RGBColor(0x1E, 0x6A, 0xA3)   # steel blue
_COLOR_HEADING3  = RGBColor(0x28, 0x7A, 0x5F)   # teal
_COLOR_CODE_BG   = "F0F0F5"                      # light grey (hex, no #)
_COLOR_CODE_FONT = RGBColor(0x4B, 0x00, 0x82)   # indigo
_COLOR_TABLE_HDR = "4F46E5"                      # brand purple (hex, no #)


# ── Low-level XML helpers ─────────────────────────────────────────────

def _set_cell_bg(cell, hex_color: str) -> None:
    tc   = cell._tc
    tcPr = tc.get_or_add_tcPr()
    shd  = OxmlElement("w:shd")
    shd.set(qn("w:val"),   "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"),  hex_color)
    tcPr.append(shd)


def _set_para_shading(para, hex_color: str) -> None:
    pPr = para._p.get_or_add_pPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"),   "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"),  hex_color)
    pPr.append(shd)


# ── Inline markup parser ──────────────────────────────────────────────

# Matches: **bold**, *italic*, `code`, or plain text between them.
_INLINE_RE = re.compile(r"\*\*(.+?)\*\*|\*(.+?)\*|`([^`]+)`|([^*`]+)", re.DOTALL)


def _add_inline(para, text: str) -> None:
    """Add *text* to *para*, honouring **bold**, *italic*, and `code`."""
    for m in _INLINE_RE.finditer(text):
        bold_txt, italic_txt, code_txt, plain_txt = m.groups()
        if bold_txt is not None:
            run = para.add_run(bold_txt)
            run.bold = True
        elif italic_txt is not None:
            run = para.add_run(italic_txt)
            run.italic = True
        elif code_txt is not None:
            run = para.add_run(code_txt)
            run.font.name = "Courier New"
            run.font.size = Pt(9)
            run.font.color.rgb = _COLOR_CODE_FONT
        elif plain_txt is not None:
            para.add_run(plain_txt)


# ── Document styling helpers ──────────────────────────────────────────

def _heading(doc: Document, text: str, level: int, first_h1: list) -> None:
    """Add a heading paragraph with custom colour and size."""
    if level == 1 and not first_h1:
        # First H1 becomes the document Title style
        para = doc.add_paragraph(style="Title")
        para.clear()
        run = para.add_run(text)
        run.font.color.rgb = _COLOR_HEADING1
        run.font.size = Pt(26)
        first_h1.append(True)
        return

    style_map = {1: "Heading 1", 2: "Heading 2", 3: "Heading 3", 4: "Heading 4"}
    para  = doc.add_paragraph(style=style_map.get(level, "Heading 4"))
    para.clear()
    run   = para.add_run(text)
    color = {1: _COLOR_HEADING1, 2: _COLOR_HEADING2, 3: _COLOR_HEADING3}.get(
        level, _COLOR_HEADING3
    )
    run.font.color.rgb = color
    sizes  = {1: Pt(20), 2: Pt(16), 3: Pt(13), 4: Pt(11)}
    run.font.size = sizes.get(level, Pt(11))


def _code_block(doc: Document, lines: list[str]) -> None:
    """Add a shaded, monospaced code block."""
    for line in lines:
        para = doc.add_paragraph(style="Normal")
        _set_para_shading(para, _COLOR_CODE_BG)
        para.paragraph_format.left_indent  = Inches(0.3)
        para.paragraph_format.right_indent = Inches(0.3)
        para.paragraph_format.space_before = Pt(0)
        para.paragraph_format.space_after  = Pt(0)
        run = para.add_run(line)
        run.font.name = "Courier New"
        run.font.size = Pt(9)
        run.font.color.rgb = _COLOR_CODE_FONT


def _table_block(doc: Document, rows: list[str]) -> None:
    """
    Parse a Markdown table (list of raw pipe-delimited lines) and add
    a Word table with a styled header row.
    """
    def _split_row(line: str) -> list[str]:
        return [c.strip() for c in line.strip().strip("|").split("|")]

    # Filter out separator rows (e.g. |---|---|)
    data_rows = [r for r in rows if not re.match(r"^[\s|:\-]+$", r)]
    if not data_rows:
        return

    cols     = len(_split_row(data_rows[0]))
    tbl      = doc.add_table(rows=len(data_rows), cols=cols)
    tbl.style = "Table Grid"

    for r_idx, raw in enumerate(data_rows):
        cells = _split_row(raw)
        for c_idx, cell_text in enumerate(cells[:cols]):
            cell = tbl.cell(r_idx, c_idx)
            cell.text = ""
            para = cell.paragraphs[0]
            if r_idx == 0:
                _set_cell_bg(cell, _COLOR_TABLE_HDR)
                run = para.add_run(cell_text)
                run.bold = True
                run.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
            else:
                _add_inline(para, cell_text)

    doc.add_paragraph()  # spacing after table


# ── Main converter ────────────────────────────────────────────────────

def convert(markdown: str, output_path: str | Path) -> Path:
    """
    Convert *markdown* to a styled .docx and write it to *output_path*.

    Raises
    ------
    RuntimeError — if the parent directory does not exist or is not writable.
    """
    out = Path(output_path)
    if not out.parent.exists():
        raise RuntimeError(
            f"El directorio de salida no existe: {out.parent}. "
            "Crea la carpeta o cambia OUTPUT_DIR en .env."
        )
    if not out.parent.is_dir():
        raise RuntimeError(
            f"La ruta de salida no es una carpeta: {out.parent}."
        )

    doc      = Document()
    first_h1 = []   # mutable sentinel: empty = Title not yet used

    # ── Configure default body font ──────────────────────────────────
    style = doc.styles["Normal"]
    style.font.name = "Calibri"
    style.font.size = Pt(11)

    lines     = markdown.splitlines()
    i         = 0
    n         = len(lines)

    while i < n:
        line = lines[i]

        # ── Fenced code block ────────────────────────────────────────
        if line.startswith("```"):
            code_lines: list[str] = []
            i += 1
            while i < n and not lines[i].startswith("```"):
                code_lines.append(lines[i])
                i += 1
            _code_block(doc, code_lines)
            i += 1
            continue

        # ── Markdown table ───────────────────────────────────────────
        if "|" in line and line.strip().startswith("|"):
            table_rows = []
            while i < n and "|" in lines[i] and lines[i].strip().startswith("|"):
                table_rows.append(lines[i])
                i += 1
            _table_block(doc, table_rows)
            continue

        # ── Headings ─────────────────────────────────────────────────
        heading_m = re.match(r"^(#{1,4})\s+(.*)", line)
        if heading_m:
            level = len(heading_m.group(1))
            text  = heading_m.group(2).strip()
            _heading(doc, text, level, first_h1)
            i += 1
            continue

        # ── Unordered list ───────────────────────────────────────────
        if re.match(r"^\s*[-*]\s+", line):
            para = doc.add_paragraph(style="List Bullet")
            _add_inline(para, re.sub(r"^\s*[-*]\s+", "", line))
            i += 1
            continue

        # ── Ordered list ─────────────────────────────────────────────
        if re.match(r"^\s*\d+\.\s+", line):
            para = doc.add_paragraph(style="List Number")
            _add_inline(para, re.sub(r"^\s*\d+\.\s+", "", line))
            i += 1
            continue

        # ── Horizontal rule ──────────────────────────────────────────
        if re.match(r"^---+$", line.strip()):
            doc.add_paragraph()
            i += 1
            continue

        # ── Blank line → skip (paragraphs already spaced) ───────────
        if not line.strip():
            i += 1
            continue

        # ── Normal paragraph ─────────────────────────────────────────
        para = doc.add_paragraph(style="Normal")
        _add_inline(para, line)
        i += 1

    # ── Write file ───────────────────────────────────────────────────
    try:
        doc.save(str(out))
    except PermissionError:
        raise RuntimeError(
            f"Sin permisos para escribir en: {out}. "
            "Cierra el archivo si está abierto en Word e intenta de nuevo."
        )
    except OSError as exc:
        raise RuntimeError(
            f"No se pudo guardar el documento Word: {exc}"
        )

    return out
