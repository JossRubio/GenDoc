"""
md_to_docx.py — Converts a Markdown string to a Word (.docx) document.

Public API
----------
convert(markdown, output_path, *, primary_color, secondary_color) -> Path
    Parse *markdown* and write a styled .docx to *output_path*.
    Returns the resolved Path of the written file.

Colour roles
------------
  primary_color   → H1, H2, table header background, footer title
  secondary_color → H3+, inline/block code font, header text, footer separator

Supported Markdown elements
---------------------------
  # H1          → Cover page title (first) or Heading 1
  ## H2         → Heading 2
  ### H3        → Heading 3
  #### H4+      → Heading 4
  Paragraph     → Normal
  - / * list    → List Bullet
  1. list       → List Number
  ``` code ```  → fenced code block → monospaced paragraph with shading
  | table |     → Word table with styled header row (centred)
  **bold**      → bold run
  *italic*      → italic run
  `inline code` → monospaced run
  blank lines   → paragraph separator (not extra blank paragraphs)

Document structure
------------------
  Cover page    → title centred (vert + horiz), subtitle, month/year, rights
  Header        → placeholder logo (left) + "Autor(a):" / "Draft generado…" (right, vcentred)
  Footer        → project title · "Todos los derechos reservados, Mes Año" (left-aligned)
  Margins       → 1.27 cm on all sides (page + header/footer distance)

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
from docx.shared import Pt, RGBColor, Inches, Cm


# ── Colour defaults ───────────────────────────────────────────────────

_DEFAULT_PRIMARY   = "#2D3A8C"
_DEFAULT_SECONDARY = "#287A5F"

_COLOR_GRAY  = RGBColor(0x60, 0x60, 0x60)
_COLOR_WHITE = RGBColor(0xFF, 0xFF, 0xFF)
_COLOR_CODE_BG = "F0F0F5"


def _hex_to_rgb(hex_color: str) -> RGBColor:
    h = hex_color.lstrip("#")
    return RGBColor(int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))


def _hex_to_str(hex_color: str) -> str:
    """Return uppercase hex without '#', e.g. '2D3A8C'."""
    return hex_color.lstrip("#").upper()


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
    """Build a minimal solid-colour PNG in memory (no Pillow needed)."""
    def chunk(tag: bytes, data: bytes) -> bytes:
        crc = zlib.crc32(tag + data) & 0xFFFFFFFF
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", crc)

    signature = b"\x89PNG\r\n\x1a\n"
    ihdr = chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
    row  = bytes([210, 215, 230] * width)          # light steel-blue pixel (RGB)
    raw  = b"".join(b"\x00" + row for _ in range(height))
    idat = chunk(b"IDAT", zlib.compress(raw, 6))
    iend = chunk(b"IEND", b"")
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


def _get_or_add_tblPr(tbl_el) -> object:
    """Return the <w:tblPr> child of a CT_Tbl element, creating it if absent."""
    tblPr = tbl_el.find(qn("w:tblPr"))
    if tblPr is None:
        tblPr = OxmlElement("w:tblPr")
        tbl_el.insert(0, tblPr)
    return tblPr


def _remove_table_borders(table) -> None:
    tblPr = _get_or_add_tblPr(table._tbl)
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


def _set_cell_width(cell, width_twips: int) -> None:
    tcPr = cell._tc.get_or_add_tcPr()
    for old in tcPr.findall(qn("w:tcW")):
        tcPr.remove(old)
    tcW = OxmlElement("w:tcW")
    tcW.set(qn("w:w"),    str(width_twips))
    tcW.set(qn("w:type"), "dxa")
    tcPr.append(tcW)


def _set_cell_valign(cell, val: str = "center") -> None:
    tcPr = cell._tc.get_or_add_tcPr()
    for old in tcPr.findall(qn("w:vAlign")):
        tcPr.remove(old)
    vAlign = OxmlElement("w:vAlign")
    vAlign.set(qn("w:val"), val)
    tcPr.append(vAlign)


def _center_table(tbl) -> None:
    """Set the table's horizontal alignment to centre."""
    tblPr = _get_or_add_tblPr(tbl._tbl)
    for old in tblPr.findall(qn("w:jc")):
        tblPr.remove(old)
    jc = OxmlElement("w:jc")
    jc.set(qn("w:val"), "center")
    tblPr.append(jc)


