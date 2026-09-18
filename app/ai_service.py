"""
ai_service.py — Multi-provider LLM client.

Supported providers
-------------------
  google    — Google AI Studio (Gemini models)
  anthropic — Anthropic (Claude models)
  openai    — OpenAI (GPT / o-series models)
  custom    — Any model server reachable at a user-supplied endpoint.

The "custom" provider is not tied to a vendor: what matters is the *API
format* the server speaks, not who made the model behind it.

  openai    — OpenAI-compatible wire format. The de-facto standard, spoken by
              Azure AI Foundry / Azure OpenAI, DeepSeek, Moonshot (Kimi),
              Qwen/DashScope, Mistral, Groq, Together, OpenRouter, vLLM,
              Ollama, LM Studio and most corporate gateways.
  anthropic — Anthropic Messages format (a proxy or gateway in front of Claude).
  google    — Google Gemini generateContent format (e.g. a Vertex-style proxy).

The format is auto-detected from the endpoint host and can be overridden
explicitly from the UI. See _detect_endpoint_format() / _get_endpoint_config().

Public API
----------
detect_provider(api_key)                      -> str          ("google" | "anthropic" | "openai")
list_models(api_key, provider, custom_endpoint, custom_format)  -> list[dict]
call_llm(prompt, *, api_key_override, model_override, provider_override,
         custom_endpoint_override, custom_format_override)     -> str
build_repo_context(repo_scan)                 -> str
"""

from __future__ import annotations

import os
from urllib.parse import urlparse

from .repo_reader import RepoScan

MAX_CONTEXT_CHARS = 350_000

# OpenAI model ID prefixes that support chat/text generation
_OPENAI_CHAT_PREFIXES = ("gpt-", "o1", "o3", "o4", "chatgpt-")

# Anthropic models that support text generation (display name suffix filter)
# We rely on the SDK listing, so no manual list needed.

# API formats a custom endpoint can speak.
CUSTOM_FORMATS = ("openai", "anthropic", "google")

# Azure OpenAI default API version (used when AZURE_AI_API_VERSION is not set)
_AZURE_DEFAULT_API_VERSION = "2025-01-01-preview"

# Hosts that speak the Anthropic Messages format.
_ANTHROPIC_HOSTS = ("anthropic.com",)

# Hosts that speak the Google generateContent format.
_GOOGLE_HOSTS = ("generativelanguage.googleapis.com", "aiplatform.googleapis.com")

# Operation paths users often paste straight from a provider console
# ("Target URI"). They are stripped to recover the base URL.
_ENDPOINT_CALL_SUFFIXES = (
    "/chat/completions", "/responses", "/completions",
    "/embeddings", "/messages", "/generateContent",
)

# Curated models offered when the endpoint is an Azure AI Foundry project,
# whose API does not expose a deployment listing with an API key alone.
_FOUNDRY_RECOMMENDED_MODELS: list[dict] = [
    {"id": "DeepSeek-V4-Pro", "display_name": "DeepSeek-V4-Pro"},
    {"id": "DeepSeek-V3.2",   "display_name": "DeepSeek-V3.2"},
]

# Google fallback chain (tried in order when primary returns a retryable error)
_GOOGLE_FALLBACK_MODELS = [
    "gemini-3-flash-preview",
    "gemini-3.1-flash-lite-preview",
    "gemini-2.5-flash",
]
_GOOGLE_RETRYABLE_CODES = {404, 429, 503}


# ── Custom endpoint helpers ───────────────────────────────────────────

def _detect_endpoint_format(url: str) -> str:
    """
    Guess which API format *url* speaks, from its host and path.

    Returns one of ``CUSTOM_FORMATS``. Defaults to ``"openai"`` because the
    OpenAI wire format is what almost every model server exposes — including
    servers hosting DeepSeek, Kimi, Qwen, Llama or Mistral models.
    """
    host = (urlparse(url).hostname or "").lower()
    path = (urlparse(url).path or "").lower()
    if any(host == h or host.endswith("." + h) for h in _ANTHROPIC_HOSTS):
        return "anthropic"
    if any(host == h or host.endswith("." + h) for h in _GOOGLE_HOSTS):
        return "google"
    # A proxy on a neutral domain still betrays itself through the path.
    if "/messages" in path:
        return "anthropic"
    if "generatecontent" in path or "/v1beta/models" in path:
        return "google"
    return "openai"


