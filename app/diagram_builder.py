"""
diagram_builder.py — Build editable Word diagrams from Mermaid flowchart code.

Converts `flowchart TD`, `flowchart LR`, `graph TD`, `graph LR` Mermaid syntax
into a native DrawingML WordProcessingCanvas: each node becomes an editable
Word shape and each edge becomes a native connector.

All XML is built via lxml's element API (never via string parsing) so that
namespace declarations are emitted exactly once on the root <w:drawing> element
and all child elements inherit consistent prefixes — avoiding the corrupt-file
errors that arise when etree.fromstring() produces a standalone nsmap that
conflicts with the parent python-docx document tree on serialisation.

The resulting diagram is fully editable in Word:
  - Double-click a node to edit its text
  - Drag nodes to reposition them
  - Connectors move with the shapes they are attached to

Raises UnsupportedDiagramType for all other diagram types
(sequenceDiagram, classDiagram, etc.) — callers should fall back to image.
"""

from __future__ import annotations

import itertools
import re

from lxml import etree

# ── Namespace URIs ────────────────────────────────────────────────────

_W   = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
_WP  = "http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing"
_A   = "http://schemas.openxmlformats.org/drawingml/2006/main"
_WPS = "http://schemas.microsoft.com/office/word/2010/wordprocessingShape"
_WPC = "http://schemas.microsoft.com/office/word/2010/wordprocessingCanvas"
_XML = "http://www.w3.org/XML/1998/namespace"

# Single nsmap applied to the root <w:drawing> — all descendants inherit it
_NSMAP = {'w': _W, 'wp': _WP, 'a': _A, 'wps': _WPS, 'wpc': _WPC}


# ── Namespace-qualified name helpers ──────────────────────────────────

def _w(t):   return f'{{{_W}}}{t}'
def _wp(t):  return f'{{{_WP}}}{t}'
def _a(t):   return f'{{{_A}}}{t}'
def _wps(t): return f'{{{_WPS}}}{t}'
def _wpc(t): return f'{{{_WPC}}}{t}'


# ── EMU layout constants ──────────────────────────────────────────────

_CM = 360_000

_NODE_W = int(3.8 * _CM)
_NODE_H = int(1.0 * _CM)
_DIAM_W = int(3.0 * _CM)
_DIAM_H = int(1.6 * _CM)
_CIRC_D = int(1.4 * _CM)

_H_GAP  = int(1.0 * _CM)
_V_GAP  = int(1.8 * _CM)
_MARGIN = int(0.7 * _CM)
_MAX_W  = int(17.5 * _CM)

# Shape IDs must be unique across the whole docx; start high to avoid
# collisions with IDs assigned by python-docx for other inline pictures.
_id_counter = itertools.count(50_000)


# ── Public exception ──────────────────────────────────────────────────

class UnsupportedDiagramType(Exception):
    """Raised when the Mermaid code cannot be converted to native DrawingML."""


# ── Mermaid parser ────────────────────────────────────────────────────

def _label_from(bracket_text: str) -> str:
    s = bracket_text.strip()
    for seq in ['[[', ']]', '((', '))', '[', ']', '(', ')', '{', '}']:
        s = s.replace(seq, '')
    s = s.strip()
    if len(s) >= 2 and s[0] in ('"', "'") and s[-1] == s[0]:
        s = s[1:-1]
    return s.strip() or '?'


def _shape_from(bracket_text: str) -> str:
    s = bracket_text.strip()
    if s.startswith('(('):  return 'ellipse'
    if s.startswith('{'):   return 'diamond'
    if s.startswith('('):   return 'roundRect'
    return 'rect'


