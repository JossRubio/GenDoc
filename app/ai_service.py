"""
ai_service.py — Multi-provider LLM client.

Supported providers
-------------------
  google    — Google AI Studio (Gemini models)
  anthropic — Anthropic (Claude models)
  openai    — OpenAI (GPT / o-series models)

Public API
----------
detect_provider(api_key)                      -> str          ("google" | "anthropic" | "openai")
list_models(api_key, provider)                -> list[dict]
call_llm(prompt, *, api_key_override, model_override, provider_override) -> str
build_repo_context(repo_scan)                 -> str
"""

from __future__ import annotations

import os

from .repo_reader import RepoScan

MAX_CONTEXT_CHARS = 350_000

# OpenAI model ID prefixes that support chat/text generation
_OPENAI_CHAT_PREFIXES = ("gpt-", "o1", "o3", "o4", "chatgpt-")

# Anthropic models that support text generation (display name suffix filter)
# We rely on the SDK listing, so no manual list needed.

# Azure AI default API version (used when AZURE_AI_API_VERSION is not set)
_AZURE_DEFAULT_API_VERSION = "2025-01-01-preview"

# Google fallback chain (tried in order when primary returns a retryable error)
_GOOGLE_FALLBACK_MODELS = [
    "gemini-3-flash-preview",
    "gemini-3.1-flash-lite-preview",
    "gemini-2.5-flash",
]
_GOOGLE_RETRYABLE_CODES = {404, 429, 503}


# ── Azure AI config helper ────────────────────────────────────────────

def _get_azure_config() -> tuple[str, str | None, str, bool]:
    """
    Parse AZURE_AI_ENDPOINT and return
    (openai_base_url, project_base_url, api_version, is_foundry).

    openai_base_url  → used by openai.OpenAI / AzureOpenAI for chat completions.
    project_base_url → used by the management API to list deployments (Foundry only).

    is_foundry=True  → Azure AI Foundry project endpoint (.services.ai.azure.com)
    is_foundry=False → Classic Azure OpenAI endpoint (.openai.azure.com)

    Accepts the full "Target URI" from Foundry (e.g. ending in /openai/v1/responses)
    and automatically extracts the correct base URL.

    Supports both AZURE_AI_ENDPOINT (new) and AZURE_OPENAI_ENDPOINT (legacy).
    Raises ValueError if neither is set.
    """
    raw = (
        os.getenv("AZURE_AI_ENDPOINT", "").strip()
        or os.getenv("AZURE_OPENAI_ENDPOINT", "").strip()   # backward compat
    )
    if not raw:
        raise ValueError(
            "AZURE_AI_ENDPOINT no está configurado en el archivo .env. "
            "Pega el 'Target URI' de tu deployment en Azure AI Foundry."
        )

    api_version = (
        os.getenv("AZURE_AI_API_VERSION", "").strip()
        or os.getenv("AZURE_OPENAI_API_VERSION", "").strip()  # backward compat
        or _AZURE_DEFAULT_API_VERSION
    )

    # Azure AI Foundry project endpoint — contains /openai/v1/ in the path.
    if "/openai/v1/" in raw:
        openai_base  = raw[: raw.index("/openai/v1/") + len("/openai/v1/")]
        project_base = raw[: raw.index("/openai/v1/")]   # everything before /openai/v1/
        if not project_base.endswith("/"):
            project_base += "/"
        return openai_base, project_base, api_version, True

    # Classic Azure OpenAI endpoint (.openai.azure.com)
    return raw.rstrip("/") + "/", None, api_version, False


# ── Provider detection ────────────────────────────────────────────────

def detect_provider(api_key: str) -> str:
    """
    Guess the provider from the API key format.

    Returns ``"google"``, ``"anthropic"``, or ``"openai"``.
    Falls back to ``"google"`` when the key does not match a known pattern.
    """
    key = (api_key or "").strip()
    if key.startswith("sk-ant-"):
        return "anthropic"
    if key.startswith("sk-"):
        return "openai"
    return "google"


# ── Repo serialiser ───────────────────────────────────────────────────

