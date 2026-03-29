"""
ai_service.py — LLM integration via Google Gemini.

Public API
----------
generate_documentation(repo_scan, doc_type, template_content=None) -> str
    Build a prompt from the scanned repository, call Gemini, and return
    the response as a Markdown string.

All exceptions are normalized to ValueError or RuntimeError so callers
only need to catch those two types.
"""

from __future__ import annotations

import os

from .repo_reader import RepoScan

# ── Section definitions per document type ────────────────────────────

_SECTIONS: dict[str, list[str]] = {
    "technical": [
        "Resumen del proyecto",
        "Arquitectura general del sistema",
        "Estructura de carpetas y archivos",
        "Descripción de módulos y componentes",
        "Flujo de datos / lógica principal",
        "Dependencias y requisitos",
        "Instrucciones de instalación y configuración",
        "Variables de entorno",
        "API / endpoints (si aplica)",
        "Diagramas de flujo o arquitectura (descripción textual)",
        "Notas técnicas y decisiones de diseño",
    ],
    "user_manual": [
        "Introducción y propósito de la herramienta",
        "Requisitos previos",
        "Instalación / acceso",
        "Primeros pasos",
        "Guía de uso paso a paso",
        "Descripción de funcionalidades",
        "Casos de uso frecuentes",
        "Preguntas frecuentes (FAQ)",
        "Solución de problemas comunes",
        "Glosario",
    ],
    "executive": [
        "Resumen ejecutivo",
        "Problema que resuelve",
        "Solución propuesta",
        "Funcionalidades principales",
        "Beneficios y valor agregado",
        "Arquitectura (vista de alto nivel)",
        "Stack tecnológico",
        "Estado actual y roadmap",
        "Conclusiones",
    ],
}

# Maximum characters of repo content sent in the prompt.
_MAX_CONTEXT_CHARS = 350_000


# ── Internal helpers ─────────────────────────────────────────────────

def _build_repo_context(repo_scan: RepoScan) -> str:
    """Serialise the scanned repository as a readable Markdown block."""
    parts: list[str] = []

    parts.append("## Estructura del repositorio\n\n")
    for f in repo_scan.files:
        parts.append(f"- `{f.relative_path}`\n")
    parts.append("\n---\n\n## Contenido de los archivos\n\n")

    used_chars = sum(len(p) for p in parts)

    for f in repo_scan.files:
        lang = f.extension.lstrip(".") or "text"
        block = f"### `{f.relative_path}`\n\n```{lang}\n{f.content}\n```\n\n"
        if used_chars + len(block) > _MAX_CONTEXT_CHARS:
            parts.append(
                f"### `{f.relative_path}`\n\n"
                "*[contenido omitido por límite de contexto]*\n\n"
            )
            continue
        parts.append(block)
        used_chars += len(block)

    return "".join(parts)


def _build_prompt(
    repo_scan: RepoScan,
    doc_type: str,
    template_content: str | None,
) -> str:
    sections = _SECTIONS.get(doc_type, _SECTIONS["technical"])
    sections_block = "\n".join(f"  {i + 1}. {s}" for i, s in enumerate(sections))

    if template_content:
        structure_instruction = (
            "El usuario ha proporcionado el siguiente documento como plantilla de referencia. "
            "Respeta su estructura, estilo y nivel de detalle al redactar el documento:\n\n"
            "---INICIO PLANTILLA---\n"
            f"{template_content[:6000]}\n"
            "---FIN PLANTILLA---\n"
        )
    else:
        structure_instruction = (
            "El documento debe incluir las siguientes secciones, en el orden dado:\n"
            f"{sections_block}"
        )

    repo_context = _build_repo_context(repo_scan)

    return f"""Eres un experto en documentación de software. \
Tu tarea es generar documentación profesional, clara y detallada en Markdown \
para el repositorio de código que se proporciona más abajo.

## Instrucciones de formato

Usa **exactamente** estas convenciones Markdown:
- `#` para el título principal del documento
- `##` para cada sección principal
- `###` para subsecciones cuando sea necesario
- Listas con `-` o `*` cuando corresponda
- Tablas en sintaxis Markdown nativa con `|` cuando corresponda
- Bloques de código con triple backtick y el lenguaje especificado

## Estructura del documento

{structure_instruction}

## Instrucciones adicionales

- Redacta en español.
- Sé preciso y basa cada afirmación en el código real del repositorio.
- No incluyas texto introductorio, aclaraciones ni explicaciones fuera del documento.
- Responde **únicamente** con el documento Markdown completo.

---

{repo_context}"""


