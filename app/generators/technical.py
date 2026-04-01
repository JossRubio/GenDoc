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
        "Diagramas de flujo o arquitectura (descripción textual)",
        "Notas técnicas y decisiones de diseño",
    ]
