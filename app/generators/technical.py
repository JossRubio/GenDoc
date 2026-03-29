"""
technical.py — Generator for "Documentación Técnica".

Intended output structure:
  1. Portada (nombre del proyecto, fecha, versión)
  2. Índice
  3. Descripción general del proyecto
  4. Arquitectura y estructura de carpetas
  5. Módulos y componentes (uno por archivo relevante)
     - Propósito
     - Dependencias
     - Funciones / clases públicas con firma y descripción
  6. Flujos de datos principales
  7. Configuración y variables de entorno
  8. Instrucciones de instalación y ejecución
  9. Guía de contribución
"""

from __future__ import annotations

from ..repo_reader import RepoScan
from .base import BaseGenerator


class TechnicalDocsGenerator(BaseGenerator):
    DOC_TYPE    = "technical"
    DISPLAY_NAME = "Documentación técnica"
    FILE_SUFFIX  = "documentacion_tecnica"

    def generate(self, repo_scan: RepoScan, template_path: str | None = None) -> bytes:
        # TODO: implement with Gemini API
        # Suggested prompt strategy:
        #   - Send repo structure + each file content to the model
        #   - Ask for a structured technical description per module
        #   - Assemble sections with python-docx
        raise NotImplementedError(
            "TechnicalDocsGenerator.generate() — pendiente de implementar"
        )
