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
