# GenDoc

**GenDoc** es una herramienta web local que analiza un repositorio de código y genera automáticamente un borrador de documentación en formato Word (`.docx`), usando un modelo de lenguaje (Gemini) para redactar el contenido.

> **Importante:** el documento generado siempre es un **borrador (draft)**. No debe considerarse documentación final sin antes haber sido revisado en detalle por una persona. Quien lo reciba deberá leerlo completo, corregir lo que sea necesario y aprobarlo si lo encuentra suficientemente bueno, o usarlo como punto de partida para trabajar sobre él.

---

## ¿Qué hace?

1. Escanea los archivos de código fuente de un repositorio local.
2. Construye un prompt y lo envía a Gemini para que redacte la documentación.
3. Convierte el texto generado a un documento Word con estilo profesional.
4. Permite descargar el archivo directamente desde la interfaz.

El documento resultante incluye:

- **Portada** con el nombre del proyecto, la fecha y un aviso de derechos.
- **Índice / Agenda** con enlaces internos que llevan directamente a cada sección del documento.
- **Encabezado** con espacio para el logo de la organización, nombre del autor y mención a GenDoc.
- **Pie de página** con el nombre del proyecto y la fecha.
- Contenido estructurado con títulos, subtítulos, tablas, bloques de código y listas.

---

## Tipos de documento

| Tipo | Descripción |
|------|-------------|
| **Documentación técnica** | Describe la arquitectura, módulos, dependencias y lógica del sistema. Dirigida a desarrolladores. |
| **Manual de usuario** | Explica cómo usar el sistema desde el punto de vista del usuario final. |
| **Presentación ejecutiva** | Resumen de alto nivel orientado a tomadores de decisiones. Incluye "Agenda" en lugar de "Índice". |

---

## Cómo usarla

### Opción A — Ejecutable (recomendada)

1. Descarga la carpeta `dist/` o el archivo `GenDoc.exe`.
2. Asegúrate de que el archivo `.env` esté en la **misma carpeta** que `GenDoc.exe` con tu API Key:
   ```
   GOOGLE_API_KEY=tu_api_key_aqui
   ```
3. Haz doble clic en **`GenDoc.exe`**.  
   El navegador se abrirá automáticamente en `http://localhost:5000`.

No se requiere Python ni ninguna dependencia adicional.

---

### Opción B — Desde el código fuente

#### Requisitos

- Python 3.10 o superior
- Una API Key de [Google AI Studio](https://aistudio.google.com/) (Gemini)

#### Instalación

```bash
# 1. Clonar o descargar el repositorio
git clone <url-del-repo>
cd GenDoc

# 2. Crear y activar un entorno virtual (recomendado)
python -m venv venv
venv\Scripts\activate        # Windows
source venv/bin/activate     # macOS / Linux

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Configurar la API Key en el archivo .env
GOOGLE_API_KEY=tu_api_key_aqui
```

#### Ejecución

```bash
python run.py
```

Se abrirá automáticamente el navegador en `http://localhost:5000`.

### Uso paso a paso

1. **Selecciona el repositorio** haciendo clic en "Examinar" junto al campo correspondiente.
2. *(Opcional)* Selecciona una **plantilla** (`.txt` o `.md`) si quieres guiar el estilo del documento.
3. Elige el **tipo de documento** que deseas generar.
4. *(Opcional)* Ajusta los **colores** de la paleta si quieres personalizar el aspecto del Word.
5. Haz clic en **"⚡ Generar Documentación"** y espera. El log irá mostrando el progreso.
6. Una vez completado, haz clic en **"Descargar"** para obtener el archivo `.docx`.

---

## Personalización del documento

Desde la interfaz es posible configurar dos colores:

- **Color principal** — se aplica al título, subtítulos H1/H2, encabezados de tablas, encabezado y pie de página.
- **Color secundario** — se aplica a subtítulos H3 en adelante, bloques de código e inline code.

---

## Limitaciones conocidas y trabajo pendiente

- **Diagramas**: la herramienta aún no genera ni procesa diagramas (arquitectura, flujo, entidad-relación, etc.). Es una funcionalidad pendiente.
- **Prompts para manual de usuario y presentación ejecutiva**: los prompts específicos para estos tipos de documento todavía están siendo ajustados. Los resultados pueden ser menos precisos que los de documentación técnica.
- El documento generado **siempre requiere revisión humana** antes de ser distribuido o utilizado.

---

## Estructura del proyecto

```
GenDoc/
├── app/
│   ├── generators/        # Lógica de generación por tipo de documento
│   ├── md_to_docx.py      # Conversión de Markdown a Word
│   ├── repo_reader.py     # Escaneo del repositorio
│   ├── routes.py          # Endpoints Flask
│   └── services.py        # Capa de negocio y streaming SSE
├── static/
│   ├── css/main.css
│   └── js/app.js
├── templates/
│   └── index.html
├── requirements.txt
└── run.py
```