def build_repo_context(repo_scan: RepoScan) -> str:
    parts: list[str] = []
    parts.append("## Estructura del repositorio\n\n")
    for f in repo_scan.files:
        parts.append(f"- `{f.relative_path}`\n")
    parts.append("\n---\n\n## Contenido de los archivos\n\n")
    used_chars = sum(len(p) for p in parts)
    for f in repo_scan.files:
        lang  = f.extension.lstrip(".") or "text"
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


# ── Google helpers ────────────────────────────────────────────────────

def _google_friendly_error(exc: object) -> str:
    code = getattr(exc, "code", None) or getattr(exc, "status_code", None)
    messages: dict[int, str] = {
        400: "La solicitud fue rechazada (400). Verifica que el modelo sea válido.",
        401: "API key de Google inválida o no autorizada (401).",
        403: "Sin permisos para usar este modelo de Google (403).",
        429: "Cuota de solicitudes superada en Google AI (429). Espera unos minutos.",
        500: "Error interno del servidor de Google (500). Intenta de nuevo.",
        503: "Servicio de Google no disponible (503). Intenta más tarde.",
    }
    return messages.get(code, f"Error Google API ({code}): {exc}")


def _list_google(api_key: str) -> list[dict]:
    from google import genai
    from google.genai import errors as genai_errors
    try:
        client = genai.Client(api_key=api_key)
        result = []
        for m in client.models.list():
            supported = list(getattr(m, "supported_actions", None) or [])
            if "generateContent" not in supported:
                continue
            raw  = getattr(m, "name", "") or ""
            mid  = raw.removeprefix("models/")
            if not mid:
                continue
            display = getattr(m, "display_name", None) or mid
            result.append({"id": mid, "display_name": display})
        return result
    except genai_errors.ClientError as exc:
        raise ValueError(_google_friendly_error(exc)) from exc
    except Exception as exc:
        raise RuntimeError(f"Error al listar modelos de Google: {exc}") from exc


def _call_google(prompt: str, api_key: str, primary_model: str) -> str:
    from google import genai
    from google.genai import errors as genai_errors

    seen: set[str] = set()
    models_to_try: list[str] = []
    for m in [primary_model] + _GOOGLE_FALLBACK_MODELS:
        if m not in seen:
            seen.add(m)
            models_to_try.append(m)

    client     = genai.Client(api_key=api_key)
    last_error = ""

    for model_name in models_to_try:
        try:
            response = client.models.generate_content(model=model_name, contents=prompt)
        except genai_errors.ClientError as exc:
            code = getattr(exc, "code", None) or getattr(exc, "status_code", None)
            if code in _GOOGLE_RETRYABLE_CODES:
                last_error = f"[{model_name}] {_google_friendly_error(exc)}"
                continue
            raise RuntimeError(_google_friendly_error(exc)) from exc
        except genai_errors.ServerError as exc:
            code = getattr(exc, "code", None) or getattr(exc, "status_code", None)
            if code in _GOOGLE_RETRYABLE_CODES:
                last_error = f"[{model_name}] {_google_friendly_error(exc)}"
                continue
            raise RuntimeError(_google_friendly_error(exc)) from exc
        except (ConnectionError, TimeoutError, OSError) as exc:
            raise RuntimeError(
                f"No se pudo conectar con Google AI. Detalle: {exc}"
            ) from exc
        except Exception as exc:
            raise RuntimeError(f"Error inesperado (Google): {exc}") from exc

        try:
            text = response.text
        except ValueError:
            finish = "desconocido"
            try:
                finish = str(response.candidates[0].finish_reason)
            except Exception:
                pass
            raise RuntimeError(
                f"Google rechazó el contenido (motivo: {finish}). "
                "El repositorio puede haber activado los filtros de seguridad."
            )
        except AttributeError as exc:
            raise RuntimeError(f"Respuesta de Google con formato inesperado: {exc}") from exc

        if not text or not text.strip():
            raise RuntimeError("Google devolvió una respuesta vacía.")
        return text

    raise RuntimeError(f"Todos los modelos de Google fallaron. Último error: {last_error}")


# ── Anthropic helpers ─────────────────────────────────────────────────

