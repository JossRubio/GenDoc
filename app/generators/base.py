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

# Shared Markdown formatting block — one version per supported output language.
_FORMAT_INSTRUCTIONS: dict[str, str] = {
    "es": """\
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
  [CAPTION: Arquitectura de componentes del sistema]""",

    "en": """\
## Formatting instructions

Use **exactly** these Markdown conventions:
- `#` for the main document title
- `##` for each main section
- `###` for subsections when needed
- Lists with `-` or `*` where appropriate
- Native Markdown tables with `|` where appropriate
- Code blocks with triple backtick and the language specified

Before **each table**, **code block** and **diagram**, include on the immediately
preceding line (no blank lines between the tag and the element) the label:

  [CAPTION: brief description of the content]

The description must be concise (max 10 words) and explain what the element represents.
Valid examples:
  [CAPTION: Main project dependencies]
  [CAPTION: Installation command in virtual environment]
  [CAPTION: System component architecture]""",
}


# Language directive inserted at the very top of every prompt.
_LANG_DIRECTIVE: dict[str, str] = {
    "es": (
        "🌐 **IDIOMA DE SALIDA OBLIGATORIO: ESPAÑOL**\n"
        "Redacta TODO el contenido del documento en español. "
        "Todos los títulos, secciones, párrafos, listas, tablas y explicaciones "
        "deben estar escritos en español. No uses otro idioma en ninguna parte del documento.\n\n"
    ),
    "en": (
        "🌐 **MANDATORY OUTPUT LANGUAGE: ENGLISH**\n"
        "Write ALL document content in English. "
        "Every title, section heading, paragraph, list item, table cell and explanation "
        "must be written in English. Do not use any other language anywhere in the document.\n\n"
    ),
}


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
        section_enrichments: dict | None = None,
        output_lang: str = "es",
    ) -> str:
        """
        Assemble the full prompt for this document type.

        Parameters
        ----------
        repo_scan            : RepoScan
            Scanned repository data.
        template_content     : str | None
            Raw text of a user-supplied template document.
        locked_sections      : list[str] | None
            Section titles that must be reproduced verbatim from the template.
        section_enrichments  : dict[str, list[str]] | None
            Maps section title → list of enrichment types requested.
            Supported values: ``"table"``, ``"diagram"``.
            When provided, the LLM is instructed to include those elements
            in the corresponding sections.

        Override this method in a subclass only when the default
        structure is not appropriate for that document type.
        """
        lang = output_lang if output_lang in ("es", "en") else "es"

        # ── Resolve section names in the target language ───────────────
        sections = getattr(self, f"SECTIONS_{lang.upper()}", None) or self.SECTIONS
        persona  = getattr(self, f"PERSONA_{lang.upper()}", None)  or self.PERSONA
        extra    = getattr(self, f"EXTRA_INSTRUCTIONS_{lang.upper()}", None) or self.EXTRA_INSTRUCTIONS

        fmt_instructions = _FORMAT_INSTRUCTIONS[lang]
        lang_directive   = _LANG_DIRECTIVE[lang]

        if template_content:
            if lang == "en":
                structure_instruction = (
                    "The user has provided the following document as a reference template. "
                    "Respect its structure, style and level of detail when writing the document:\n\n"
                    "---TEMPLATE START---\n"
                    f"{template_content[:6000]}\n"
                    "---TEMPLATE END---\n"
                )
            else:
                structure_instruction = (
                    "El usuario ha proporcionado el siguiente documento como plantilla "
                    "de referencia. Respeta su estructura, estilo y nivel de detalle "
                    "al redactar el documento:\n\n"
                    "---INICIO PLANTILLA---\n"
                    f"{template_content[:6000]}\n"
                    "---FIN PLANTILLA---\n"
                )
        else:
            sections_block = "\n".join(f"  {i + 1}. {s}" for i, s in enumerate(sections))
            if lang == "en":
                structure_instruction = (
                    f"The document must include the following sections in the given order:\n{sections_block}"
                )
            else:
                structure_instruction = (
                    f"El documento debe incluir las siguientes secciones, en el orden dado:\n{sections_block}"
                )

        persona_block = (
            (f"## Your role and audience\n\n{persona}\n\n" if lang == "en"
             else f"## Tu rol y audiencia\n\n{persona}\n\n")
            if persona else ""
        )

        repo_context = ai_service.build_repo_context(repo_scan)

        extra_block = (
            (f"## Specific instructions\n\n{extra}\n\n" if lang == "en"
             else f"## Instrucciones específicas\n\n{extra}\n\n")
            if extra else ""
        )

        # Build the locked-sections block only when applicable
        locked_block = ""
        if template_content and locked_sections:
            locked_list = "\n".join(f"  - {s}" for s in locked_sections)
            if lang == "en":
                locked_block = (
                    "## Sections you must NOT modify\n\n"
                    "The following sections must be copied **exactly** as they appear "
                    "in the template, without any modification, addition or removal:\n\n"
                    f"{locked_list}\n\n"
                    "All other sections must be generated or adapted from the repository code.\n\n"
                )
            else:
                locked_block = (
                    "## Secciones que NO debes modificar\n\n"
                    "Las siguientes secciones deben copiarse **exactamente** como "
                    "aparecen en la plantilla, sin ninguna modificación, adición ni "
                    "eliminación de contenido:\n\n"
                    f"{locked_list}\n\n"
                    "El resto de secciones sí deben generarse o adaptarse según el "
                    "código del repositorio.\n\n"
                )

        # Build per-section enrichment instructions
        enrichment_block = ""
        if section_enrichments:
            lines: list[str] = []
            if lang == "en":
                _labels = {"table": "a Markdown table", "diagram": "a Mermaid diagram"}
                for section, types in section_enrichments.items():
                    what = " and ".join(_labels[t] for t in types if t in _labels)
                    if what:
                        lines.append(f'  - In section "**{section}**" include {what}.')
                if lines:
                    enrichment_block = (
                        "## Elements to include per section\n\n"
                        "For the sections listed below, make sure to incorporate the specified "
                        "elements (table and/or diagram). Use standard Markdown for tables and "
                        "[DIAGRAM]…[/DIAGRAM] tags for Mermaid diagrams:\n\n"
                        + "\n".join(lines) + "\n\n"
                    )
            else:
                _labels = {"table": "una tabla Markdown", "diagram": "un diagrama Mermaid"}
                for section, types in section_enrichments.items():
                    what = " y ".join(_labels[t] for t in types if t in _labels)
                    if what:
                        lines.append(f'  - En la sección "**{section}**" incluye {what}.')
                if lines:
                    enrichment_block = (
                        "## Elementos a incluir por sección\n\n"
                        "Para las secciones indicadas a continuación, asegúrate de "
                        "incorporar los elementos especificados (tabla y/o diagrama). "
                        "Usa el formato Markdown estándar para tablas y las etiquetas "
                        "[DIAGRAM]…[/DIAGRAM] para diagramas Mermaid:\n\n"
                        + "\n".join(lines) + "\n\n"
                    )

        if lang == "en":
            general_rules = (
                "## General instructions\n\n"
                "- Write entirely in English.\n"
                "- Base every statement on the actual repository code; "
                "do not invent features that do not exist.\n"
                "- Do not include introductory text, disclaimers or comments "
                "outside the document itself.\n"
                "- Respond **only** with the complete Markdown document.\n\n"
            )
            intro = (
                "You are a software documentation expert. "
                "Your task is to generate professional Markdown documentation "
                "for the code repository provided below.\n\n"
            )
        else:
            general_rules = (
                "## Instrucciones generales\n\n"
                "- Redacta íntegramente en español.\n"
                "- Basa cada afirmación en el código real del repositorio; "
                "no inventes funcionalidades que no existan.\n"
                "- No incluyas texto introductorio, aclaraciones ni comentarios "
                "fuera del documento en sí.\n"
                "- Responde **únicamente** con el documento Markdown completo.\n\n"
            )
            intro = (
                "Eres un experto en documentación de software. "
                "Tu tarea es generar documentación profesional en Markdown "
                "para el repositorio de código que se proporciona más abajo.\n\n"
            )

        doc_structure_label = "## Document structure\n\n" if lang == "en" else "## Estructura del documento\n\n"

        return (
            f"{lang_directive}"
            f"{intro}"
            f"{persona_block}"
            f"{fmt_instructions}\n\n"
            f"{doc_structure_label}"
            f"{structure_instruction}\n\n"
            f"{locked_block}"
            f"{enrichment_block}"
            f"{general_rules}"
            f"{extra_block}"
            f"---\n\n{repo_context}"
        )

    # ── Generation ────────────────────────────────────────────────────

    def generate(
        self,
        repo_scan: RepoScan,
        template_content: str | None = None,
        locked_sections: list[str] | None = None,
        *,
        section_enrichments: dict | None = None,
        api_key_override: str | None = None,
        model_override: str | None = None,
        provider_override: str | None = None,
        output_lang: str = "es",
    ) -> str:
        """
        Build the prompt for this document type, send it to Gemini, and
        return the response as a Markdown string.

        Parameters
        ----------
        locked_sections : list[str] | None
            Section titles the LLM must reproduce verbatim from the template.
        api_key_override : str | None
            Override the API key from the environment.
        model_override : str | None
            Override the model from the environment.

        Raises
        ------
        ValueError   — configuration problems (see ai_service.call_gemini).
        RuntimeError — API / network / response errors.
        """
        try:
            prompt = self.build_prompt(repo_scan, template_content, locked_sections,
                                       section_enrichments, output_lang)
        except Exception as exc:
            raise RuntimeError(
                f"No se pudo construir el prompt para '{self.DISPLAY_NAME}': {exc}"
            ) from exc

        return ai_service.call_llm(
            prompt,
            api_key_override=api_key_override,
            model_override=model_override,
            provider_override=provider_override,
        )

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

    def output_filename(self, repo_name: str, fmt: str = "docx") -> str:
        suffix = self.FILE_SUFFIX or self.DOC_TYPE
        return f"{repo_name}_{suffix}.{fmt}"

    def output_path(self, repo_name: str, output_dir: str, fmt: str = "docx") -> Path:
        return Path(output_dir) / self.output_filename(repo_name, fmt)