def _get_endpoint_config(
    endpoint_override: str | None = None,
    format_override: str | None = None,
) -> tuple[str, str | None, str, str, str]:
    """
    Resolve the custom endpoint into
    ``(base_url, project_base_url, api_version, api_format, flavor)``.

    Resolution order: *endpoint_override* → ``LLM_ENDPOINT`` →
    ``AZURE_AI_ENDPOINT`` → ``AZURE_OPENAI_ENDPOINT`` (the last two kept for
    backward compatibility with existing .env files).

    ``api_format`` is one of ``CUSTOM_FORMATS``; ``flavor`` refines the openai
    format into ``"foundry"`` (Azure AI Foundry project), ``"azure"`` (classic
    Azure OpenAI, which needs the AzureOpenAI client and an api-version) or
    ``"generic"`` (plain OpenAI-compatible server).

    The full "Target URI" copied from a provider console is accepted: query
    strings and operation paths such as ``/chat/completions`` are stripped.
    Raises ValueError when no endpoint is available.
    """
    raw = (
        (endpoint_override or "").strip()
        or os.getenv("LLM_ENDPOINT", "").strip()
        or os.getenv("AZURE_AI_ENDPOINT", "").strip()
        or os.getenv("AZURE_OPENAI_ENDPOINT", "").strip()   # backward compat
    )
    if not raw:
        raise ValueError(
            "Endpoint no configurado. Ingresa la URL del endpoint donde están "
            "desplegados tus modelos en el campo Endpoint."
        )
    if "://" not in raw:
        # A bare host: local servers are plain http, anything else https.
        local = raw.split("/")[0].split(":")[0].lower()
        scheme = "http" if local in ("localhost", "127.0.0.1", "0.0.0.0", "::1") else "https"
        raw = f"{scheme}://{raw}"

    api_version = (
        os.getenv("AZURE_AI_API_VERSION", "").strip()
        or os.getenv("AZURE_OPENAI_API_VERSION", "").strip()  # backward compat
        or _AZURE_DEFAULT_API_VERSION
    )

    # A pasted Target URI often carries ?api-version=… — honour it, then drop it.
    if "?" in raw:
        raw, _, query = raw.partition("?")
        for part in query.split("&"):
            key, _, value = part.partition("=")
            if key.lower() == "api-version" and value:
                api_version = value

    fmt = (format_override or "").strip().lower()
    if fmt not in CUSTOM_FORMATS:
        fmt = _detect_endpoint_format(raw)

    # Strip the operation path so only the base URL remains.
    lowered = raw.lower()
    for suffix in _ENDPOINT_CALL_SUFFIXES:
        idx = lowered.find(suffix)
        if idx != -1:
            raw = raw[:idx]
            break
    raw = raw.rstrip("/")

    if fmt != "openai":
        # The anthropic and google SDKs append their own versioned paths,
        # so they need the server root rather than a versioned base.
        for versioned in ("/v1beta", "/v1"):
            if raw.lower().endswith(versioned):
                raw = raw[: -len(versioned)]
        return raw.rstrip("/"), None, api_version, fmt, "generic"

    # ── OpenAI format ────────────────────────────────────────────────
    # Case 1: URL already contains /openai/v1/ — Azure AI Foundry.
    if "/openai/v1" in raw:
        cut          = raw.index("/openai/v1")
        openai_base  = raw[: cut + len("/openai/v1")] + "/"
        project_base = raw[:cut] + "/"
        return openai_base, project_base, api_version, fmt, "foundry"

    # Case 2: Azure AI Foundry domain without /openai/v1/ (project endpoint
    # pasted directly). Its OpenAI-compatible API lives at {endpoint}/openai/v1/.
    if ".services.ai.azure.com" in raw.lower():
        return raw + "/openai/v1/", raw + "/", api_version, fmt, "foundry"

    # Case 3: Classic Azure OpenAI endpoint (.openai.azure.com)
    if ".openai.azure.com" in raw.lower():
        return raw + "/", None, api_version, fmt, "azure"

    # Case 4: Any other OpenAI-compatible server. Bare hosts get the
    # conventional /v1 prefix; an explicit path is trusted as given.
    path = (urlparse(raw).path or "").strip("/")
    if not path:
        raw += "/v1"
    return raw + "/", None, api_version, fmt, "generic"


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


# ── Custom endpoint clients ───────────────────────────────

