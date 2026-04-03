"""
diagram_builder.py — Build editable Word diagrams from Mermaid flowchart code.

Converts `flowchart TD`, `flowchart LR`, `graph TD`, `graph LR` Mermaid syntax
into a native DrawingML WordProcessingCanvas: each node becomes an editable
Word shape and each edge becomes a native connector.

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

# ── EMU layout constants ──────────────────────────────────────────────

_CM = 360_000          # 1 cm in EMU

_NODE_W = int(3.8 * _CM)   # default node width
_NODE_H = int(1.0 * _CM)   # default node height
_DIAM_W = int(3.0 * _CM)   # diamond width  (wider than tall for readability)
_DIAM_H = int(1.6 * _CM)   # diamond height
_CIRC_D = int(1.4 * _CM)   # circle / ellipse diameter

_H_GAP  = int(1.0 * _CM)   # gap between nodes in the same layer
_V_GAP  = int(1.8 * _CM)   # gap between layers
_MARGIN = int(0.7 * _CM)   # canvas outer margin

_MAX_W  = int(17.5 * _CM)  # max canvas width (fits within standard page margins)

# Document-wide ID counter — must be unique across the whole docx
_id_counter = itertools.count(500)


# ── Public exception ──────────────────────────────────────────────────

class UnsupportedDiagramType(Exception):
    """Raised when the Mermaid code cannot be converted to native DrawingML."""


# ── Mermaid parser ────────────────────────────────────────────────────

def _label_from(bracket_text: str) -> str:
    """Strip Mermaid node bracket syntax and return the display label."""
    s = bracket_text.strip()
    for seq in ['[[', ']]', '((', '))', '[', ']', '(', ')', '{', '}']:
        s = s.replace(seq, '')
    s = s.strip()
    if len(s) >= 2 and s[0] in ('"', "'") and s[-1] == s[0]:
        s = s[1:-1]
    return s.strip() or '?'


def _shape_from(bracket_text: str) -> str:
    """Infer DrawingML preset geometry from Mermaid bracket syntax."""
    s = bracket_text.strip()
    if s.startswith('(('):  return 'ellipse'
    if s.startswith('{'):   return 'diamond'
    if s.startswith('('):   return 'roundRect'
    return 'rect'


# Matches inline node definitions: ID[text], ID(text), ID{text}, ID((text))
_NODE_DEF_RE = re.compile(
    r'([\w_]+)\s*(\[\[.*?\]\]|\(\(.*?\)\)|\[.*?\]|\(.*?\)|\{.*?\})'
)

# Matches edges with optional inline node definitions on source and target
_EDGE_RE = re.compile(
    r'([\w_]+)'                                                          # source ID
    r'(?:\s*(?:\[\[.*?\]\]|\(\(.*?\)\)|\[.*?\]|\(.*?\)|\{.*?\}))?'     # optional src def
    r'\s*'
    r'(?:'
        r'--\s*(.*?)\s*-->'      # -- label -->
        r'|-->?\s*\|([^|]*)\|'   # -->|label|  or  ->|label|
        r'|--[-.=>]+-?>?'        # plain arrows/lines: -->, ---, -.->. ==>
        r'|-->'
    r')'
    r'\s*'
    r'([\w_]+)'                                                          # target ID
    r'(?:\s*(?:\[\[.*?\]\]|\(\(.*?\)\)|\[.*?\]|\(.*?\)|\{.*?\}))?'     # optional dst def
)


def _parse(code: str) -> tuple[str, dict, list]:
    """
    Parse a Mermaid flowchart/graph diagram.

    Returns
    -------
    direction : 'TD' | 'LR'
    nodes     : {id: {'label': str, 'shape': str}}
    edges     : [(src_id, dst_id, label)]

    Raises UnsupportedDiagramType for non-flowchart diagram types.
    """
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

        # Extract inline node definitions first
        for nm in _NODE_DEF_RE.finditer(s):
            nid, suffix = nm.group(1), nm.group(2)
            if nid not in nodes:
                nodes[nid] = {'label': _label_from(suffix), 'shape': _shape_from(suffix)}

        # Extract edges
        for em in _EDGE_RE.finditer(s):
            src  = em.group(1)
            lbl1 = (em.group(2) or '').strip()   # from -- label -->
            lbl2 = (em.group(3) or '').strip()   # from -->|label|
            dst  = em.group(4)
            label = lbl1 or lbl2
            # Strip quotes from edge labels
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
    """BFS from root nodes to assign each node a layer index."""
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
    """
    Return {node_id: {x, y, w, h}} in EMU.
    Nodes in each layer are centred relative to the widest layer.
    """
    node_ids = list(nodes.keys())
    layer_map = _assign_layers(node_ids, edges)

    by_layer: dict[int, list] = {}
    for nid, l in layer_map.items():
        by_layer.setdefault(l, []).append(nid)

    max_w = max(_node_dim(nodes[n]['shape'])[0] for n in node_ids)
    max_h = max(_node_dim(nodes[n]['shape'])[1] for n in node_ids)

    pos: dict[str, dict] = {}

    if direction == 'TD':
        # Canvas width determined by the widest layer
        max_layer_w = max(
            sum(_node_dim(nodes[n]['shape'])[0] for n in ln)
            + _H_GAP * max(0, len(ln) - 1)
            for ln in by_layer.values()
        )
        canvas_w = max_layer_w + 2 * _MARGIN

        # Scale down if wider than page
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

    else:  # LR
        max_layer_h = max(
            sum(_node_dim(nodes[n]['shape'])[1] for n in ln)
            + _H_GAP * max(0, len(ln) - 1)
            for ln in by_layer.values()
        )
        canvas_h = max_layer_h + 2 * _MARGIN

        # Estimate canvas width to check scale
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


# ── XML helpers ───────────────────────────────────────────────────────

def _esc(s: str) -> str:
    return (s.replace('&', '&amp;')
             .replace('<', '&lt;')
             .replace('>', '&gt;')
             .replace('"', '&quot;'))


def _shape_xml(nid: str, sp_id: int, label: str, shape: str,
               x: int, y: int, w: int, h: int,
               fill_hex: str, text_hex: str) -> str:
    prst = {'roundRect': 'roundRect', 'diamond': 'diamond',
            'ellipse': 'ellipse'}.get(shape, 'rect')
    return (
        f'<wps:wsp>'
        f'<wps:cNvPr id="{sp_id}" name="{_esc(nid)}"/>'
        f'<wps:cNvSpPr><a:spLocks noChangeArrowheads="1"/></wps:cNvSpPr>'
        f'<wps:spPr>'
        f'<a:xfrm><a:off x="{x}" y="{y}"/><a:ext cx="{w}" cy="{h}"/></a:xfrm>'
        f'<a:prstGeom prst="{prst}"><a:avLst/></a:prstGeom>'
        f'<a:solidFill><a:srgbClr val="{fill_hex}"/></a:solidFill>'
        f'<a:ln w="12700"><a:solidFill><a:srgbClr val="{fill_hex}"/></a:solidFill></a:ln>'
        f'</wps:spPr>'
        f'<wps:txbx><w:txbxContent><w:p>'
        f'<w:pPr><w:jc w:val="center"/></w:pPr>'
        f'<w:r><w:rPr>'
        f'<w:color w:val="{text_hex}"/><w:sz w:val="18"/><w:szCs w:val="18"/>'
        f'</w:rPr><w:t xml:space="preserve">{_esc(label)}</w:t></w:r>'
        f'</w:p></w:txbxContent></wps:txbx>'
        f'<wps:bodyPr anchor="ctr" anchorCtr="1" wrap="square"'
        f' lIns="91440" rIns="91440" tIns="45720" bIns="45720"/>'
        f'</wps:wsp>'
    )


def _connector_xml(sp_id: int, src_id: int, dst_id: int,
                   x1: int, y1: int, x2: int, y2: int,
                   label: str, line_hex: str,
                   direction: str) -> str:
    # Connection-site indices: 0=top, 1=right, 2=bottom, 3=left
    src_idx = 2 if direction == 'TD' else 1
    dst_idx = 0 if direction == 'TD' else 3

    off_x = min(x1, x2)
    off_y = min(y1, y2)
    ext_cx = max(1, abs(x2 - x1))
    ext_cy = max(1, abs(y2 - y1))
    flip = ((' flipH="1"' if x2 < x1 else '')
            + (' flipV="1"' if y2 < y1 else ''))

    label_xml = ''
    if label:
        label_xml = (
            f'<wps:txbx><w:txbxContent><w:p>'
            f'<w:pPr><w:jc w:val="center"/></w:pPr>'
            f'<w:r><w:rPr><w:sz w:val="16"/><w:szCs w:val="16"/></w:rPr>'
            f'<w:t xml:space="preserve">{_esc(label)}</w:t>'
            f'</w:r></w:p></w:txbxContent></wps:txbx>'
        )

    return (
        f'<wps:wsp>'
        f'<wps:cNvPr id="{sp_id}" name="Connector {sp_id}"/>'
        f'<wps:cNvCxnSpPr>'
        f'<a:stCxn id="{src_id}" idx="{src_idx}"/>'
        f'<a:endCxn id="{dst_id}" idx="{dst_idx}"/>'
        f'</wps:cNvCxnSpPr>'
        f'<wps:spPr>'
        f'<a:xfrm{flip}>'
        f'<a:off x="{off_x}" y="{off_y}"/>'
        f'<a:ext cx="{ext_cx}" cy="{ext_cy}"/>'
        f'</a:xfrm>'
        f'<a:prstGeom prst="straightConnector1"><a:avLst/></a:prstGeom>'
        f'<a:ln w="19050">'
        f'<a:solidFill><a:srgbClr val="{line_hex}"/></a:solidFill>'
        f'<a:headEnd type="none"/>'
        f'<a:tailEnd type="arrow" w="med" len="med"/>'
        f'</a:ln>'
        f'</wps:spPr>'
        f'{label_xml}'
        f'<wps:bodyPr/>'
        f'</wps:wsp>'
    )


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

    The diagram is rendered as a WordProcessingCanvas containing editable
    shapes and connectors styled with *primary_hex*.

    Parameters
    ----------
    doc          : docx.Document
    mermaid_code : str   — Raw Mermaid code (without %%{init}%% directives)
    primary_hex  : str   — Hex colour without '#', e.g. '2D3A8C'

    Returns
    -------
    True  — diagram appended successfully.
    False — diagram type not supported; caller should fall back to image.
    """
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.shared import Pt

    try:
        direction, nodes, edges = _parse(mermaid_code)
    except UnsupportedDiagramType:
        return False

    pos = _compute_layout(nodes, edges, direction)

    # Canvas bounding box
    cx = max(p['x'] + p['w'] for p in pos.values()) + _MARGIN
    cy = max(p['y'] + p['h'] for p in pos.values()) + _MARGIN

    # Colour contrast
    h = primary_hex.lstrip('#')
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    text_hex = '000000' if (0.299 * r + 0.587 * g + 0.114 * b) / 255 > 0.5 else 'FFFFFF'
    fill_hex = primary_hex.lstrip('#').upper()

    # Assign unique IDs to each shape
    shape_ids: dict[str, int] = {nid: next(_id_counter) for nid in nodes}
    doc_pr_id = next(_id_counter)

    # Build shape elements
    shapes_xml = ''.join(
        _shape_xml(
            nid, shape_ids[nid],
            nodes[nid]['label'], nodes[nid]['shape'],
            pos[nid]['x'], pos[nid]['y'], pos[nid]['w'], pos[nid]['h'],
            fill_hex, text_hex,
        )
        for nid in nodes
    )

    # Build connector elements
    conns_xml = ''
    for src, dst, label in edges:
        if src not in pos or dst not in pos:
            continue
        sp, dp = pos[src], pos[dst]
        if direction == 'TD':
            x1, y1 = sp['x'] + sp['w'] // 2, sp['y'] + sp['h']
            x2, y2 = dp['x'] + dp['w'] // 2, dp['y']
        else:
            x1, y1 = sp['x'] + sp['w'], sp['y'] + sp['h'] // 2
            x2, y2 = dp['x'],           dp['y'] + dp['h'] // 2
        conns_xml += _connector_xml(
            next(_id_counter), shape_ids[src], shape_ids[dst],
            x1, y1, x2, y2, label, fill_hex, direction,
        )

    # Assemble full drawing XML with all namespaces declared at root
    ns = (
        f'xmlns:w="{_W}" xmlns:wp="{_WP}" '
        f'xmlns:a="{_A}" xmlns:wps="{_WPS}" xmlns:wpc="{_WPC}"'
    )
    drawing_xml = (
        f'<w:drawing {ns}>'
        f'<wp:inline distT="0" distB="0" distL="0" distR="0">'
        f'<wp:extent cx="{cx}" cy="{cy}"/>'
        f'<wp:effectExtent l="0" t="0" r="0" b="0"/>'
        f'<wp:docPr id="{doc_pr_id}" name="Diagrama {doc_pr_id}"/>'
        f'<wp:cNvGraphicFramePr/>'
        f'<a:graphic>'
        f'<a:graphicData uri="{_WPC}">'
        f'<wpc:wpc>'
        f'<wpc:bg/><wpc:whole/>'
        f'{shapes_xml}'
        f'{conns_xml}'
        f'</wpc:wpc>'
        f'</a:graphicData>'
        f'</a:graphic>'
        f'</wp:inline>'
        f'</w:drawing>'
    )

    try:
        drawing_el = etree.fromstring(drawing_xml.encode('utf-8'))
    except etree.XMLSyntaxError:
        return False

    para = doc.add_paragraph()
    para.alignment = WD_ALIGN_PARAGRAPH.CENTER
    para.paragraph_format.space_before = Pt(8)
    para.paragraph_format.space_after  = Pt(8)
    run = para.add_run()
    run._r.append(drawing_el)
    return True