# ── Inline markup parser ──────────────────────────────────────────────

_INLINE_RE = re.compile(r"\*\*(.+?)\*\*|\*(.+?)\*|`([^`]+)`|([^*`]+)", re.DOTALL)


def _add_inline(para, text: str, secondary_rgb: RGBColor) -> None:
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
            run.font.name      = "Courier New"
            run.font.size      = Pt(9)
            run.font.color.rgb = secondary_rgb
        elif plain_txt is not None:
            para.add_run(plain_txt)


# ── Document styling helpers ──────────────────────────────────────────

def _heading(doc: Document, text: str, level: int, first_h1: list,
             primary_rgb: RGBColor, secondary_rgb: RGBColor) -> None:
    """Add a heading paragraph with colour driven by the palette."""
    if level == 1 and not first_h1:
        para = doc.add_paragraph(style="Title")
        para.clear()
        run = para.add_run(text)
        run.font.color.rgb = primary_rgb
        run.font.size = Pt(26)
        first_h1.append(True)
        return

    style_map = {1: "Heading 1", 2: "Heading 2", 3: "Heading 3", 4: "Heading 4"}
    para  = doc.add_paragraph(style=style_map.get(level, "Heading 4"))
    para.clear()
    run   = para.add_run(text)
    # H1 / H2 → primary colour;  H3+ → secondary colour
    run.font.color.rgb = primary_rgb if level <= 2 else secondary_rgb
    sizes = {1: Pt(20), 2: Pt(16), 3: Pt(13), 4: Pt(11)}
    run.font.size = sizes.get(level, Pt(11))


def _code_block(doc: Document, lines: list[str], secondary_rgb: RGBColor) -> None:
    """Add a shaded, monospaced code block."""
    for line in lines:
        para = doc.add_paragraph(style="Normal")
        _set_para_shading(para, _COLOR_CODE_BG)
        para.paragraph_format.left_indent  = Inches(0.3)
        para.paragraph_format.right_indent = Inches(0.3)
        para.paragraph_format.space_before = Pt(0)
        para.paragraph_format.space_after  = Pt(0)
        run = para.add_run(line)
        run.font.name      = "Courier New"
        run.font.size      = Pt(9)
        run.font.color.rgb = secondary_rgb


def _table_block(doc: Document, rows: list[str], primary_rgb: RGBColor,
                 primary_hex: str, secondary_rgb: RGBColor) -> None:
    """Parse a Markdown table and add a centred Word table with a styled header row."""
    def _split_row(line: str) -> list[str]:
        return [c.strip() for c in line.strip().strip("|").split("|")]

    data_rows = [r for r in rows if not re.match(r"^[\s|:\-]+$", r)]
    if not data_rows:
        return

    cols = len(_split_row(data_rows[0]))
    tbl  = doc.add_table(rows=len(data_rows), cols=cols)
    tbl.style = "Table Grid"
    _center_table(tbl)

    for r_idx, raw in enumerate(data_rows):
        cells = _split_row(raw)
        for c_idx, cell_text in enumerate(cells[:cols]):
            cell = tbl.cell(r_idx, c_idx)
            cell.text = ""
            para = cell.paragraphs[0]
            if r_idx == 0:
                _set_cell_bg(cell, primary_hex)
                run = para.add_run(cell_text)
                run.bold = True
                run.font.color.rgb = _COLOR_WHITE
            else:
                _add_inline(para, cell_text, secondary_rgb)

    doc.add_paragraph()  # spacing after table


# ── Cover page ────────────────────────────────────────────────────────

