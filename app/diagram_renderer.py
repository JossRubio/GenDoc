"""
diagram_renderer.py — Render Mermaid diagrams with automatic fallback chain.

Rendering strategy (PNG and SVG):
  1. mermaid.ink GET  — themed (%%{init}%% directive + primary colour)
  2. mermaid.ink GET  — plain (no init directive; shorter URL, avoids 400 on long diagrams)
  3. kroki.io   POST  — fallback service; code in request body, no URL-length limit

Only the Python standard library is required (urllib, base64).
Callers should catch RuntimeError and fall back to a code block if every
strategy fails.
"""

from __future__ import annotations

import base64
import urllib.error
import urllib.request

_MERMAID_INK = "https://mermaid.ink"
_KROKI       = "https://kroki.io"
_TIMEOUT     = 20  # seconds per request


# ── Colour helpers ────────────────────────────────────────────────────

def _luminance(hex_color: str) -> float:
    """
    Return the perceived luminance of a hex colour (0.0 = black, 1.0 = white).
    Uses the ITU-R BT.601 weighted formula.
    """
    h = hex_color.lstrip("#")
    r = int(h[0:2], 16)
    g = int(h[2:4], 16)
    b = int(h[4:6], 16)
    return (0.299 * r + 0.587 * g + 0.114 * b) / 255.0


# ── Internal helpers ──────────────────────────────────────────────────

def _build_full_code(mermaid_code: str, primary_hex: str) -> str:
    """Return mermaid_code with the %%{init:...}%% theme directive prepended."""
    text_hex = "#000000" if _luminance(primary_hex) > 0.5 else "#ffffff"
    init = (
        f"%%{{init: {{'theme': 'base', 'themeVariables': {{"
        f"'primaryColor': '#{primary_hex}', "
        f"'primaryTextColor': '{text_hex}', "
        f"'primaryBorderColor': '#{primary_hex}', "
        f"'lineColor': '#{primary_hex}', "
        f"'clusterBkg': '#f4f4f8', "
        f"'titleColor': '#{primary_hex}'"
        f"}}}}}}%%\n"
    )
    return init + mermaid_code.strip()


def _get(url: str) -> bytes:
    """HTTP GET via mermaid.ink."""
    req = urllib.request.Request(url, headers={"User-Agent": "GenDoc/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=_TIMEOUT) as resp:
            if resp.status != 200:
                raise RuntimeError(f"mermaid.ink respondió con HTTP {resp.status}.")
            return resp.read()
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"mermaid.ink HTTP {exc.code}: {exc.reason}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"No se pudo conectar a mermaid.ink: {exc.reason}") from exc


def _post_kroki(mermaid_code: str, fmt: str) -> bytes:
    """HTTP POST to kroki.io — code in body, no URL-length constraint."""
    url  = f"{_KROKI}/mermaid/{fmt}"
    data = mermaid_code.strip().encode("utf-8")
    req  = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "text/plain", "Accept": f"image/{fmt}",
                 "User-Agent": "GenDoc/1.0"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=_TIMEOUT) as resp:
            if resp.status != 200:
                raise RuntimeError(f"kroki.io respondió con HTTP {resp.status}.")
            return resp.read()
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"kroki.io HTTP {exc.code}: {exc.reason}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"No se pudo conectar a kroki.io: {exc.reason}") from exc


def _b64(code: str) -> str:
    return base64.urlsafe_b64encode(code.encode("utf-8")).decode("ascii")


# ── Public API ────────────────────────────────────────────────────────

def render(mermaid_code: str, primary_hex: str) -> bytes:
    """
    Render *mermaid_code* to PNG bytes.

    Tries three strategies in order, raising RuntimeError only if all fail:
      1. mermaid.ink GET with %%{init}%% theme directive (themed PNG)
      2. mermaid.ink GET without init directive   (shorter URL)
      3. kroki.io POST                            (code in body, no URL limit)

    Parameters
    ----------
    mermaid_code : str
        Raw Mermaid diagram code (without any init directive).
    primary_hex  : str
        Hex colour without '#', e.g. '2D3A8C'.
    """
    last_error = ""

    # 1 — mermaid.ink with theme
    try:
        return _get(f"{_MERMAID_INK}/img/{_b64(_build_full_code(mermaid_code, primary_hex))}")
    except RuntimeError as exc:
        last_error = str(exc)

    # 2 — mermaid.ink without theme init (shorter URL)
    try:
        return _get(f"{_MERMAID_INK}/img/{_b64(mermaid_code.strip())}")
    except RuntimeError as exc:
        last_error = str(exc)

    # 3 — kroki.io POST
    try:
        return _post_kroki(mermaid_code, "png")
    except RuntimeError as exc:
        last_error = str(exc)

    raise RuntimeError(last_error)


def render_svg(mermaid_code: str, primary_hex: str) -> bytes:
    """
    Render *mermaid_code* to SVG bytes.

    Same three-strategy fallback chain as ``render()``.
    The returned SVG can be embedded in Word documents as a vector diagram
    (editable via right-click → Convert to Shapes in Word 2016+).

    Parameters
    ----------
    mermaid_code : str
        Raw Mermaid diagram code (without any init directive).
    primary_hex  : str
        Hex colour without '#', e.g. '2D3A8C'.
    """
    last_error = ""

    # 1 — mermaid.ink with theme
    try:
        return _get(f"{_MERMAID_INK}/svg/{_b64(_build_full_code(mermaid_code, primary_hex))}")
    except RuntimeError as exc:
        last_error = str(exc)

    # 2 — mermaid.ink without theme init
    try:
        return _get(f"{_MERMAID_INK}/svg/{_b64(mermaid_code.strip())}")
    except RuntimeError as exc:
        last_error = str(exc)

    # 3 — kroki.io POST
    try:
        return _post_kroki(mermaid_code, "svg")
    except RuntimeError as exc:
        last_error = str(exc)

    raise RuntimeError(last_error)
