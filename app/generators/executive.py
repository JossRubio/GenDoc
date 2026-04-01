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

    PERSONA = """\
Estás redactando una presentación ejecutiva dirigida a tomadores de decisiones:
gerentes, directores, clientes o inversionistas. El lector no es técnico y no
necesita (ni quiere) conocer los detalles de implementación. Su interés es
entender el valor del sistema, qué problema resuelve, qué beneficios aporta
y cuál es su estado actual.

Pautas de redacción:
- Prioriza el impacto de negocio sobre los detalles técnicos.
- Usa lenguaje ejecutivo: conciso, estratégico y orientado a resultados.
- Cada sección debe poder leerse en menos de dos minutos.
- Evita nombres de archivos, fragmentos de código o términos de programación.
  Si mencionas tecnologías, hazlo a nivel de concepto ("usa una base de datos
  relacional"), no de implementación ("usa PostgreSQL 15 con índices B-tree").
- Apoya los puntos clave con datos, métricas o comparaciones cuando el código
  las sugiera (tiempos, volúmenes, número de funcionalidades, etc.).
- El tono es profesional y seguro: el documento debe transmitir que el proyecto
  está bien pensado y aporta valor real a la organización."""

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