def _list_anthropic(api_key: str) -> list[dict]:
    try:
        import anthropic as _anthropic
    except ImportError:
        raise RuntimeError(
            "El paquete 'anthropic' no está instalado. "
            "Ejecuta: pip install anthropic"
        )
    try:
        client = _anthropic.Anthropic(api_key=api_key)
        result = []
        for m in client.models.list():
            mid     = getattr(m, "id", None) or ""
            display = getattr(m, "display_name", None) or mid
            if mid:
                result.append({"id": mid, "display_name": display})
        return result
    except _anthropic.AuthenticationError as exc:
        raise ValueError(f"API key de Anthropic inválida o no autorizada: {exc}") from exc
    except Exception as exc:
        raise RuntimeError(f"Error al listar modelos de Anthropic: {exc}") from exc


def _call_anthropic(prompt: str, api_key: str, model: str) -> str:
    try:
        import anthropic as _anthropic
    except ImportError:
        raise RuntimeError(
            "El paquete 'anthropic' no está instalado. "
            "Ejecuta: pip install anthropic"
        )
    try:
        client  = _anthropic.Anthropic(api_key=api_key)
        message = client.messages.create(
            model=model,
            max_tokens=8096,
            messages=[{"role": "user", "content": prompt}],
        )
        text = message.content[0].text if message.content else ""
        if not text or not text.strip():
            raise RuntimeError("Anthropic devolvió una respuesta vacía.")
        return text
    except _anthropic.AuthenticationError as exc:
        raise RuntimeError(f"API key de Anthropic inválida o no autorizada: {exc}") from exc
    except _anthropic.RateLimitError as exc:
        raise RuntimeError(f"Cuota de Anthropic superada (429): {exc}") from exc
    except _anthropic.APIStatusError as exc:
        raise RuntimeError(f"Error de la API de Anthropic ({exc.status_code}): {exc}") from exc
    except (ConnectionError, TimeoutError, OSError) as exc:
        raise RuntimeError(f"No se pudo conectar con Anthropic. Detalle: {exc}") from exc
    except Exception as exc:
        raise RuntimeError(f"Error inesperado (Anthropic): {exc}") from exc


# ── OpenAI helpers ────────────────────────────────────────────────────

def _list_openai(api_key: str) -> list[dict]:
    try:
        import openai as _openai
    except ImportError:
        raise RuntimeError(
            "El paquete 'openai' no está instalado. "
            "Ejecuta: pip install openai"
        )
    try:
        client = _openai.OpenAI(api_key=api_key)
        result = []
        for m in client.models.list():
            mid = getattr(m, "id", None) or ""
            if any(mid.startswith(p) for p in _OPENAI_CHAT_PREFIXES):
                result.append({"id": mid, "display_name": mid})
        result.sort(key=lambda x: x["id"])
        return result
    except _openai.AuthenticationError as exc:
        raise ValueError(f"API key de OpenAI inválida o no autorizada: {exc}") from exc
    except Exception as exc:
        raise RuntimeError(f"Error al listar modelos de OpenAI: {exc}") from exc


def _call_openai(prompt: str, api_key: str, model: str) -> str:
    try:
        import openai as _openai
    except ImportError:
        raise RuntimeError(
            "El paquete 'openai' no está instalado. "
            "Ejecuta: pip install openai"
        )
    try:
        client   = _openai.OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
        )
        text = response.choices[0].message.content if response.choices else ""
        if not text or not text.strip():
            raise RuntimeError("OpenAI devolvió una respuesta vacía.")
        return text
    except _openai.AuthenticationError as exc:
        raise RuntimeError(f"API key de OpenAI inválida o no autorizada: {exc}") from exc
    except _openai.RateLimitError as exc:
        raise RuntimeError(f"Cuota de OpenAI superada (429): {exc}") from exc
    except _openai.APIStatusError as exc:
        raise RuntimeError(f"Error de la API de OpenAI ({exc.status_code}): {exc}") from exc
    except (ConnectionError, TimeoutError, OSError) as exc:
        raise RuntimeError(f"No se pudo conectar con OpenAI. Detalle: {exc}") from exc
    except Exception as exc:
        raise RuntimeError(f"Error inesperado (OpenAI): {exc}") from exc