def _custom_client(api_key: str, endpoint_override: str | None = None,
                   format_override: str | None = None):
    """
    Build the SDK client that matches the API format of the endpoint.

    openai    -> openai.OpenAI(base_url=...), or openai.AzureOpenAI for classic
                 Azure OpenAI endpoints, which require an api-version.
    anthropic -> anthropic.Anthropic(base_url=...)
    google    -> genai.Client(http_options=HttpOptions(base_url=...))

    Returns ``(client, api_format)``.
    """
    base, _project, api_version, fmt, flavor = _get_endpoint_config(
        endpoint_override, format_override
    )

    if fmt == "anthropic":
        try:
            import anthropic as _anthropic
        except ImportError:
            raise RuntimeError(
                "El paquete 'anthropic' no está instalado. "
                "Ejecuta: pip install anthropic"
            )
        return _anthropic.Anthropic(api_key=api_key, base_url=base), fmt

    if fmt == "google":
        from google import genai
        from google.genai import types as genai_types
        return genai.Client(
            api_key=api_key,
            http_options=genai_types.HttpOptions(base_url=base),
        ), fmt

    try:
        import openai as _openai
    except ImportError:
        raise RuntimeError(
            "El paquete 'openai' no está instalado. "
            "Ejecuta: pip install openai"
        )
    if flavor == "azure":
        return _openai.AzureOpenAI(
            azure_endpoint=base, api_key=api_key, api_version=api_version
        ), fmt
    return _openai.OpenAI(base_url=base, api_key=api_key), fmt


def _raise_if_endpoint_unusable(exc: Exception) -> None:
    """
    Re-raise *exc* as ValueError on an auth failure or RuntimeError on a
    connectivity failure. Returns silently for anything else, letting the
    caller treat the response as "reached the server, nothing usable back".
    """
    status = getattr(exc, "status_code", None) or getattr(exc, "code", None)
    name   = type(exc).__name__

    if status in (401, 403) or name in ("AuthenticationError", "PermissionDeniedError"):
        raise ValueError(f"API key rechazada por el endpoint: {exc}") from exc
    if name in ("APIConnectionError", "APITimeoutError") or isinstance(
        exc, (ConnectionError, TimeoutError)
    ):
        raise RuntimeError(
            f"No se pudo conectar con el endpoint. Verifica la URL. Detalle: {exc}"
        ) from exc


def _list_custom(api_key: str, endpoint_override: str | None = None,
                 format_override: str | None = None) -> list[dict]:
    """
    List the models the endpoint exposes, using the listing call of its format.

    Every supported format defines one, so most servers answer. Servers that do
    not (notably Azure AI Foundry project endpoints, whose deployment listing
    needs Entra ID rather than an API key) yield an empty list and the UI falls
    back to the manual model input.

    Raises ValueError when the key is rejected (401/403) and RuntimeError when
    the endpoint is unreachable — an unusable configuration either way.
    """
    _base, _project, _api_version, fmt, flavor = _get_endpoint_config(
        endpoint_override, format_override
    )
    client, _ = _custom_client(api_key, endpoint_override, format_override)
    result: list[dict] = []

    try:
        if fmt == "google":
            for m in client.models.list():
                mid = (getattr(m, "name", "") or "").removeprefix("models/")
                if mid:
                    result.append({
                        "id": mid,
                        "display_name": getattr(m, "display_name", None) or mid,
                    })
        else:
            # Both the OpenAI and Anthropic listings key on .id
            for m in client.models.list():
                mid = getattr(m, "id", None) or ""
                if mid:
                    result.append({
                        "id": mid,
                        "display_name": getattr(m, "display_name", None) or mid,
                    })
    except Exception as exc:
        _raise_if_endpoint_unusable(exc)
        # Any other response (404, unsupported operation, odd payload) simply
        # means this server does not advertise its models — not an error.
        result = []

    if not result and flavor == "foundry":
        return list(_FOUNDRY_RECOMMENDED_MODELS)
    return result


def _validate_custom(api_key: str, endpoint_override: str | None = None,
                     format_override: str | None = None) -> None:
    """
    Check that the endpoint accepts the API key, without requiring it to
    support model listing.

    401/403 -> invalid key (ValueError). Connection failure -> RuntimeError.
    Anything else (including 404) means the request reached the server and was
    not rejected on credentials, so the key is treated as usable.
    """
    client, _fmt = _custom_client(api_key, endpoint_override, format_override)
    try:
        client.models.list()
    except Exception as exc:
        _raise_if_endpoint_unusable(exc)


