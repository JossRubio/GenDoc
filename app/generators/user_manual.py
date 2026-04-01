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