_NODE_DEF_RE = re.compile(
    r'([\w_]+)\s*(\[\[.*?\]\]|\(\(.*?\)\)|\[.*?\]|\(.*?\)|\{.*?\})'
)
_EDGE_RE = re.compile(
    r'([\w_]+)'
    r'(?:\s*(?:\[\[.*?\]\]|\(\(.*?\)\)|\[.*?\]|\(.*?\)|\{.*?\}))?'
    r'\s*'
    r'(?:'
        r'--\s*(.*?)\s*-->'
        r'|-->?\s*\|([^|]*)\|'
        r'|--[-.=>]+-?>?'
        r'|-->'
    r')'
    r'\s*'
    r'([\w_]+)'
    r'(?:\s*(?:\[\[.*?\]\]|\(\(.*?\)\)|\[.*?\]|\(.*?\)|\{.*?\}))?'
)


def _parse(code: str) -> tuple[str, dict, list]:
    lines = code.strip().splitlines()
    if not lines:
        raise UnsupportedDiagramType("empty diagram")

    first = lines[0].strip().lower()
    if not (first.startswith('flowchart') or first.startswith('graph ')):
        raise UnsupportedDiagramType(f"unsupported type: {lines[0].strip()[:40]}")

    m = re.match(r'(?:flowchart|graph)\s+(\w+)', lines[0].strip(), re.IGNORECASE)
    raw_dir = m.group(1).upper() if m else 'TD'
    direction = 'LR' if raw_dir in ('LR', 'RL') else 'TD'

    nodes: dict[str, dict] = {}
    edges: list[tuple] = []

    for line in lines[1:]:
        s = line.strip()
        if (not s
                or s.startswith('%%')
                or s.lower().startswith('subgraph')
                or s.lower() == 'end'
                or s.lower().startswith(('style ', 'classdef ', 'class ', 'click '))):
            continue

        for nm in _NODE_DEF_RE.finditer(s):
            nid, suffix = nm.group(1), nm.group(2)
            if nid not in nodes:
                nodes[nid] = {'label': _label_from(suffix), 'shape': _shape_from(suffix)}

        for em in _EDGE_RE.finditer(s):
            src  = em.group(1)
            lbl1 = (em.group(2) or '').strip()
            lbl2 = (em.group(3) or '').strip()
            dst  = em.group(4)
            label = lbl1 or lbl2
            if len(label) >= 2 and label[0] in ('"', "'") and label[-1] == label[0]:
                label = label[1:-1]

            if src not in nodes:
                nodes[src] = {'label': src, 'shape': 'rect'}
            if dst not in nodes:
                nodes[dst] = {'label': dst, 'shape': 'rect'}
            edges.append((src, dst, label.strip()))

    if not nodes:
        raise UnsupportedDiagramType("no nodes found")

    return direction, nodes, edges


# ── Layout engine ─────────────────────────────────────────────────────

def _node_dim(shape: str) -> tuple[int, int]:
    if shape == 'diamond': return _DIAM_W, _DIAM_H
    if shape == 'ellipse': return _CIRC_D, _CIRC_D
    return _NODE_W, _NODE_H


def _assign_layers(node_ids: list, edges: list) -> dict[str, int]:
    in_deg   = {n: 0 for n in node_ids}
    children = {n: [] for n in node_ids}
    for src, dst, _ in edges:
        if dst in in_deg:
            in_deg[dst] += 1
        if src in children:
            children[src].append(dst)

    roots = [n for n in node_ids if in_deg[n] == 0] or [node_ids[0]]
    layer = {r: 0 for r in roots}
    queue = list(roots)
    while queue:
        n = queue.pop(0)
        for ch in children.get(n, []):
            new_l = layer[n] + 1
            if new_l > layer.get(ch, -1):
                layer[ch] = new_l
                queue.append(ch)
    for n in node_ids:
        layer.setdefault(n, 0)
    return layer