# ── Azure AI helpers ──────────────────────────────────────────────────

def _azure_client(api_key: str):
    """
    Build and return the correct OpenAI client for the configured Azure endpoint.

    Azure AI Foundry project endpoints → openai.OpenAI(base_url=...)
    Classic Azure OpenAI endpoints     → openai.AzureOpenAI(azure_endpoint=...)
    """
    try:
        import openai as _openai
    except ImportError:
        raise RuntimeError(
            "El paquete 'openai' no está instalado. "
            "Ejecuta: pip install openai"
        )
    openai_base, _project_base, api_version, is_foundry = _get_azure_config()
    if is_foundry:
        return _openai.OpenAI(base_url=openai_base, api_key=api_key)
    return _openai.AzureOpenAI(
        azure_endpoint=openai_base, api_key=api_key, api_version=api_version
    )


def _list_azure(api_key: str) -> list[dict]:
    """
    List deployments from Azure AI Foundry using the management REST API.

    For Foundry endpoints, calls:
      GET {project_base_url}deployments?api-version={version}
    which returns all models deployed in the project (gpt-4.1, DeepSeek-V3.2, etc.).

    For classic Azure OpenAI endpoints, falls back to openai client models.list().
    """
    import httpx

    openai_base, project_base, api_version, is_foundry = _get_azure_config()

    if is_foundry:
        # Azure AI Foundry project-scoped endpoints (services.ai.azure.com) do not
        # expose a deployment-listing REST API accessible with an API key alone.
        # Management operations require Azure AD / ARM credentials.
        # Return an empty list so the UI falls back to the manual deployment name input.
        return []

    # Classic Azure OpenAI — use the OpenAI SDK models endpoint
    try:
        import openai as _openai
    except ImportError:
        raise RuntimeError("El paquete 'openai' no está instalado.")
    try:
        client = _azure_client(api_key)
        result = []
        for m in client.models.list():
            mid = getattr(m, "id", None) or ""
            if mid:
                result.append({"id": mid, "display_name": mid})
        return result
    except ValueError:
        raise
    except _openai.AuthenticationError as exc:
        raise ValueError(f"API key de Azure AI inválida o no autorizada: {exc}") from exc
    except Exception as exc:
        raise RuntimeError(f"Error al listar modelos de Azure AI: {exc}") from exc


def _validate_azure(api_key: str) -> None:
    """
    Validate an Azure AI Foundry key by making a lightweight HEAD/GET request.

    For Foundry endpoints: GET {openai_base}/models
      - 401 / 403 → key rejected → raises ValueError
      - Anything else (including 404) → key accepted, endpoint just doesn't exist

    For classic Azure OpenAI: delegates to _list_azure (SDK validates the key).
    Raises ValueError on auth error, RuntimeError on connectivity error.
    """
    import httpx

    openai_base, _, _, is_foundry = _get_azure_config()

    if not is_foundry:
        _list_azure(api_key)   # raises ValueError on auth error
        return

    url = openai_base.rstrip("/") + "/models"
    try:
        r = httpx.get(url, headers={"api-key": api_key}, timeout=10)
        if r.status_code in (401, 403):
            raise ValueError(
                f"API key de Azure AI inválida o no autorizada ({r.status_code})."
            )
        # 404 or anything else → key was accepted by the server
    except httpx.RequestError as exc:
        raise RuntimeError(f"No se pudo conectar con Azure AI: {exc}") from exc


def _call_azure(prompt: str, api_key: str, model: str) -> str:
    try:
        import openai as _openai
    except ImportError:
        raise RuntimeError(
            "El paquete 'openai' no está instalado. "
            "Ejecuta: pip install openai"
        )
    try:
        client = _azure_client(api_key)
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
        )
        text = response.choices[0].message.content if response.choices else ""
        if not text or not text.strip():
            raise RuntimeError("Azure devolvió una respuesta vacía.")
        return text
    except _openai.AuthenticationError as exc:
        raise RuntimeError(f"API key de Azure inválida o no autorizada: {exc}") from exc
    except _openai.RateLimitError as exc:
        raise RuntimeError(f"Cuota de Azure superada (429): {exc}") from exc
    except _openai.APIStatusError as exc:
        raise RuntimeError(f"Error de la API de Azure ({exc.status_code}): {exc}") from exc
    except (ConnectionError, TimeoutError, OSError) as exc:
        raise RuntimeError(f"No se pudo conectar con Azure. Detalle: {exc}") from exc
    except (ValueError, RuntimeError):
        raise
    except Exception as exc:
        raise RuntimeError(f"Error inesperado (Azure AI): {exc}") from exc


