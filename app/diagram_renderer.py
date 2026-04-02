"""
diagram_renderer.py — Render Mermaid diagrams via mermaid.ink.

Provides PNG and SVG rendering. Only the Python standard library is required
(urllib, base64). Callers should catch RuntimeError and fall back gracefully
if the remote service is unavailable.
"""

from __future__ import annotations

import base64
import urllib.error
import urllib.request

_MERMAID_INK = "https://mermaid.ink"
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


def _fetch(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "GenDoc/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=_TIMEOUT) as resp:
            if resp.status != 200:
                raise RuntimeError(
                    f"mermaid.ink respondió con HTTP {resp.status}."
                )
            return resp.read()
    except urllib.error.URLError as exc:
        raise RuntimeError(
            f"No se pudo conectar a mermaid.ink: {exc.reason}"
        ) from exc


# ── Public API ────────────────────────────────────────────────────────

def render(mermaid_code: str, primary_hex: str) -> bytes:
    """
    Render *mermaid_code* to PNG bytes via the public mermaid.ink service.

    Parameters
    ----------
    mermaid_code : str
        Raw Mermaid diagram code (without any init directive).
    primary_hex  : str
        Hex colour without '#', e.g. '2D3A8C'.

    Returns
    -------
    bytes
        Raw PNG image data.

    Raises
    ------
    RuntimeError
        If the HTTP request fails or the service returns a non-200 status.
    """
    b64 = base64.urlsafe_b64encode(
        _build_full_code(mermaid_code, primary_hex).encode("utf-8")
    ).decode("ascii")
    return _fetch(f"{_MERMAID_INK}/img/{b64}")


def render_svg(mermaid_code: str, primary_hex: str) -> bytes:
    """
    Render *mermaid_code* to SVG bytes via the public mermaid.ink service.

    The returned SVG can be embedded in Word documents as a vector diagram
    (editable via right-click → Convert to Shapes in Word 2016+).

    Parameters
    ----------
    mermaid_code : str
        Raw Mermaid diagram code (without any init directive).
    primary_hex  : str
        Hex colour without '#', e.g. '2D3A8C'.

    Returns
    -------
    bytes
        Raw SVG data (UTF-8 encoded XML).

    Raises
    ------
    RuntimeError
        If the HTTP request fails or the service returns a non-200 status.
    """
    b64 = base64.urlsafe_b64encode(
        _build_full_code(mermaid_code, primary_hex).encode("utf-8")
    ).decode("ascii")
    return _fetch(f"{_MERMAID_INK}/svg/{b64}")
