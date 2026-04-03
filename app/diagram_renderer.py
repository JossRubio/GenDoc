"""
diagram_renderer.py — Render Mermaid diagrams via external services.

Rendering strategy:
  1. mermaid.ink GET — themed (%%{init}%% + primary colour)
       → if HTTP 4xx (URL too long / bad syntax): retry plain (no init, shorter URL)
       → if connection error (service unreachable): skip to step 2 immediately
  2. kroki.io POST — code in request body, no URL-length limit, independent service

Total worst-case wait: 2 × 8 s = 16 s per diagram (both services unreachable).
Previously this was up to 60 s (3 attempts × 20 s).

Only the Python standard library is required (urllib, base64).
Callers should catch RuntimeError if both services fail.
"""

from __future__ import annotations

import base64
import urllib.error
import urllib.request

_MERMAID_INK = "https://mermaid.ink"
_KROKI       = "https://kroki.io"
_TIMEOUT     = 8   # seconds per request


# ── Colour helpers ────────────────────────────────────────────────────

def _luminance(hex_color: str) -> float:
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return (0.299 * r + 0.587 * g + 0.114 * b) / 255.0


# ── Internal helpers ──────────────────────────────────────────────────

def _build_full_code(mermaid_code: str, primary_hex: str) -> str:
    """Prepend the %%{init:...}%% theme directive to *mermaid_code*."""
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


def _b64(code: str) -> str:
    return base64.urlsafe_b64encode(code.encode("utf-8")).decode("ascii")


def _get_mermaid(code: str, endpoint: str) -> bytes:
    """
    GET from mermaid.ink/{endpoint}/{b64}.

    Raises
    ------
    RuntimeError("4xx: …")       — service rejected the request (bad URL / syntax)
    RuntimeError("unreachable")  — connection-level failure (timeout, DNS, etc.)
    """
    url = f"{_MERMAID_INK}/{endpoint}/{_b64(code)}"
    req = urllib.request.Request(url, headers={"User-Agent": "GenDoc/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=_TIMEOUT) as resp:
            return resp.read()
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"4xx: mermaid.ink HTTP {exc.code}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"unreachable: {exc.reason}") from exc


def _post_kroki(mermaid_code: str, fmt: str) -> bytes:
    """POST to kroki.io — code in body, no URL-length constraint."""
    url  = f"{_KROKI}/mermaid/{fmt}"
    data = mermaid_code.strip().encode("utf-8")
    req  = urllib.request.Request(
        url, data=data,
        headers={"Content-Type": "text/plain", "Accept": f"image/{fmt}",
                 "User-Agent": "GenDoc/1.0"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=_TIMEOUT) as resp:
            return resp.read()
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"kroki.io HTTP {exc.code}: {exc.reason}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"No se pudo conectar a kroki.io: {exc.reason}") from exc


def _render(mermaid_code: str, primary_hex: str, endpoint: str) -> bytes:
    """
    Shared render logic for PNG (``img``) and SVG (``svg``) endpoints.

    Strategy
    --------
    1. mermaid.ink themed URL
       - HTTP 4xx → immediately retry with plain URL (shorter, avoids 400)
       - Connection error → skip mermaid.ink entirely and go to step 2
    2. kroki.io POST (independent service, code in body)
    """
    # Step 1 — mermaid.ink
    try:
        return _get_mermaid(_build_full_code(mermaid_code, primary_hex), endpoint)
    except RuntimeError as exc:
        err = str(exc)
        if err.startswith("4xx"):
            # Service is up but rejected the URL — retry with shorter plain URL
            try:
                return _get_mermaid(mermaid_code.strip(), endpoint)
            except RuntimeError:
                pass  # plain also failed → fall through to kroki
        # Connection error: mermaid.ink unreachable → skip straight to kroki

    # Step 2 — kroki.io
    fmt = "png" if endpoint == "img" else "svg"
    return _post_kroki(mermaid_code, fmt)


# ── Public API ────────────────────────────────────────────────────────

def render(mermaid_code: str, primary_hex: str) -> bytes:
    """
    Render *mermaid_code* to PNG bytes.

    Raises RuntimeError if both mermaid.ink and kroki.io fail.
    """
    return _render(mermaid_code, primary_hex, "img")


def render_svg(mermaid_code: str, primary_hex: str) -> bytes:
    """
    Render *mermaid_code* to SVG bytes.

    Raises RuntimeError if both mermaid.ink and kroki.io fail.
    """
    return _render(mermaid_code, primary_hex, "svg")
