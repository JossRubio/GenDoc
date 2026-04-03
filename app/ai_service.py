"""
ai_service.py — Thin Gemini client.

Responsibilities:
  - Validate API configuration (key, model name).
  - Serialise a RepoScan into the repo-context block included in prompts.
  - Execute a single call to Gemini and return the raw Markdown string.
  - Normalise every possible API/network error into ValueError or RuntimeError
    with a clear, user-facing Spanish message.

What does NOT live here:
  - Section lists (each generator owns them).
  - Prompt assembly (each generator owns that too).

Public API
----------
build_repo_context(repo_scan)  -> str
call_gemini(prompt)            -> str
"""

from __future__ import annotations

import os

from .repo_reader import RepoScan

# Maximum characters of repository content included in any prompt.
# Keeps requests within Gemini's context window and controls cost.
MAX_CONTEXT_CHARS = 350_000


# ── Repo serialiser (shared by all generators) ───────────────────────

def build_repo_context(repo_scan: RepoScan) -> str:
    """
    Serialise *repo_scan* into a Markdown block suitable for inclusion
    in a generation prompt.  Files that would push the total past
    ``MAX_CONTEXT_CHARS`` are listed but their content is omitted.
    """
    parts: list[str] = []

    parts.append("## Estructura del repositorio\n\n")
    for f in repo_scan.files:
        parts.append(f"- `{f.relative_path}`\n")
    parts.append("\n---\n\n## Contenido de los archivos\n\n")

    used_chars = sum(len(p) for p in parts)

    for f in repo_scan.files:
        lang = f.extension.lstrip(".") or "text"
        block = f"### `{f.relative_path}`\n\n```{lang}\n{f.content}\n```\n\n"
        if used_chars + len(block) > MAX_CONTEXT_CHARS:
            parts.append(
                f"### `{f.relative_path}`\n\n"
                "*[contenido omitido por límite de contexto]*\n\n"
            )
            continue
        parts.append(block)
        used_chars += len(block)

    return "".join(parts)


# ── Error helper ──────────────────────────────────────────────────────

def _friendly_api_error(exc: object) -> str:
    """Map a Gemini APIError HTTP code to a user-facing Spanish message."""
    code = getattr(exc, "code", None) or getattr(exc, "status_code", None)

    messages: dict[int, str] = {
        400: (
            "La solicitud al modelo fue rechazada (400). "
            "Verifica que LLM_MODEL en .env sea un nombre de modelo válido."
        ),
        401: (
            "La clave de API es inválida o no está autorizada (401). "
            "Revisa LLM_API_KEY en tu archivo .env."
        ),
        403: (
            "Sin permisos para usar este modelo (403). "
            "Verifica que tu clave de API tenga acceso a Gemini."
        ),
        429: (
            "Se superó la cuota de solicitudes al modelo (429). "
            "Espera unos minutos y vuelve a intentarlo, "
            "o revisa tu plan en Google AI Studio."
        ),
        500: (
            "Error interno del servidor de Google (500). "
            "El servicio puede estar temporalmente no disponible. "
            "Intenta de nuevo en unos minutos."
        ),
        503: (
            "El servicio de Gemini no está disponible en este momento (503). "
            "Intenta de nuevo más tarde."
        ),
    }

    if code in messages:
        return messages[code]

    return f"Error de la API de Gemini ({code}): {exc}"


# ── Fallback model chain ──────────────────────────────────────────────

# HTTP codes that indicate a model is unavailable or rate-limited.
# For these the next model in the fallback chain is tried automatically.
# Auth errors (401, 403) are NOT retried — switching models won't fix them.
_RETRYABLE_CODES = {404, 429, 503}

_FALLBACK_MODELS = [
    "gemini-3-flash-preview",
    "gemini-3.1-flash-lite-preview",
    "gemini-2.5-flash",
]


# ── Public API ────────────────────────────────────────────────────────