def _friendly_api_error(exc: genai_errors.APIError) -> str:
    """Map Gemini API HTTP codes to user-friendly Spanish messages."""
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
            "Espera unos minutos y vuelve a intentarlo, o revisa tu plan en Google AI Studio."
        ),
        500: (
            "Error interno del servidor de Google (500). "
            "El servicio puede estar temporalmente no disponible. Intenta de nuevo en unos minutos."
        ),
        503: (
            "El servicio de Gemini no está disponible en este momento (503). "
            "Intenta de nuevo más tarde."
        ),
    }

    if code in messages:
        return messages[code]

    return f"Error de la API de Gemini ({code}): {exc}"


# ── Public API ───────────────────────────────────────────────────────

def generate_documentation(
    repo_scan: RepoScan,
    doc_type: str,
    template_content: str | None = None,
) -> str:
    """
    Call Gemini with a prompt built from *repo_scan* and return the
    response as a Markdown string.

    Raises
    ------
    ValueError   — configuration problems (missing/invalid API key, bad model name).
    RuntimeError — API errors, network failures, empty or blocked responses.
    """
    # ── Validate config ──────────────────────────────────────────────
    api_key = os.getenv("LLM_API_KEY", "").strip()
    if not api_key or api_key == "tu_api_key_aqui":
        raise ValueError(
            "LLM_API_KEY no está configurada. "
            "Abre el archivo .env y reemplaza 'tu_api_key_aqui' con tu clave de Google AI Studio."
        )

    model_name = os.getenv("LLM_MODEL", "gemini-2.5-flash").strip()
    if not model_name:
        raise ValueError(
            "LLM_MODEL está vacío en el archivo .env. "
            "Usa un valor como 'gemini-2.5-flash'."
        )

    # ── Build prompt ─────────────────────────────────────────────────
    try:
        prompt = _build_prompt(repo_scan, doc_type, template_content)
    except Exception as exc:
        raise RuntimeError(
            f"No se pudo construir el prompt para el modelo: {exc}"
        ) from exc

    # ── Call Gemini ──────────────────────────────────────────────────
    # Imported here (not at module level) to avoid slow SDK initialization
    # on every app startup — the SDK is only needed when the user actually
    # clicks "Generar".
    from google import genai                      # noqa: PLC0415
    from google.genai import errors as genai_errors  # noqa: PLC0415

    try:
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(model=model_name, contents=prompt)
    except genai_errors.ClientError as exc:
        raise RuntimeError(_friendly_api_error(exc)) from exc
    except genai_errors.ServerError as exc:
        raise RuntimeError(_friendly_api_error(exc)) from exc
    except (ConnectionError, TimeoutError, OSError) as exc:
        raise RuntimeError(
            f"No se pudo conectar con la API de Gemini. "
            f"Verifica tu conexión a internet. Detalle: {exc}"
        ) from exc
    except Exception as exc:
        raise RuntimeError(
            f"Error inesperado al llamar al modelo: {exc}"
        ) from exc

    # ── Validate response ────────────────────────────────────────────
    # response.text raises ValueError when content is blocked by safety filters
    try:
        text = response.text
    except ValueError:
        # Inspect finish reason for a clearer message
        finish_reason = "desconocido"
        try:
            finish_reason = str(response.candidates[0].finish_reason)
        except Exception:
            pass
        raise RuntimeError(
            f"El modelo rechazó generar el contenido (motivo: {finish_reason}). "
            "Esto ocurre cuando el contenido del repositorio activa los filtros de seguridad. "
            "Intenta con un repositorio diferente."
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