# Retry schedule for 429 (rate limit) responses from a custom endpoint.
# Self-hosted and pay-as-you-go deployments often ship low default TPM/RPM
# quotas, so a short wait-and-retry resolves most transient rate-limit hits.
_CUSTOM_RATE_LIMIT_BACKOFF = [10, 20, 40]  # seconds


def _custom_generate(client, fmt: str, model: str, prompt: str) -> str:
    """Single generation call, dispatched by API format."""
    if fmt == "anthropic":
        message = client.messages.create(
            model=model,
            max_tokens=8096,
            messages=[{"role": "user", "content": prompt}],
        )
        return message.content[0].text if message.content else ""

    if fmt == "google":
        response = client.models.generate_content(model=model, contents=prompt)
        return response.text or ""

    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.choices[0].message.content if response.choices else ""


def _call_custom(prompt: str, api_key: str, model: str,
                 endpoint_override: str | None = None,
                 format_override: str | None = None) -> str:
    """Send *prompt* to the custom endpoint using the API format it speaks."""
    import time as _time
    import sys

    client, fmt = _custom_client(api_key, endpoint_override, format_override)

    _chars = len(prompt)
    print(
        f"[_call_custom] format={fmt!r}  model={model!r}  prompt_chars={_chars}  "
        f"est_tokens~{_chars // 4}",
        file=sys.stderr, flush=True,
    )

    for attempt, wait in enumerate([0] + _CUSTOM_RATE_LIMIT_BACKOFF):
        if wait:
            _time.sleep(wait)
        try:
            text = _custom_generate(client, fmt, model, prompt)
            if not text or not text.strip():
                raise RuntimeError("El endpoint devolvió una respuesta vacía.")
            return text
        except (ValueError, RuntimeError):
            raise
        except Exception as exc:
            status = getattr(exc, "status_code", None) or getattr(exc, "code", None)
            if status == 429:
                if attempt >= len(_CUSTOM_RATE_LIMIT_BACKOFF):
                    raise RuntimeError(
                        f"Cuota del endpoint superada (429) tras "
                        f"{len(_CUSTOM_RATE_LIMIT_BACKOFF)} reintentos: {exc}"
                    ) from exc
                continue   # try again after the next backoff wait
            if status in (401, 403):
                raise RuntimeError(f"API key rechazada por el endpoint: {exc}") from exc
            if status == 404:
                raise RuntimeError(
                    f"El modelo '{model}' no existe en este endpoint. "
                    "Verifica el nombre del modelo o del deployment."
                ) from exc
            if type(exc).__name__ in ("APIConnectionError", "APITimeoutError") or isinstance(
                exc, (ConnectionError, TimeoutError, OSError)
            ):
                raise RuntimeError(
                    f"No se pudo conectar con el endpoint. Detalle: {exc}"
                ) from exc
            if status:
                raise RuntimeError(f"Error del endpoint ({status}): {exc}") from exc
            raise RuntimeError(f"Error inesperado del endpoint: {exc}") from exc


# ── Public API ────────────────────────────────────────────

# "azure" is the former name of the "custom" provider; accepted so older
# clients and saved .env files keep working.
_CUSTOM_PROVIDERS = ("custom", "azure")


