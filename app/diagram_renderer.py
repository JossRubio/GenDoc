"""
diagram_renderer.py — Render Mermaid diagrams to PNG using mermaid.ink.

Only the Python standard library is required (urllib, base64).
Callers should catch RuntimeError and fall back to a code block if the
remote service is unavailable.
"""

from __future__ import annotations

import base64
import urllib.error
import urllib.request

_MERMAID_INK = "https://mermaid.ink/img"
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


# ── Public API ────────────────────────────────────────────────────────

def render(mermaid_code: str, primary_hex: str) -> bytes:
    """
    Render *mermaid_code* to PNG bytes via the public mermaid.ink service.

    The diagram nodes are styled with *primary_hex* as the fill colour.
    Foreground text colour (black or white) is chosen automatically based
    on the perceived luminance of *primary_hex* so labels remain readable.

    Parameters
    ----------
    mermaid_code : str
        Raw Mermaid diagram code (without any init directive — this function
        prepends one automatically).
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
    # Choose readable text colour based on background luminance
    text_hex = "#000000" if _luminance(primary_hex) > 0.5 else "#ffffff"

    # Mermaid init directive — overrides the default theme with palette colours
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

    full_code = init + mermaid_code.strip()

    # mermaid.ink expects URL-safe base64 in the path segment
    b64  = base64.urlsafe_b64encode(full_code.encode("utf-8")).decode("ascii")
    url  = f"{_MERMAID_INK}/{b64}"
    req  = urllib.request.Request(url, headers={"User-Agent": "GenDoc/1.0"})

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
