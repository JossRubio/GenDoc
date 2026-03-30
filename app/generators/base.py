"""
base.py — Base class for all document generators.

Each subclass must declare:
    DOC_TYPE     : str        — API key (e.g. "technical")
    DISPLAY_NAME : str        — Human-readable label
    FILE_SUFFIX  : str        — Output filename suffix
    SECTIONS     : list[str]  — Ordered section names for the default prompt

Subclasses may override ``build_prompt()`` for custom prompt logic, or
leave it as-is to use the shared structure defined here.

``generate()`` is a concrete final step: it calls ``build_prompt()``
followed by ``ai_service.call_gemini()`` and returns a Markdown string.

To add a new document type:
  1. Create a new module in this package (e.g. my_type.py).
  2. Subclass BaseGenerator, set the four class attributes, and optionally
     override build_prompt().
  3. Register the class in generators/__init__.py → GENERATORS.
"""

from __future__ import annotations

from pathlib import Path

from .. import ai_service
from ..repo_reader import RepoScan

# Shared Markdown formatting block, included in every prompt.
_FORMAT_INSTRUCTIONS = """\
## Instrucciones de formato

Usa **exactamente** estas convenciones Markdown:
- `#` para el título principal del documento
- `##` para cada sección principal
- `###` para subsecciones cuando sea necesario
- Listas con `-` o `*` cuando corresponda
- Tablas en sintaxis Markdown nativa con `|` cuando corresponda
- Bloques de código con triple backtick y el lenguaje especificado"""


class BaseGenerator:
    DOC_TYPE:     str       = ""
    DISPLAY_NAME: str       = ""
    FILE_SUFFIX:  str       = ""
    SECTIONS:     list[str] = []

    # ── Prompt building ───────────────────────────────────────────────

    def build_prompt(
        self,
        repo_scan: RepoScan,
        template_content: str | None = None,
    ) -> str:
        """
        Assemble the full prompt for this document type.

        Override this method in a subclass only when the default
        structure is not appropriate for that document type.
        """
        if template_content:
            structure_instruction = (
                "El usuario ha proporcionado el siguiente documento como plantilla "
                "de referencia. Respeta su estructura, estilo y nivel de detalle "
                "al redactar el documento:\n\n"
                "---INICIO PLANTILLA---\n"
                f"{template_content[:6000]}\n"
                "---FIN PLANTILLA---\n"
            )
        else:
            sections_block = "\n".join(
                f"  {i + 1}. {s}" for i, s in enumerate(self.SECTIONS)
            )
            structure_instruction = (
                "El documento debe incluir las siguientes secciones, "
                f"en el orden dado:\n{sections_block}"
            )

        repo_context = ai_service.build_repo_context(repo_scan)

        return (
            "Eres un experto en documentación de software. "
            "Tu tarea es generar documentación profesional, clara y detallada "
            "en Markdown para el repositorio de código que se proporciona más abajo.\n\n"
            f"{_FORMAT_INSTRUCTIONS}\n\n"
            "## Estructura del documento\n\n"
            f"{structure_instruction}\n\n"
            "## Instrucciones adicionales\n\n"
            "- Redacta en español.\n"
            "- Sé preciso y basa cada afirmación en el código real del repositorio.\n"
            "- No incluyas texto introductorio, aclaraciones ni explicaciones "
            "fuera del documento.\n"
            "- Responde **únicamente** con el documento Markdown completo.\n\n"
            f"---\n\n{repo_context}"
        )

    # ── Generation ────────────────────────────────────────────────────

    def generate(
        self,
        repo_scan: RepoScan,
        template_content: str | None = None,
    ) -> str:
        """
        Build the prompt for this document type, send it to Gemini, and
        return the response as a Markdown string.

        Raises
        ------
        ValueError   — configuration problems (see ai_service.call_gemini).
        RuntimeError — API / network / response errors.
        """
        try:
            prompt = self.build_prompt(repo_scan, template_content)
        except Exception as exc:
            raise RuntimeError(
                f"No se pudo construir el prompt para '{self.DISPLAY_NAME}': {exc}"
            ) from exc

        return ai_service.call_gemini(prompt)

    # ── Output path helpers ───────────────────────────────────────────

    def output_filename(self, repo_name: str) -> str:
        suffix = self.FILE_SUFFIX or self.DOC_TYPE
        return f"{repo_name}_{suffix}.docx"

    def output_path(self, repo_name: str, output_dir: str) -> Path:
        return Path(output_dir) / self.output_filename(repo_name)