def test_model(api_key: str, provider: str, model: str,
               custom_endpoint: str | None = None,
               custom_format: str | None = None) -> None:
    """
    Make a minimal 1-token call to verify the model is deployed and reachable.

    Raises ValueError on auth/model errors, RuntimeError on network errors.
    A successful return (no exception) means the model is available.
    """
    prov = (provider or "").lower()

    if prov in _CUSTOM_PROVIDERS:
        try:
            client, fmt = _custom_client(api_key, custom_endpoint, custom_format)
            _custom_generate(client, fmt, model, "Hi")
        except ValueError:
            raise
        except Exception as exc:
            # Auth and connectivity failures get the shared wording.
            _raise_if_endpoint_unusable(exc)
            status = getattr(exc, "status_code", None) or getattr(exc, "code", None)
            if status == 404:
                raise ValueError(
                    f"El modelo '{model}' no existe en este endpoint. "
                    "Verifica el nombre del modelo o del deployment."
                ) from exc
            if status:
                raise ValueError(f"Error {status}: {exc}") from exc
            raise RuntimeError(str(exc)) from exc

    elif prov == "google":
        from google import genai
        from google.genai import errors as genai_errors
        try:
            client = genai.Client(api_key=api_key)
            client.models.generate_content(model=model, contents="Hi")
        except genai_errors.ClientError as exc:
            raise ValueError(_google_friendly_error(exc)) from exc
        except Exception as exc:
            raise RuntimeError(str(exc)) from exc

    elif prov == "anthropic":
        try:
            import anthropic as _anthropic
        except ImportError:
            raise RuntimeError("El paquete 'anthropic' no está instalado.")
        try:
            _anthropic.Anthropic(api_key=api_key).messages.create(
                model=model, max_tokens=1,
                messages=[{"role": "user", "content": "Hi"}],
            )
        except _anthropic.AuthenticationError as exc:
            raise ValueError(str(exc)) from exc
        except _anthropic.APIStatusError as exc:
            raise ValueError(f"Error {exc.status_code}: {exc}") from exc
        except Exception as exc:
            raise RuntimeError(str(exc)) from exc

    elif prov == "openai":
        try:
            import openai as _openai
        except ImportError:
            raise RuntimeError("El paquete 'openai' no está instalado.")
        try:
            _openai.OpenAI(api_key=api_key).chat.completions.create(
                model=model, max_tokens=1,
                messages=[{"role": "user", "content": "Hi"}],
            )
        except _openai.AuthenticationError as exc:
            raise ValueError(str(exc)) from exc
        except _openai.NotFoundError as exc:
            raise ValueError(
                f"Modelo '{model}' no encontrado. Verifica el nombre del modelo."
            ) from exc
        except _openai.APIStatusError as exc:
            raise ValueError(f"Error {exc.status_code}: {exc}") from exc
        except Exception as exc:
            raise RuntimeError(str(exc)) from exc

    else:
        raise ValueError(f"Proveedor desconocido: {provider}")


def validate_key(api_key: str, provider: str | None = None,
                 custom_endpoint: str | None = None,
                 custom_format: str | None = None) -> list[dict]:
    """
    Validate *api_key* for the given provider and return available models.

    For a custom endpoint the key is validated first, then the endpoint is
    asked for its models; an endpoint with no listing API yields [] and the UI
    falls back to the manual model input.

    Raises ValueError on auth error, RuntimeError on network/unexpected error.
    """
    prov = (provider or detect_provider(api_key)).lower()
    if prov in _CUSTOM_PROVIDERS:
        _validate_custom(api_key, custom_endpoint, custom_format)
        return _list_custom(api_key, custom_endpoint, custom_format)
    return list_models(api_key, prov)


def list_models(api_key: str, provider: str | None = None,
                custom_endpoint: str | None = None,
                custom_format: str | None = None) -> list[dict]:
    """
    Return models available to *api_key* that support text generation.

    Parameters
    ----------
    api_key  : str
        Provider API key.
    provider : "google" | "anthropic" | "openai" | "custom" | None
        When None, auto-detected from the key format.
    custom_endpoint : str | None
        Base URL, required when *provider* is "custom".
    custom_format : "openai" | "anthropic" | "google" | None
        API format of the custom endpoint; auto-detected when None.

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
    if prov in _CUSTOM_PROVIDERS:
        return _list_custom(api_key, custom_endpoint, custom_format)
    return _list_google(api_key)


def call_llm(
    prompt: str,
    *,
    api_key_override: str | None = None,
    model_override:   str | None = None,
    provider_override: str | None = None,
    custom_endpoint_override: str | None = None,
    custom_format_override: str | None = None,
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
      2. ``LLM_MODEL`` env variable
      3. Provider default (no default exists for a custom endpoint, whose
         model names only the server knows)

    Raises
    ------
    ValueError   — Missing / invalid API key, or missing model.
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

    if provider in _CUSTOM_PROVIDERS:
        if not model:
            model = os.getenv("LLM_MODEL", "").strip()
        if not model:
            raise ValueError(
                "Indica el nombre del modelo del endpoint. Selecciónalo de la "
                "lista o escríbelo manualmente: el endpoint decide cómo se llama."
            )
        return _call_custom(
            prompt, api_key, model,
            custom_endpoint_override, custom_format_override,
        )

    # Google (default)
    if not model:
        model = os.getenv("LLM_MODEL", "gemini-3-flash-preview").strip() or "gemini-3-flash-preview"
    return _call_google(prompt, api_key, model)