def call_gemini(prompt: str) -> str:
    """
    Send *prompt* to Gemini and return the response as a Markdown string.

    The primary model is read from ``LLM_MODEL`` in the environment.
    If that model returns a retryable error (404, 429, 503) the call is
    retried with each model in ``_FALLBACK_MODELS`` in order until one
    succeeds or all are exhausted.

    Configuration
    -------------
    LLM_API_KEY  — Google AI Studio API key (required).
    LLM_MODEL    — primary model identifier (default: ``gemini-3-flash-preview``).

    Raises
    ------
    ValueError   — Missing / invalid API key, empty model name.
    RuntimeError — All models failed, or a non-retryable API error occurred.
    """
    # ── Validate config ──────────────────────────────────────────────
    api_key = os.getenv("LLM_API_KEY", "").strip()
    if not api_key or api_key == "tu_api_key_aqui":
        raise ValueError(
            "LLM_API_KEY no está configurada. "
            "Abre el archivo .env y reemplaza 'tu_api_key_aqui' "
            "con tu clave de Google AI Studio."
        )

    primary = os.getenv("LLM_MODEL", "gemini-3-flash-preview").strip()
    if not primary:
        raise ValueError(
            "LLM_MODEL está vacío en el archivo .env. "
            "Usa un valor como 'gemini-2.5-flash'."
        )

    # Build ordered list: primary first, then fallbacks (skip duplicates)
    seen: set[str] = set()
    models_to_try: list[str] = []
    for m in [primary] + _FALLBACK_MODELS:
        if m not in seen:
            seen.add(m)
            models_to_try.append(m)

    # ── Call Gemini with fallback chain ──────────────────────────────
    # Imported here (not at module level) so the heavy SDK initialisation
    # only happens when the user actually clicks "Generar", not at startup.
    from google import genai                         # noqa: PLC0415
    from google.genai import errors as genai_errors  # noqa: PLC0415

    client = genai.Client(api_key=api_key)
    last_error: str = ""

    for model_name in models_to_try:
        try:
            response = client.models.generate_content(
                model=model_name, contents=prompt
            )
        except genai_errors.ClientError as exc:
            code = getattr(exc, "code", None) or getattr(exc, "status_code", None)
            if code in _RETRYABLE_CODES:
                last_error = f"[{model_name}] {_friendly_api_error(exc)}"
                continue  # try next model
            raise RuntimeError(_friendly_api_error(exc)) from exc
        except genai_errors.ServerError as exc:
            code = getattr(exc, "code", None) or getattr(exc, "status_code", None)
            if code in _RETRYABLE_CODES:
                last_error = f"[{model_name}] {_friendly_api_error(exc)}"
                continue
            raise RuntimeError(_friendly_api_error(exc)) from exc
        except (ConnectionError, TimeoutError, OSError) as exc:
            raise RuntimeError(
                "No se pudo conectar con la API de Gemini. "
                f"Verifica tu conexión a internet. Detalle: {exc}"
            ) from exc
        except Exception as exc:
            raise RuntimeError(f"Error inesperado al llamar al modelo: {exc}") from exc

        # ── Validate response ────────────────────────────────────────
        # response.text raises ValueError when content is blocked by safety filters.
        try:
            text = response.text
        except ValueError:
            finish_reason = "desconocido"
            try:
                finish_reason = str(response.candidates[0].finish_reason)
            except Exception:
                pass
            raise RuntimeError(
                f"El modelo rechazó generar el contenido (motivo: {finish_reason}). "
                "Esto ocurre cuando el contenido del repositorio activa los filtros "
                "de seguridad. Intenta con un repositorio diferente."
            )
        except AttributeError as exc:
            raise RuntimeError(
                f"La respuesta del modelo tiene un formato inesperado: {exc}"
            ) from exc

        if not text or not text.strip():
            raise RuntimeError(
                "El modelo devolvió una respuesta vacía. "
                "Revisa que el repositorio contenga archivos con código legible."
            )

        return text

    # All models in the chain exhausted
    raise RuntimeError(
        f"Todos los modelos disponibles fallaron. Último error: {last_error}"
    )
