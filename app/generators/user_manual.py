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
