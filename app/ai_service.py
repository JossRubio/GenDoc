"""
ai_service.py — LLM integration via Google Gemini.

Public API
----------
generate_documentation(repo_scan, doc_type, template_content=None) -> str
    Build a prompt from the scanned repository, call Gemini, and return
    the response as a Markdown string.
"""

from __future__ import annotations

import os

from google import genai

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

# Maximum characters of repo content included in the prompt.
# Keeps requests within Gemini's context window and avoids huge costs.
_MAX_CONTEXT_CHARS = 350_000


# ── Internal helpers ─────────────────────────────────────────────────

def _build_repo_context(repo_scan: RepoScan) -> str:
    """Serialise the scanned repository as a readable Markdown block."""
    parts: list[str] = []

    # 1. File tree
    parts.append("## Estructura del repositorio\n\n")
    for f in repo_scan.files:
        parts.append(f"- `{f.relative_path}`\n")
    parts.append("\n---\n\n## Contenido de los archivos\n\n")

    used_chars = sum(len(p) for p in parts)

    # 2. File contents — skip a file when the budget would be exceeded
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


def _read_template(template_path: str) -> str | None:
    """
    Read the user-supplied template file and return its text content.
    Returns None if the file cannot be decoded as text (e.g. binary .docx).
    """
    try:
        return open(template_path, encoding="utf-8", errors="strict").read()
    except (UnicodeDecodeError, OSError):
        return None


# ── Public API ───────────────────────────────────────────────────────

def generate_documentation(
    repo_scan: RepoScan,
    doc_type: str,
    template_content: str | None = None,
) -> str:
    """
    Call Gemini with a prompt built from *repo_scan* and return the
    response as a Markdown string.

    Parameters
    ----------
    repo_scan:
        Result of ``repo_reader.scan()``.
    doc_type:
        One of ``"technical"``, ``"user_manual"``, ``"executive"``.
    template_content:
        Plain-text content of the user's reference document, or ``None``.

    Raises
    ------
    ValueError  — if ``LLM_API_KEY`` is not set.
    RuntimeError — if the model returns an empty or blocked response.
    """
    api_key = os.getenv("LLM_API_KEY", "")
    if not api_key or api_key == "tu_api_key_aqui":
        raise ValueError(
            "LLM_API_KEY no está configurada. "
            "Agrega tu clave de API en el archivo .env"
        )

    model_name = os.getenv("LLM_MODEL", "gemini-2.5-flash")
    prompt = _build_prompt(repo_scan, doc_type, template_content)

    client = genai.Client(api_key=api_key)
    response = client.models.generate_content(model=model_name, contents=prompt)

    text = response.text
    if not text or not text.strip():
        raise RuntimeError(
            "El modelo devolvió una respuesta vacía. "
            "Revisa que la clave API sea válida y que el repositorio no esté vacío."
        )

    return text
