"""
executive.py — Presentación Ejecutiva generator.

Output structure (concise, high-level, no technical jargon):
  1. Resumen ejecutivo
  2. Problema que resuelve
  3. Solución propuesta
  4. Funcionalidades principales
  5. Beneficios y valor agregado
  6. Arquitectura (vista de alto nivel)
  7. Diagramas
  8. Stack tecnológico
  9. Estado actual y roadmap
  10. Conclusiones
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

    EXTRA_INSTRUCTIONS = """\
Para la sección "Diagramas", genera entre 2 y 3 diagramas Mermaid que comuniquen
el VALOR y la ESTRUCTURA del sistema a un público ejecutivo no técnico.

Tipos de diagramas prioritarios para este documento:
- Diagrama de alto nivel que muestre cómo el sistema resuelve el problema del negocio
  (flujo de valor: entrada → proceso → resultado/beneficio)
- Mapa conceptual de las funcionalidades principales y su impacto en el negocio
- Diagrama de componentes o fases del sistema expresado en términos de negocio
  (p. ej. "Recolección de datos" → "Análisis" → "Reporte", sin tecnicismos)
- Línea de tiempo o roadmap visual del estado actual y próximas mejoras (si aplica)

Cada diagrama debe seguir esta estructura exacta:

1. Un párrafo corto orientado al negocio que explique qué muestra el diagrama y
   por qué es relevante para la toma de decisiones.
2. El bloque del diagrama delimitado por las etiquetas [DIAGRAM] y [/DIAGRAM]:

[DIAGRAM]
<código Mermaid válido y completo>
[/DIAGRAM]

Reglas estrictas para los bloques de diagrama:
- Usa ÚNICAMENTE las etiquetas [DIAGRAM] y [/DIAGRAM]. No uses ```mermaid.
- El contenido dentro de las etiquetas debe ser código Mermaid puro y válido.
- No incluyas el bloque %%{init: ...}%% — se añade automáticamente durante el procesado.
- Los tipos de diagrama recomendados son: flowchart LR, flowchart TD o graph LR,
  según lo que mejor transmita la idea de negocio.
- Usa etiquetas en español con terminología de negocio, no de ingeniería.
- Los nodos deben representar CONCEPTOS DE NEGOCIO, FASES o RESULTADOS,
  no módulos de software ni nombres de clases."""

    SECTIONS = [
        "Resumen ejecutivo",
        "Problema que resuelve",
        "Solución propuesta",
        "Funcionalidades principales",
        "Beneficios y valor agregado",
        "Arquitectura (vista de alto nivel)",
        "Diagramas",
        "Stack tecnológico",
        "Estado actual y roadmap",
        "Conclusiones",
    ]