def _add_cover_page(doc: Document, title: str,
                    primary_rgb: RGBColor, secondary_rgb: RGBColor) -> None:
    """
    Add a cover page as section 1 (vertical-centre alignment) followed by a
    'next page' section break.  The main body is section 2.
    """
    month_year = _month_year_es()

    body_sectPr = doc.element.body.sectPr
    orig_pgSz   = body_sectPr.find(qn("w:pgSz")) if body_sectPr is not None else None

    # ── Title ────────────────────────────────────────────────────────
    title_para = doc.add_paragraph()
    title_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
    title_para.paragraph_format.space_before = Pt(0)
    title_para.paragraph_format.space_after  = Pt(20)
    run = title_para.add_run(title)
    run.font.size      = Pt(36)
    run.font.bold      = True
    run.font.color.rgb = primary_rgb

    # ── Subtitle ─────────────────────────────────────────────────────
    sub_para = doc.add_paragraph()
    sub_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
    sub_para.paragraph_format.space_before = Pt(0)
    sub_para.paragraph_format.space_after  = Pt(30)
    sub_run = sub_para.add_run("Draft de documentación realizada por GenDoc")
    sub_run.font.size      = Pt(14)
    sub_run.font.italic    = True
    sub_run.font.color.rgb = secondary_rgb

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
    sep_para = doc.add_paragraph()
    sep_para.paragraph_format.space_before = Pt(0)
    sep_para.paragraph_format.space_after  = Pt(0)

    pPr    = sep_para._p.get_or_add_pPr()
    sectPr = OxmlElement("w:sectPr")

    type_el = OxmlElement("w:type")
    type_el.set(qn("w:val"), "nextPage")
    sectPr.append(type_el)

    if orig_pgSz is not None:
        sectPr.append(copy.deepcopy(orig_pgSz))
    else:
        pgSz = OxmlElement("w:pgSz")
        pgSz.set(qn("w:w"), "12240")
        pgSz.set(qn("w:h"), "15840")
        sectPr.append(pgSz)

    # 1.27 cm = 720 twips — used for the cover section margins
    pgMar = OxmlElement("w:pgMar")
    for attr in ("w:top", "w:right", "w:bottom", "w:left", "w:header", "w:footer"):
        pgMar.set(qn(attr), "720")
    pgMar.set(qn("w:gutter"), "0")
    sectPr.append(pgMar)

    # Vertical centre for the cover page
    vAlign = OxmlElement("w:vAlign")
    vAlign.set(qn("w:val"), "center")
    sectPr.append(vAlign)

    pPr.append(sectPr)


# ── Header & footer ───────────────────────────────────────────────────

def _setup_header_footer(doc: Document, project_title: str,
                         primary_rgb: RGBColor, secondary_rgb: RGBColor) -> None:
    """
    Header layout (borderless 2-column table):
        [logo placeholder]  |  Autor(a):                ← both lines vertically
                            |  Draft generado por GenDoc    centred next to image

    Footer layout (left-aligned):
        <project title>   ·   Todos los derechos reservados, Mes Año
    """
    month_year = _month_year_es()
    section    = doc.sections[-1]

    # ── Header ───────────────────────────────────────────────────────
    header  = section.header
    # Letter paper (21.59 cm) minus 2 × 1.27 cm margins = 19.05 cm usable width
    hdr_tbl = header.add_table(rows=1, cols=2, width=Cm(19.05))
    _remove_table_borders(hdr_tbl)

    # Logo column: 1.3 in (1872 twips); text column: ~6.2 in (8928 twips)
    _set_cell_width(hdr_tbl.cell(0, 0), 1872)
    _set_cell_width(hdr_tbl.cell(0, 1), 8928)

    # Image cell — vertically centred
    cell_img = hdr_tbl.cell(0, 0)
    _set_cell_valign(cell_img, "center")
    p_img = cell_img.paragraphs[0]
    p_img.alignment = WD_ALIGN_PARAGRAPH.LEFT
    run_img = p_img.add_run()
    run_img.add_picture(io.BytesIO(_make_placeholder_png(120, 50)), width=Inches(1.05))

    # Text cell — vertically centred
    cell_txt = hdr_tbl.cell(0, 1)
    _set_cell_valign(cell_txt, "center")

    p_author = cell_txt.paragraphs[0]
    p_author.paragraph_format.space_before = Pt(0)
    p_author.paragraph_format.space_after  = Pt(1)
    r_author = p_author.add_run("Autor(a):")
    r_author.font.size      = Pt(9)
    r_author.font.bold      = True
    r_author.font.color.rgb = primary_rgb

    p_draft = cell_txt.add_paragraph()
    p_draft.paragraph_format.space_before = Pt(0)
    p_draft.paragraph_format.space_after  = Pt(0)
    r_draft = p_draft.add_run("Draft generado por GenDoc")
    r_draft.font.size      = Pt(8)
    r_draft.font.italic    = True
    r_draft.font.color.rgb = primary_rgb

    # Remove the default leading <w:p> that precedes our table
    hdr_el  = header._element
    first_p = hdr_el.find(qn("w:p"))
    if first_p is not None:
        hdr_el.remove(first_p)
    # OOXML requires at least one trailing <w:p> in headers/footers
    header.add_paragraph()

    # ── Footer ───────────────────────────────────────────────────────
    footer = section.footer
    fp     = footer.paragraphs[0]
    fp.alignment = WD_ALIGN_PARAGRAPH.LEFT

    r_title = fp.add_run(project_title)
    r_title.font.bold      = True
    r_title.font.size      = Pt(9)
    r_title.font.color.rgb = primary_rgb

    r_sep = fp.add_run("   ·   ")
    r_sep.font.size      = Pt(9)
    r_sep.font.color.rgb = _COLOR_GRAY

    r_rights = fp.add_run(f"Todos los derechos reservados, {month_year}")
    r_rights.font.size      = Pt(9)
    r_rights.font.color.rgb = _COLOR_GRAY


