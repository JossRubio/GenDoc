"""
executive.py — Generator for "Presentación Ejecutiva".

Intended output structure (concise, high-level — no technical jargon):
  1. Portada (nombre del proyecto, fecha)
  2. Resumen ejecutivo (1 página)
  3. Problema que resuelve / propuesta de valor
  4. Tecnologías utilizadas (lista simple, sin código)
  5. Principales funcionalidades (bullets)
  6. Métricas del proyecto (nº de módulos, lenguajes, líneas de código estimadas)
  7. Estado actual y próximos pasos
  8. Equipo / contacto (placeholder)
"""

from __future__ import annotations

from ..repo_reader import RepoScan
from .base import BaseGenerator


class ExecutivePresentationGenerator(BaseGenerator):
    DOC_TYPE     = "executive"
    DISPLAY_NAME = "Presentación Ejecutiva"
    FILE_SUFFIX  = "presentacion_ejecutiva"

    def generate(self, repo_scan: RepoScan, template_path: str | None = None) -> bytes:
        # TODO: implement with Gemini API
        # Suggested prompt strategy:
        #   - Send only the repo structure (no file contents) plus README if present
        #   - Ask the model for a concise executive summary suitable for non-technical stakeholders
        #   - Keep output to ~2-3 pages; use python-docx with styled headings and bullet lists
        raise NotImplementedError(
            "ExecutivePresentationGenerator.generate() — pendiente de implementar"
        )
