"""
md_to_docx.py — Converts a Markdown string to a Word (.docx) document.

Public API
----------
convert(markdown, output_path) -> Path
    Parse *markdown* and write a styled .docx to *output_path*.
    Returns the resolved Path of the written file.

Supported Markdown elements
---------------------------
  # H1          → Cover page title (first occurrence) or Heading 1
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

Document structure
------------------
  Cover page    → title centred (vert + horiz), subtitle, month/year, rights
  Header        → logo placeholder (left) + author text (right) on all body pages
  Footer        → project title · "Todos los derechos reservados, Mes Año"

Raises
------
RuntimeError — if the output directory does not exist or cannot be written.
"""

from __future__ import annotations

import copy
import io
import re
import struct
import zlib
from datetime import datetime
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
_COLOR_GRAY      = RGBColor(0x60, 0x60, 0x60)   # mid grey


# ── Localisation ──────────────────────────────────────────────────────

_MONTHS_ES = [
    "enero", "febrero", "marzo", "abril", "mayo", "junio",
    "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
]


def _month_year_es() -> str:
    now = datetime.now()
    return f"{_MONTHS_ES[now.month - 1].capitalize()} {now.year}"


# ── Placeholder logo PNG ──────────────────────────────────────────────

def _make_placeholder_png(width: int = 120, height: int = 50) -> bytes:
    """
    Build a minimal solid-colour PNG in memory (no external dependencies).
    Returns raw PNG bytes representing a light steel-blue rectangle.
    """
    def chunk(tag: bytes, data: bytes) -> bytes:
        crc = zlib.crc32(tag + data) & 0xFFFFFFFF
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", crc)

    signature = b"\x89PNG\r\n\x1a\n"
    ihdr      = chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
    row       = bytes([210, 215, 230] * width)           # light steel-blue pixel (RGB)
    raw       = b"".join(b"\x00" + row for _ in range(height))
    idat      = chunk(b"IDAT", zlib.compress(raw, 6))
    iend      = chunk(b"IEND", b"")
    return signature + ihdr + idat + iend


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


def _remove_table_borders(table) -> None:
    """Strip all visible borders from a table (used for layout tables)."""
    tblPr = table._tbl.get_or_add_tblPr()
    for old in tblPr.findall(qn("w:tblBorders")):
        tblPr.remove(old)
    borders = OxmlElement("w:tblBorders")
    for side in ("top", "left", "bottom", "right", "insideH", "insideV"):
        el = OxmlElement(f"w:{side}")
        el.set(qn("w:val"),   "none")
        el.set(qn("w:sz"),    "0")
        el.set(qn("w:space"), "0")
        el.set(qn("w:color"), "auto")
        borders.append(el)
    tblPr.append(borders)


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


# ── Cover page ────────────────────────────────────────────────────────

def _add_cover_page(doc: Document, title: str) -> None:
    """
    Add a cover page as section 1 with vertical centre alignment,
    followed by a 'next page' section break.  The main body occupies
    section 2 (the document-level sectPr).

    Cover layout:
        [vertically centred on the page]
        <title>  — large, bold, indigo
        Draft de documentación realizada por GenDoc  — smaller, italic
        <Mes Año>
        Todos los derechos reservados
    """
    month_year = _month_year_es()

    # Read the document-level page size + margins BEFORE adding the section
    # break paragraph so we can replicate them in the cover section.
    body_sectPr = doc.element.body.sectPr
    orig_pgSz   = body_sectPr.find(qn("w:pgSz")) if body_sectPr is not None else None
    orig_pgMar  = body_sectPr.find(qn("w:pgMar")) if body_sectPr is not None else None

    # ── Title ────────────────────────────────────────────────────────
    title_para = doc.add_paragraph()
    title_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
    title_para.paragraph_format.space_before = Pt(0)
    title_para.paragraph_format.space_after  = Pt(20)
    run = title_para.add_run(title)
    run.font.size      = Pt(36)
    run.font.bold      = True
    run.font.color.rgb = _COLOR_HEADING1

    # ── Subtitle ─────────────────────────────────────────────────────
    sub_para = doc.add_paragraph()
    sub_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
    sub_para.paragraph_format.space_before = Pt(0)
    sub_para.paragraph_format.space_after  = Pt(30)
    sub_run = sub_para.add_run("Draft de documentación realizada por GenDoc")
    sub_run.font.size      = Pt(14)
    sub_run.font.italic    = True
    sub_run.font.color.rgb = _COLOR_HEADING2

    # ── Month / year ─────────────────────────────────────────────────
    date_para = doc.add_paragraph()
    date_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
    date_para.paragraph_format.space_before = Pt(0)
    date_para.paragraph_format.space_after  = Pt(4)
    date_run = date_para.add_run(month_year)
    date_run.font.size      = Pt(10)
    date_run.font.color.rgb = _COLOR_GRAY

    # ── Rights notice ────────────────────────────────────────────────
    rights_para = doc.add_paragraph()
    rights_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
    rights_para.paragraph_format.space_before = Pt(0)
    rights_para.paragraph_format.space_after  = Pt(0)
    rights_run = rights_para.add_run("Todos los derechos reservados")
    rights_run.font.size      = Pt(10)
    rights_run.font.color.rgb = _COLOR_GRAY

    # ── Section break paragraph ───────────────────────────────────────
    # This paragraph's <w:sectPr> defines section 1 (cover).
    # Everything after it belongs to section 2 (main body).
    sep_para = doc.add_paragraph()
    sep_para.paragraph_format.space_before = Pt(0)
    sep_para.paragraph_format.space_after  = Pt(0)

    pPr    = sep_para._p.get_or_add_pPr()
    sectPr = OxmlElement("w:sectPr")

    # Break type: start a new page
    type_el = OxmlElement("w:type")
    type_el.set(qn("w:val"), "nextPage")
    sectPr.append(type_el)

    # Copy page size from main section (fallback to US Letter)
    if orig_pgSz is not None:
        sectPr.append(copy.deepcopy(orig_pgSz))
    else:
        pgSz = OxmlElement("w:pgSz")
        pgSz.set(qn("w:w"), "12240")
        pgSz.set(qn("w:h"), "15840")
        sectPr.append(pgSz)

    # Copy page margins from main section
    if orig_pgMar is not None:
        sectPr.append(copy.deepcopy(orig_pgMar))

    # Vertical alignment: centre — this is what centres the cover content
    vAlign = OxmlElement("w:vAlign")
    vAlign.set(qn("w:val"), "center")
    sectPr.append(vAlign)

    pPr.append(sectPr)