# ── Main converter ────────────────────────────────────────────────────

def convert(
    markdown: str,
    output_path: str | Path,
    *,
    primary_color:   str = _DEFAULT_PRIMARY,
    secondary_color: str = _DEFAULT_SECONDARY,
) -> Path:
    """
    Convert *markdown* to a styled .docx and write it to *output_path*.

    Parameters
    ----------
    primary_color   : hex string (e.g. '#2D3A8C') — title, H1/H2, table headers
    secondary_color : hex string — H3+, code, header/footer accent text

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
        raise RuntimeError(f"La ruta de salida no es una carpeta: {out.parent}.")

    primary_rgb   = _hex_to_rgb(primary_color)
    primary_hex   = _hex_to_str(primary_color)
    secondary_rgb = _hex_to_rgb(secondary_color)

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
        title = out.stem.replace("_", " ").title()

    # ── Cover page (section 1, vAlign=center) ────────────────────────
    _add_cover_page(doc, title, primary_rgb, secondary_rgb)

    # ── Header + footer on main section (section 2) ──────────────────
    _setup_header_footer(doc, title, primary_rgb, secondary_rgb)

    # ── Apply 1.27 cm margins to all sections (page + header/footer) ─
    for sec in doc.sections:
        sec.top_margin      = Cm(1.27)
        sec.bottom_margin   = Cm(1.27)
        sec.left_margin     = Cm(1.27)
        sec.right_margin    = Cm(1.27)
        sec.header_distance = Cm(1.27)
        sec.footer_distance = Cm(1.27)

    # ── Process markdown body ────────────────────────────────────────
    # first_h1 pre-filled: the title was consumed by the cover, so any
    # remaining H1 lines render as Heading 1 (not the Title style).
    first_h1 = [True]
    i        = 0

    while i < n:
        line = lines[i]

        # Skip the line already used for the cover title
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
            _code_block(doc, code_lines, secondary_rgb)
            i += 1
            continue

        # ── Markdown table ───────────────────────────────────────────
        if "|" in line and line.strip().startswith("|"):
            table_rows: list[str] = []
            while i < n and "|" in lines[i] and lines[i].strip().startswith("|"):
                table_rows.append(lines[i])
                i += 1
            _table_block(doc, table_rows, primary_rgb, primary_hex, secondary_rgb)
            continue

        # ── Headings ─────────────────────────────────────────────────
        heading_m = re.match(r"^(#{1,4})\s+(.*)", line)
        if heading_m:
            level = len(heading_m.group(1))
            text  = heading_m.group(2).strip()
            _heading(doc, text, level, first_h1, primary_rgb, secondary_rgb)
            i += 1
            continue

        # ── Unordered list ───────────────────────────────────────────
        if re.match(r"^\s*[-*]\s+", line):
            para = doc.add_paragraph(style="List Bullet")
            _add_inline(para, re.sub(r"^\s*[-*]\s+", "", line), secondary_rgb)
            i += 1
            continue

        # ── Ordered list ─────────────────────────────────────────────
        if re.match(r"^\s*\d+\.\s+", line):
            para = doc.add_paragraph(style="List Number")
            _add_inline(para, re.sub(r"^\s*\d+\.\s+", "", line), secondary_rgb)
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
        _add_inline(para, line, secondary_rgb)
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
        raise RuntimeError(f"No se pudo guardar el documento Word: {exc}")

    return out
