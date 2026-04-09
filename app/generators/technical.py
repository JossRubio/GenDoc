"""
technical.py — Documentación Técnica generator.

Output structure:
  1.  Resumen del proyecto
  2.  Arquitectura general del sistema
  3.  Estructura de carpetas y archivos
  4.  Descripción de módulos y componentes
  5.  Flujo de datos / lógica principal
  6.  Dependencias y requisitos
  7.  Instrucciones de instalación y configuración
  8.  Variables de entorno
  9.  API / endpoints (si aplica)
  10. Diagramas de flujo o arquitectura (descripción textual)
  11. Notas técnicas y decisiones de diseño
"""

from __future__ import annotations

from .base import BaseGenerator


class TechnicalDocsGenerator(BaseGenerator):
    DOC_TYPE     = "technical"
    DISPLAY_NAME = "Documentación técnica"
    FILE_SUFFIX  = "documentacion_tecnica"

    PERSONA = """\
Estás redactando documentación técnica dirigida a desarrolladores de software,
arquitectos de sistemas y equipos de operaciones. El lector tiene experiencia
programando y está familiarizado con conceptos como APIs, dependencias, variables
de entorno y patrones de diseño.

Pautas de redacción:
- Usa terminología técnica precisa; no simplifiques conceptos que el lector ya domina.
- Describe el "cómo" y el "por qué" de las decisiones de implementación.
- Incluye nombres reales de archivos, módulos, clases y funciones cuando sea relevante.
- Usa bloques de código para ejemplos de configuración, comandos o fragmentos clave.
- Las tablas son útiles para listar parámetros, variables de entorno o endpoints.
- El tono es formal-técnico: directo, sin adornos, pero completo en el detalle."""

    EXTRA_INSTRUCTIONS = """\
Para la sección "Diagramas", genera entre 1 y 3 diagramas Mermaid que representen
la arquitectura o los flujos más relevantes del repositorio (arquitectura de
componentes, flujo de datos, secuencia de llamadas, etc.).

Cada diagrama debe seguir esta estructura exacta:

1. Un párrafo corto que explique qué representa el diagrama.
2. El bloque del diagrama delimitado por las etiquetas [DIAGRAM] y [/DIAGRAM]:

[DIAGRAM]
<código Mermaid válido y completo>
[/DIAGRAM]

Reglas estrictas para los bloques de diagrama:
- Usa ÚNICAMENTE las etiquetas [DIAGRAM] y [/DIAGRAM]. No uses ```mermaid.
- El contenido dentro de las etiquetas debe ser código Mermaid puro y válido.
- No incluyas el bloque %%{init: ...}%% — se añade automáticamente durante el procesado.
- Los tipos de diagrama recomendados son: graph TD, graph LR, sequenceDiagram,
  classDiagram o flowchart TD, según lo que mejor describa el sistema.
- Basa los diagramas en el código real: módulos, rutas, clases o funciones que
  realmente existan en el repositorio."""

    SECTIONS = [
        "Resumen del proyecto",
        "Arquitectura general del sistema",
        "Estructura de carpetas y archivos",
        "Descripción de módulos y componentes",
        "Flujo de datos / lógica principal",
        "Dependencias y requisitos",
        "Instrucciones de instalación y configuración",
        "Variables de entorno",
        "API / endpoints (si aplica)",
        "Diagramas",
        "Notas técnicas y decisiones de diseño",
    ]

    SECTIONS_EN = [
        "Project summary",
        "System architecture overview",
        "Folder and file structure",
        "Modules and components description",
        "Data flow / main logic",
        "Dependencies and requirements",
        "Installation and configuration instructions",
        "Environment variables",
        "API / endpoints (if applicable)",
        "Diagrams",
        "Technical notes and design decisions",
    ]

    PERSONA_EN = """\
You are writing technical documentation aimed at software developers,
systems architects and operations teams. The reader has programming experience
and is familiar with concepts such as APIs, dependencies, environment variables
and design patterns.

Writing guidelines:
- Use precise technical terminology; do not simplify concepts the reader already masters.
- Describe the "how" and "why" behind implementation decisions.
- Include real file names, modules, classes and functions where relevant.
- Use code blocks for configuration examples, commands or key snippets.
- Tables are useful for listing parameters, environment variables or endpoints.
- The tone is formal-technical: direct, unadorned, but thorough in detail."""

    EXTRA_INSTRUCTIONS_EN = """\
For the "Diagrams" section, generate between 1 and 3 Mermaid diagrams representing
the most relevant architecture or flows of the repository (component architecture,
data flow, call sequence, etc.).

Each diagram must follow this exact structure:

1. A short paragraph explaining what the diagram represents.
2. The diagram block delimited by the [DIAGRAM] and [/DIAGRAM] tags:

[DIAGRAM]
<valid and complete Mermaid code>
[/DIAGRAM]

Strict rules for diagram blocks:
- Use ONLY the [DIAGRAM] and [/DIAGRAM] tags. Do not use ```mermaid.
- The content inside the tags must be pure, valid Mermaid code.
- Do not include the %%{init: ...}%% block — it is added automatically during processing.
- Recommended diagram types: graph TD, graph LR, sequenceDiagram, classDiagram
  or flowchart TD, whichever best describes the system.
- Base diagrams on real code: modules, routes, classes or functions that actually
  exist in the repository."""