# ── Header & footer ───────────────────────────────────────────────────

def _setup_header_footer(doc: Document, project_title: str) -> None:
    """
    Configure header and footer on the last (main body) section.

    Header layout:
        [logo placeholder image]   Autor(a):
                                   Draft generado por GenDoc

    Footer layout (centred):
        <project title>  ·  Todos los derechos reservados, Mes Año
    """
    month_year = _month_year_es()
    section    = doc.sections[-1]

    # ── Header ───────────────────────────────────────────────────────
    header  = section.header
    p0      = header.paragraphs[0]
    p0.clear()
    p0.paragraph_format.space_before = Pt(0)
    p0.paragraph_format.space_after  = Pt(2)

    # Left: placeholder logo image (inline run)
    img_run = p0.add_run()
    img_run.add_picture(io.BytesIO(_make_placeholder_png(120, 50)), width=Inches(1.05))

    # Spacer between image and text
    sp = p0.add_run("  ")
    sp.font.size = Pt(10)

    # Author label on the same line as the image
    r_author = p0.add_run("Autor(a):")
    r_author.font.size      = Pt(9)
    r_author.font.bold      = True
    r_author.font.color.rgb = _COLOR_GRAY

    # Second line: "Draft generado por GenDoc" — indented to align with text above
    p1 = header.add_paragraph()
    p1.paragraph_format.left_indent  = Inches(1.2)
    p1.paragraph_format.space_before = Pt(0)
    p1.paragraph_format.space_after  = Pt(0)
    r_draft = p1.add_run("Draft generado por GenDoc")
    r_draft.font.size      = Pt(8)
    r_draft.font.italic    = True
    r_draft.font.color.rgb = _COLOR_GRAY

    # ── Footer ───────────────────────────────────────────────────────
    footer   = section.footer
    fp       = footer.paragraphs[0]
    fp.alignment = WD_ALIGN_PARAGRAPH.CENTER

    r_title = fp.add_run(project_title)
    r_title.font.bold      = True
    r_title.font.size      = Pt(9)
    r_title.font.color.rgb = _COLOR_HEADING1

    r_sep = fp.add_run("   ·   ")
    r_sep.font.size      = Pt(9)
    r_sep.font.color.rgb = _COLOR_GRAY

    r_rights = fp.add_run(f"Todos los derechos reservados, {month_year}")
    r_rights.font.size      = Pt(9)
    r_rights.font.color.rgb = _COLOR_GRAY


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

    doc = Document()

    # ── Configure default body font ──────────────────────────────────
    style = doc.styles["Normal"]
    style.font.name = "Calibri"
    style.font.size = Pt(11)

    lines = markdown.splitlines()
    n     = len(lines)

    # ── Find first H1 — used as the cover page title ─────────────────
    title          = None
    title_line_idx = -1
    for idx, line in enumerate(lines):
        m = re.match(r"^#\s+(.*)", line)
        if m:
            title          = m.group(1).strip()
            title_line_idx = idx
            break

    if not title:
        # Fallback: derive from the output filename
        title = out.stem.replace("_", " ").title()

    # ── Cover page (section 1, vAlign=center) ────────────────────────
    _add_cover_page(doc, title)

    # ── Header + footer on main section (section 2) ──────────────────
    _setup_header_footer(doc, title)

    # ── Process markdown body ────────────────────────────────────────
    # first_h1 starts pre-filled: the title was consumed by the cover page,
    # so any remaining H1s should render as Heading 1 (not Title style).
    first_h1 = [True]
    i        = 0

    while i < n:
        line = lines[i]

        # Skip the line already consumed for the cover title
        if i == title_line_idx:
            i += 1
            continue

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
            table_rows: list[str] = []
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