def _compute_layout(nodes: dict, edges: list, direction: str) -> dict[str, dict]:
    node_ids  = list(nodes.keys())
    layer_map = _assign_layers(node_ids, edges)

    by_layer: dict[int, list] = {}
    for nid, l in layer_map.items():
        by_layer.setdefault(l, []).append(nid)

    max_w = max(_node_dim(nodes[n]['shape'])[0] for n in node_ids)
    max_h = max(_node_dim(nodes[n]['shape'])[1] for n in node_ids)
    pos: dict[str, dict] = {}

    if direction == 'TD':
        max_layer_w = max(
            sum(_node_dim(nodes[n]['shape'])[0] for n in ln)
            + _H_GAP * max(0, len(ln) - 1)
            for ln in by_layer.values()
        )
        canvas_w = max_layer_w + 2 * _MARGIN
        scale = min(1.0, _MAX_W / canvas_w)

        for l, ln in sorted(by_layer.items()):
            layer_w = (
                sum(_node_dim(nodes[n]['shape'])[0] for n in ln)
                + _H_GAP * max(0, len(ln) - 1)
            )
            x = int((canvas_w - layer_w) / 2 * scale)
            for nid in ln:
                w, h = _node_dim(nodes[nid]['shape'])
                w, h = int(w * scale), int(h * scale)
                y = int((_MARGIN + l * (max_h + _V_GAP)) * scale)
                pos[nid] = {'x': x, 'y': y, 'w': w, 'h': h}
                x += w + int(_H_GAP * scale)
    else:
        max_layer_h = max(
            sum(_node_dim(nodes[n]['shape'])[1] for n in ln)
            + _H_GAP * max(0, len(ln) - 1)
            for ln in by_layer.values()
        )
        canvas_h = max_layer_h + 2 * _MARGIN
        n_layers = max(by_layer.keys()) + 1
        est_w = _MARGIN + n_layers * (max_w + _H_GAP) + _MARGIN
        scale = min(1.0, _MAX_W / max(est_w, 1))

        for l, ln in sorted(by_layer.items()):
            layer_h = (
                sum(_node_dim(nodes[n]['shape'])[1] for n in ln)
                + _H_GAP * max(0, len(ln) - 1)
            )
            y = int((canvas_h - layer_h) / 2 * scale)
            for nid in ln:
                w, h = _node_dim(nodes[nid]['shape'])
                w, h = int(w * scale), int(h * scale)
                x = int((_MARGIN + l * (max_w + _H_GAP)) * scale)
                pos[nid] = {'x': x, 'y': y, 'w': w, 'h': h}
                y += h + int(_H_GAP * scale)

    return pos


# ── lxml element builders ─────────────────────────────────────────────

def _sub(parent, tag, attrib=None):
    """Create a SubElement; attrib values are always strings."""
    return etree.SubElement(parent, tag, attrib={k: str(v) for k, v in (attrib or {}).items()})


def _add_shape(canvas, sp_id: int, name: str,
               shape: str, x: int, y: int, w: int, h: int,
               fill_hex: str, text_hex: str, label: str) -> None:
    """Append a wps:wsp shape node to *canvas*."""
    prst = {'roundRect': 'roundRect', 'diamond': 'diamond',
            'ellipse': 'ellipse'}.get(shape, 'rect')

    wsp    = _sub(canvas, _wps('wsp'))
    _sub(wsp, _wps('cNvPr'), {'id': sp_id, 'name': name})
    _sub(wsp, _wps('cNvSpPr'))          # empty: no shape locks

    sppr   = _sub(wsp, _wps('spPr'))
    xfrm   = _sub(sppr, _a('xfrm'))
    _sub(xfrm, _a('off'), {'x': x, 'y': y})
    _sub(xfrm, _a('ext'), {'cx': w, 'cy': h})
    prstg  = _sub(sppr, _a('prstGeom'), {'prst': prst})
    _sub(prstg, _a('avLst'))
    fill   = _sub(sppr, _a('solidFill'))
    _sub(fill, _a('srgbClr'), {'val': fill_hex})
    ln     = _sub(sppr, _a('ln'), {'w': '12700'})
    lnfill = _sub(ln, _a('solidFill'))
    _sub(lnfill, _a('srgbClr'), {'val': fill_hex})

    # Text body — w:txbxContent uses w: namespace (already in nsmap)
    txbx    = _sub(wsp, _wps('txbx'))
    content = _sub(txbx, _w('txbxContent'))
    p       = _sub(content, _w('p'))
    ppr     = _sub(p, _w('pPr'))
    _sub(ppr, _w('jc'), {_w('val'): 'center'})
    r       = _sub(p, _w('r'))
    rpr     = _sub(r, _w('rPr'))
    _sub(rpr, _w('color'),  {_w('val'): text_hex})
    _sub(rpr, _w('sz'),     {_w('val'): '18'})
    _sub(rpr, _w('szCs'),   {_w('val'): '18'})
    t       = _sub(r, _w('t'), {f'{{{_XML}}}space': 'preserve'})
    t.text  = label

    _sub(wsp, _wps('bodyPr'), {
        'anchor': 'ctr', 'anchorCtr': '1', 'wrap': 'square',
        'lIns': '91440', 'rIns': '91440', 'tIns': '45720', 'bIns': '45720',
    })


