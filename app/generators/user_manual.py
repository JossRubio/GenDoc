"""
user_manual.py — Manual de Usuario generator.

Output structure:
  1.  Introducción y propósito de la herramienta
  2.  Requisitos previos
  3.  Instalación / acceso
  4.  Primeros pasos
  5.  Guía de uso paso a paso
  6.  Descripción de funcionalidades
  7.  Casos de uso frecuentes
  8.  Preguntas frecuentes (FAQ)
  9.  Solución de problemas comunes
  10. Glosario
"""

from __future__ import annotations

from .base import BaseGenerator


class UserManualGenerator(BaseGenerator):
    DOC_TYPE     = "user_manual"
    DISPLAY_NAME = "Manual de Usuario"
    FILE_SUFFIX  = "manual_usuario"

    SECTIONS = [
        "Introducción y propósito de la herramienta",
        "Requisitos previos",
        "Instalación / acceso",
        "Primeros pasos",
        "Guía de uso paso a paso",
        "Descripción de funcionalidades",
        "Casos de uso frecuentes",
        "Preguntas frecuentes (FAQ)",
        "Solución de problemas comunes",
        "Glosario",
    ]
