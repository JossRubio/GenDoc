"""
user_manual.py — Manual de Usuario generator.

Output structure:
  1.  Introducción y propósito de la herramienta
  2.  Requisitos previos
  3.  Instalación / acceso
  4.  Primeros pasos
  5.  Guía de uso paso a paso
  6.  Descripción de funcionalidades
  7.  Diagramas de flujo de uso
  8.  Casos de uso frecuentes
  9.  Preguntas frecuentes (FAQ)
  10. Solución de problemas comunes
  11. Glosario
"""

from __future__ import annotations

from .base import BaseGenerator


class UserManualGenerator(BaseGenerator):
    DOC_TYPE     = "user_manual"
    DISPLAY_NAME = "Manual de Usuario"
    FILE_SUFFIX  = "manual_usuario"

    PERSONA = """\
Estás redactando un manual de usuario dirigido a personas que utilizarán la
aplicación en su trabajo diario. El lector NO es desarrollador: puede tener
poca o ninguna experiencia técnica. Su único interés es saber cómo usar la
herramienta para realizar sus tareas.

Pautas de redacción:
- Usa lenguaje claro, sencillo y amigable. Evita jerga técnica; si debes usar
  algún término especializado, explícalo en el momento.
- Escribe en modo imperativo y segunda persona ("Haz clic en…", "Ingresa tu…",
  "Selecciona la opción…").
- Organiza las instrucciones en pasos numerados, cortos y concretos.
- Describe lo que el usuario VE y HACE, no cómo funciona el código por dentro.
- Anticipa dudas comunes y explica qué hacer cuando algo no funciona como se espera.
- El tono es cercano y de apoyo: el manual debe sentirse como una guía que
  acompaña al usuario, no como un manual de ingeniería."""

    EXTRA_INSTRUCTIONS = """\
Para la sección "Diagramas de flujo de uso", genera entre 2 y 4 diagramas Mermaid
que ayuden al usuario a entender CÓMO SE USA la herramienta. Los diagramas deben
ser claros para personas sin conocimientos técnicos.

Tipos de diagramas prioritarios para este documento:
- Flujo de navegación o pasos que sigue el usuario para completar una tarea principal
- Diagrama de decisión que muestre qué hacer ante distintos escenarios (p. ej. errores)
- Secuencia de pasos para una funcionalidad clave (instalación, configuración inicial,
  uso típico)
- Mapa de funcionalidades accesibles desde la interfaz principal

Cada diagrama debe seguir esta estructura exacta:

1. Un párrafo corto (en lenguaje no técnico) que explique para qué sirve el diagrama.
2. El bloque del diagrama delimitado por las etiquetas [DIAGRAM] y [/DIAGRAM]:

[DIAGRAM]
<código Mermaid válido y completo>
[/DIAGRAM]

Reglas estrictas para los bloques de diagrama:
- Usa ÚNICAMENTE las etiquetas [DIAGRAM] y [/DIAGRAM]. No uses ```mermaid.
- El contenido dentro de las etiquetas debe ser código Mermaid puro y válido.
- No incluyas el bloque %%{init: ...}%% — se añade automáticamente durante el procesado.
- Los tipos de diagrama recomendados son: flowchart TD, flowchart LR o sequenceDiagram,
  según lo que mejor represente el flujo del usuario.
- Usa etiquetas en español y descripciones comprensibles para usuarios finales.
- Los nodos deben reflejar ACCIONES del usuario o PANTALLAS/ESTADOS que ve,
  no componentes internos del sistema."""

    SECTIONS = [
        "Introducción y propósito de la herramienta",
        "Requisitos previos",
        "Instalación / acceso",
        "Primeros pasos",
        "Guía de uso paso a paso",
        "Descripción de funcionalidades",
        "Diagramas de flujo de uso",
        "Casos de uso frecuentes",
        "Preguntas frecuentes (FAQ)",
        "Solución de problemas comunes",
        "Glosario",
    ]

    SECTIONS_EN = [
        "Introduction and purpose of the tool",
        "Prerequisites",
        "Installation / access",
        "Getting started",
        "Step-by-step usage guide",
        "Feature descriptions",
        "Usage flow diagrams",
        "Common use cases",
        "Frequently asked questions (FAQ)",
        "Troubleshooting",
        "Glossary",
    ]

    PERSONA_EN = """\
You are writing a user manual aimed at people who will use the application in their
daily work. The reader is NOT a developer: they may have little or no technical
experience. Their only interest is knowing how to use the tool to complete their tasks.

Writing guidelines:
- Use clear, simple and friendly language. Avoid technical jargon; if you must use
  a specialised term, explain it on the spot.
- Write in imperative mood and second person ("Click on…", "Enter your…",
  "Select the option…").
- Organise instructions in numbered, short and concrete steps.
- Describe what the user SEES and DOES, not how the code works internally.
- Anticipate common questions and explain what to do when something doesn't work as expected.
- The tone is warm and supportive: the manual should feel like a guide accompanying
  the user, not an engineering handbook."""

    EXTRA_INSTRUCTIONS_EN = """\
For the "Usage flow diagrams" section, generate between 2 and 4 Mermaid diagrams
that help the user understand HOW TO USE the tool. Diagrams must be clear to people
without technical knowledge.

Priority diagram types for this document:
- Navigation flow or steps the user follows to complete a main task
- Decision diagram showing what to do in different scenarios (e.g. errors)
- Sequence of steps for a key feature (installation, initial setup, typical use)
- Map of features accessible from the main interface

Each diagram must follow this exact structure:

1. A short paragraph (in non-technical language) explaining what the diagram is for.
2. The diagram block delimited by the [DIAGRAM] and [/DIAGRAM] tags:

[DIAGRAM]
<valid and complete Mermaid code>
[/DIAGRAM]

Strict rules for diagram blocks:
- Use ONLY the [DIAGRAM] and [/DIAGRAM] tags. Do not use ```mermaid.
- The content inside the tags must be pure, valid Mermaid code.
- Do not include the %%{init: ...}%% block — it is added automatically during processing.
- Recommended diagram types: flowchart TD, flowchart LR or sequenceDiagram,
  whichever best represents the user flow.
- Use English labels and descriptions understandable by end users.
- Nodes must reflect USER ACTIONS or SCREENS/STATES the user sees,
  not internal system components."""
