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
- Bloques de código con triple backtick y el lenguaje especificado

Antes de **cada tabla**, **bloque de código** y **diagrama** incluye, en la línea
inmediatamente anterior (sin líneas en blanco entre el tag y el elemento), la etiqueta:

  [CAPTION: breve descripción del contenido]

La descripción debe ser concisa (máximo 10 palabras) y explicar qué representa el
elemento. Ejemplos válidos:
  [CAPTION: Dependencias principales del proyecto]
  [CAPTION: Comando de instalación en entorno virtual]
  [CAPTION: Arquitectura de componentes del sistema]"""


class BaseGenerator:
    DOC_TYPE:     str       = ""
    DISPLAY_NAME: str       = ""
    FILE_SUFFIX:  str       = ""
    SECTIONS:     list[str] = []

    # Each subclass defines its own writing persona: who is the audience,
    # what tone to use, and what to emphasise or avoid.
    PERSONA: str = ""

    # Optional block injected just before the repo context.
    # Use this for type-specific technical instructions (e.g. diagram syntax).
    EXTRA_INSTRUCTIONS: str = ""

    # ── Prompt building ───────────────────────────────────────────────

    def build_prompt(
        self,
        repo_scan: RepoScan,
        template_content: str | None = None,
        locked_sections: list[str] | None = None,
    ) -> str:
        """
        Assemble the full prompt for this document type.

        Parameters
        ----------
        repo_scan        : RepoScan
            Scanned repository data.
        template_content : str | None
            Raw text of a user-supplied template document.
        locked_sections  : list[str] | None
            Section titles that must be reproduced verbatim from the template
            without any modification. Only meaningful when *template_content*
            is provided. Sections not in this list will be generated/adapted
            by the LLM.

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

        persona_block = (
            f"## Tu rol y audiencia\n\n{self.PERSONA}\n\n"
            if self.PERSONA else ""
        )

        repo_context = ai_service.build_repo_context(repo_scan)

        extra_block = (
            f"## Instrucciones específicas\n\n{self.EXTRA_INSTRUCTIONS}\n\n"
            if self.EXTRA_INSTRUCTIONS else ""
        )

        # Build the locked-sections block only when applicable
        locked_block = ""
        if template_content and locked_sections:
            locked_list = "\n".join(f"  - {s}" for s in locked_sections)
            locked_block = (
                "## Secciones que NO debes modificar\n\n"
                "Las siguientes secciones deben copiarse **exactamente** como "
                "aparecen en la plantilla, sin ninguna modificación, adición ni "
                "eliminación de contenido:\n\n"
                f"{locked_list}\n\n"
                "El resto de secciones sí deben generarse o adaptarse según el "
                "código del repositorio.\n\n"
            )

        return (
            "Eres un experto en documentación de software. "
            "Tu tarea es generar documentación profesional en Markdown "
            "para el repositorio de código que se proporciona más abajo.\n\n"
            f"{persona_block}"
            f"{_FORMAT_INSTRUCTIONS}\n\n"
            "## Estructura del documento\n\n"
            f"{structure_instruction}\n\n"
            f"{locked_block}"
            "## Instrucciones generales\n\n"
            "- Redacta íntegramente en español.\n"
            "- Basa cada afirmación en el código real del repositorio; "
            "no inventes funcionalidades que no existan.\n"
            "- No incluyas texto introductorio, aclaraciones ni comentarios "
            "fuera del documento en sí.\n"
            "- Responde **únicamente** con el documento Markdown completo.\n\n"
            f"{extra_block}"
            f"---\n\n{repo_context}"
        )

    # ── Generation ────────────────────────────────────────────────────

    def generate(
        self,
        repo_scan: RepoScan,
        template_content: str | None = None,
        locked_sections: list[str] | None = None,
    ) -> str:
        """
        Build the prompt for this document type, send it to Gemini, and
        return the response as a Markdown string.

        Parameters
        ----------
        locked_sections : list[str] | None
            Section titles the LLM must reproduce verbatim from the template.

        Raises
        ------
        ValueError   — configuration problems (see ai_service.call_gemini).
        RuntimeError — API / network / response errors.
        """
        try:
            prompt = self.build_prompt(repo_scan, template_content, locked_sections)
        except Exception as exc:
            raise RuntimeError(
                f"No se pudo construir el prompt para '{self.DISPLAY_NAME}': {exc}"
            ) from exc

        return ai_service.call_gemini(prompt)

    def build_section_prompt(
        self,
        repo_scan: RepoScan,
        section_name: str,
    ) -> str:
        """
        Build a focused prompt to generate a single section of the document.

        The LLM is asked to produce only the content of *section_name*,
        starting with its ``##`` heading.  The other section names are listed
        as context so the LLM can calibrate scope and avoid duplication.
        """
        sections_context = "\n".join(f"  - {s}" for s in self.SECTIONS)
        persona_block = (
            f"## Tu rol y audiencia\n\n{self.PERSONA}\n\n"
            if self.PERSONA else ""
        )
        extra_block = (
            f"## Instrucciones específicas\n\n{self.EXTRA_INSTRUCTIONS}\n\n"
            if self.EXTRA_INSTRUCTIONS else ""
        )
        repo_context = ai_service.build_repo_context(repo_scan)

        return (
            "Eres un experto en documentación de software. "
            f"Tu tarea es escribir UNA sección de un documento "
            f"'{self.DISPLAY_NAME}' para el repositorio que se describe más abajo.\n\n"
            f"{persona_block}"
            f"{_FORMAT_INSTRUCTIONS}\n\n"
            "## Contexto del documento\n\n"
            f"El documento completo contiene estas secciones:\n{sections_context}\n\n"
            "## Sección a generar\n\n"
            f"Escribe ÚNICAMENTE el contenido de la sección: **{section_name}**\n\n"
            f"- Empieza con `## {section_name}` como primera línea.\n"
            "- No incluyas otras secciones ni el título principal del documento.\n"
            "- Redacta íntegramente en español.\n"
            "- Basa cada afirmación en el código real del repositorio.\n"
            "- No incluyas texto introductorio ni comentarios fuera de la sección.\n"
            "- Responde **únicamente** con el contenido Markdown de esta sección.\n\n"
            f"{extra_block}"
            f"---\n\n{repo_context}"
        )

    def generate_section(self, repo_scan: RepoScan, section_name: str) -> str:
        """
        Generate the Markdown content for a single *section_name*.

        Raises
        ------
        ValueError   — configuration problems.
        RuntimeError — API / network / response errors.
        """
        try:
            prompt = self.build_section_prompt(repo_scan, section_name)
        except Exception as exc:
            raise RuntimeError(
                f"No se pudo construir el prompt para la sección '{section_name}': {exc}"
            ) from exc

        return ai_service.call_gemini(prompt)

    # ── Output path helpers ───────────────────────────────────────────

    def output_filename(self, repo_name: str) -> str:
        suffix = self.FILE_SUFFIX or self.DOC_TYPE
        return f"{repo_name}_{suffix}.docx"

    def output_path(self, repo_name: str, output_dir: str) -> Path:
        return Path(output_dir) / self.output_filename(repo_name)
