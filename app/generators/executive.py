"""
executive.py — Presentación Ejecutiva generator.

Output structure (concise, high-level, no technical jargon):
  1. Resumen ejecutivo
  2. Problema que resuelve
  3. Solución propuesta
  4. Funcionalidades principales
  5. Beneficios y valor agregado
  6. Arquitectura (vista de alto nivel)
  7. Stack tecnológico
  8. Estado actual y roadmap
  9. Conclusiones
"""

from __future__ import annotations

from .base import BaseGenerator


class ExecutivePresentationGenerator(BaseGenerator):
    DOC_TYPE     = "executive"
    DISPLAY_NAME = "Presentación Ejecutiva"
    FILE_SUFFIX  = "presentacion_ejecutiva"

    SECTIONS = [
        "Resumen ejecutivo",
        "Problema que resuelve",
        "Solución propuesta",
        "Funcionalidades principales",
        "Beneficios y valor agregado",
        "Arquitectura (vista de alto nivel)",
        "Stack tecnológico",
        "Estado actual y roadmap",
        "Conclusiones",
    ]