def _add_connector(canvas, sp_id: int, src_sp_id: int, dst_sp_id: int,
                   x1: int, y1: int, x2: int, y2: int,
                   label: str, line_hex: str, direction: str) -> None:
    """Append a wps:wsp connector to *canvas*."""
    src_idx = 2 if direction == 'TD' else 1   # bottom / right
    dst_idx = 0 if direction == 'TD' else 3   # top   / left

    off_x  = min(x1, x2)
    off_y  = min(y1, y2)
    ext_cx = max(1, abs(x2 - x1))
    ext_cy = max(1, abs(y2 - y1))

    wsp = _sub(canvas, _wps('wsp'))
    _sub(wsp, _wps('cNvPr'), {'id': sp_id, 'name': f'Connector {sp_id}'})

    cxnpr = _sub(wsp, _wps('cNvCxnSpPr'))
    _sub(cxnpr, _a('stCxn'),  {'id': src_sp_id, 'idx': src_idx})
    _sub(cxnpr, _a('endCxn'), {'id': dst_sp_id, 'idx': dst_idx})

    xfrm_attrib: dict = {}
    if x2 < x1: xfrm_attrib['flipH'] = '1'
    if y2 < y1: xfrm_attrib['flipV'] = '1'

    sppr  = _sub(wsp, _wps('spPr'))
    xfrm  = _sub(sppr, _a('xfrm'), xfrm_attrib)
    _sub(xfrm, _a('off'), {'x': off_x, 'y': off_y})
    _sub(xfrm, _a('ext'), {'cx': ext_cx, 'cy': ext_cy})
    prstg = _sub(sppr, _a('prstGeom'), {'prst': 'straightConnector1'})
    _sub(prstg, _a('avLst'))
    ln    = _sub(sppr, _a('ln'), {'w': '19050'})
    lnf   = _sub(ln, _a('solidFill'))
    _sub(lnf, _a('srgbClr'), {'val': line_hex})
    _sub(ln, _a('headEnd'), {'type': 'none'})
    _sub(ln, _a('tailEnd'),  {'type': 'arrow', 'w': 'med', 'len': 'med'})

    if label:
        txbx    = _sub(wsp, _wps('txbx'))
        content = _sub(txbx, _w('txbxContent'))
        p       = _sub(content, _w('p'))
        ppr     = _sub(p, _w('pPr'))
        _sub(ppr, _w('jc'), {_w('val'): 'center'})
        r       = _sub(p, _w('r'))
        rpr     = _sub(r, _w('rPr'))
        _sub(rpr, _w('sz'),   {_w('val'): '16'})
        _sub(rpr, _w('szCs'), {_w('val'): '16'})
        t       = _sub(r, _w('t'), {f'{{{_XML}}}space': 'preserve'})
        t.text  = label

    _sub(wsp, _wps('bodyPr'))


# ── Public API ────────────────────────────────────────────────────────

def is_supported(mermaid_code: str) -> bool:
    """Return True if *mermaid_code* can be rendered as native DrawingML (no HTTP needed)."""
    try:
        _parse(mermaid_code)
        return True
    except UnsupportedDiagramType:
        return False


