"""
user_manual.py — Generator for "Manual de Usuario".

Intended output structure:
  1. Portada
  2. Índice
  3. Introducción — qué hace la aplicación y para quién es
  4. Requisitos del sistema
  5. Instalación paso a paso
  6. Primeros pasos (guía de inicio rápido)
  7. Descripción de la interfaz (pantallas / secciones principales)
  8. Funcionalidades detalladas — flujos de uso con ejemplos
  9. Preguntas frecuentes (FAQ)
  10. Solución de problemas comunes
  11. Glosario
"""

from __future__ import annotations

from ..repo_reader import RepoScan
from .base import BaseGenerator


class UserManualGenerator(BaseGenerator):
    DOC_TYPE     = "user_manual"
    DISPLAY_NAME = "Manual de Usuario"
    FILE_SUFFIX  = "manual_usuario"

    def generate(self, repo_scan: RepoScan, template_path: str | None = None) -> bytes:
        # TODO: implement with Gemini API
        # Suggested prompt strategy:
        #   - Focus on entry-point files (main, app, index) and UI components
        #   - Ask model to describe features from an end-user perspective
        #   - Use plain language, avoid exposing internal implementation details
        #   - Assemble with python-docx including screenshots placeholders
        raise NotImplementedError(
            "UserManualGenerator.generate() — pendiente de implementar"
        )