# ── Public API ────────────────────────────────────────────────────────

def validate_key(api_key: str, provider: str | None = None) -> list[dict]:
    """
    Validate *api_key* for the given provider and return available models.

    For Azure AI Foundry: performs a lightweight HTTP test and returns [].
    For all other providers: validates by listing models and returns them.

    Raises ValueError on auth error, RuntimeError on network/unexpected error.
    """
    prov = (provider or detect_provider(api_key)).lower()
    if prov == "azure":
        _validate_azure(api_key)
        return []
    return list_models(api_key, prov)


def list_models(api_key: str, provider: str | None = None) -> list[dict]:
    """
    Return models available to *api_key* that support text generation.

    Parameters
    ----------
    api_key  : str
        Provider API key.
    provider : "google" | "anthropic" | "openai" | None
        When None, auto-detected from the key format.

    Each entry: ``{"id": "model-id", "display_name": "Human Name"}``.

    Raises
    ------
    ValueError   — API key rejected (auth error).
    RuntimeError — Network or unexpected error.
    """
    prov = (provider or detect_provider(api_key)).lower()
    if prov == "anthropic":
        return _list_anthropic(api_key)
    if prov == "openai":
        return _list_openai(api_key)
    if prov == "azure":
        return _list_azure(api_key)
    return _list_google(api_key)


def call_llm(
    prompt: str,
    *,
    api_key_override: str | None = None,
    model_override:   str | None = None,
    provider_override: str | None = None,
) -> str:
    """
    Send *prompt* to the configured LLM and return the response as a string.

    Provider resolution order:
      1. *provider_override* (explicit, from UI)
      2. Auto-detected from *api_key_override* (if provided)
      3. ``"google"`` (server default)

    API key resolution order:
      1. *api_key_override*
      2. ``LLM_API_KEY`` env variable

    Model resolution order:
      1. *model_override*
      2. ``LLM_MODEL`` env variable (Google only)
      3. Provider default

    Raises
    ------
    ValueError   — Missing / invalid API key.
    RuntimeError — All models failed or non-retryable error.
    """
    api_key = (api_key_override or "").strip() or os.getenv("LLM_API_KEY", "").strip()
    if not api_key or api_key == "tu_api_key_aqui":
        raise ValueError(
            "LLM_API_KEY no está configurada. "
            "Abre el archivo .env o ingresa tu API key en la interfaz."
        )

    # Resolve provider
    if provider_override:
        provider = provider_override.lower()
    elif api_key_override:
        provider = detect_provider(api_key_override)
    else:
        provider = "google"

    model = (model_override or "").strip()

    if provider == "anthropic":
        if not model:
            model = "claude-sonnet-4-5"
        return _call_anthropic(prompt, api_key, model)

    if provider == "openai":
        if not model:
            model = "gpt-4o"
        return _call_openai(prompt, api_key, model)

    if provider == "azure":
        if not model:
            model = os.getenv("LLM_MODEL", "").strip() or "gpt-4o"
        return _call_azure(prompt, api_key, model)

    # Google (default)
    if not model:
        model = os.getenv("LLM_MODEL", "gemini-3-flash-preview").strip() or "gemini-3-flash-preview"
    return _call_google(prompt, api_key, model)


# Keep old name as alias so any direct callers don't break
def call_gemini(
    prompt: str,
    *,
    api_key_override: str | None = None,
    model_override:   str | None = None,
) -> str:
    return call_llm(
        prompt,
        api_key_override=api_key_override,
        model_override=model_override,
        provider_override=None,
    )