def build_native(doc, mermaid_code: str, primary_hex: str) -> bool:
    """
    Parse *mermaid_code* and insert a native DrawingML diagram into *doc*.

    The diagram is a WordProcessingCanvas (<wpc:wpc>) with editable shapes
    and connectors.  All XML is built via lxml's element API so that namespace
    declarations are emitted once on the root <w:drawing> and all children
    inherit consistent prefixes — no string-parsing / fromstring() involved.

    Returns True on success, False if the diagram type is unsupported.
    Any unexpected error also returns False so the caller can fall back to
    image rendering.
    """
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.shared import Pt

    try:
        direction, nodes, edges = _parse(mermaid_code)
    except UnsupportedDiagramType:
        return False

    try:
        pos = _compute_layout(nodes, edges, direction)

        cx = max(p['x'] + p['w'] for p in pos.values()) + _MARGIN
        cy = max(p['y'] + p['h'] for p in pos.values()) + _MARGIN

        h_val = primary_hex.lstrip('#')
        r_val = int(h_val[0:2], 16)
        g_val = int(h_val[2:4], 16)
        b_val = int(h_val[4:6], 16)
        text_hex = '000000' if (0.299*r_val + 0.587*g_val + 0.114*b_val)/255 > 0.5 else 'FFFFFF'
        fill_hex = h_val.upper()

        shape_ids: dict[str, int] = {nid: next(_id_counter) for nid in nodes}
        doc_pr_id = next(_id_counter)

        # ── Build the drawing element tree (lxml API, no string parsing) ──
        drawing = etree.Element(_w('drawing'), nsmap=_NSMAP)

        inline = _sub(drawing, _wp('inline'),
                      {'distT': '0', 'distB': '0', 'distL': '0', 'distR': '0'})
        _sub(inline, _wp('extent'),       {'cx': cx, 'cy': cy})
        _sub(inline, _wp('effectExtent'), {'l': '0', 't': '0', 'r': '0', 'b': '0'})
        _sub(inline, _wp('docPr'),        {'id': doc_pr_id, 'name': f'Diagrama {doc_pr_id}'})

        cnv_gfx = _sub(inline, _wp('cNvGraphicFramePr'))
        _sub(cnv_gfx, _a('graphicFrameLocks'), {'noChangeAspect': '1'})

        graphic  = _sub(inline, _a('graphic'))
        gfx_data = _sub(graphic, _a('graphicData'), {'uri': _WPC})
        canvas   = _sub(gfx_data, _wpc('wpc'))
        _sub(canvas, _wpc('bg'))
        _sub(canvas, _wpc('whole'))

        # Add shapes
        for nid in nodes:
            p = pos[nid]
            _add_shape(
                canvas, shape_ids[nid], nid,
                nodes[nid]['shape'], p['x'], p['y'], p['w'], p['h'],
                fill_hex, text_hex, nodes[nid]['label'],
            )

        # Add connectors
        for src, dst, label in edges:
            if src not in pos or dst not in pos:
                continue
            sp, dp = pos[src], pos[dst]
            if direction == 'TD':
                x1, y1 = sp['x'] + sp['w']//2, sp['y'] + sp['h']
                x2, y2 = dp['x'] + dp['w']//2, dp['y']
            else:
                x1, y1 = sp['x'] + sp['w'], sp['y'] + sp['h']//2
                x2, y2 = dp['x'],            dp['y'] + dp['h']//2
            _add_connector(
                canvas, next(_id_counter),
                shape_ids[src], shape_ids[dst],
                x1, y1, x2, y2,
                label, fill_hex, direction,
            )

        # ── Insert into document ──────────────────────────────────────
        para = doc.add_paragraph()
        para.alignment = WD_ALIGN_PARAGRAPH.CENTER
        para.paragraph_format.space_before = Pt(8)
        para.paragraph_format.space_after  = Pt(8)
        run = para.add_run()
        run._r.append(drawing)

        return True

    except Exception:
        return False
