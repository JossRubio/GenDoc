# GenDoc

**GenDoc** es una herramienta web local que analiza un repositorio de código y genera automáticamente un documento de documentación en formato Word (`.docx`), usando un modelo de lenguaje (LLM) para redactar el contenido.

> **Importante:** el documento generado siempre es un **borrador (draft)**. No debe considerarse documentación final sin antes haber sido revisado en detalle por una persona. Quien lo reciba deberá leerlo completo, corregir lo que sea necesario y aprobarlo si lo encuentra suficientemente bueno, o usarlo como punto de partida para trabajar sobre él.

---

## ¿Qué hace?

1. Escanea los archivos de código fuente de un repositorio local.
2. Construye un prompt adaptado al tipo de documento solicitado y lo envía al LLM configurado.
3. Genera el documento final en formato Word (`.docx`) con estilo profesional.
4. Permite descargar el archivo directamente desde la interfaz.

Cuando se proporciona una **plantilla `.docx`**, GenDoc trabaja en modo de edición quirúrgica: en lugar de crear un documento desde cero, edita únicamente las secciones seleccionadas dentro del archivo original, preservando la portada, índice, estilos, márgenes y cualquier sección que el usuario haya bloqueado.

El documento resultante incluye:

- **Portada** con el nombre del proyecto, la fecha y un aviso de derechos.
- **Índice / Agenda** con enlaces internos a cada sección.
- **Encabezado** con espacio para el logo de la organización, nombre del autor y mención a GenDoc.
- **Pie de página** con el nombre del proyecto y la fecha.
- Contenido estructurado con títulos, subtítulos, tablas, bloques de código, listas y diagramas Mermaid.

---

## Tipos de documento

| Tipo | Descripción |
|------|-------------|
| **Documentación técnica** | Describe la arquitectura, módulos, dependencias y lógica del sistema. Dirigida a desarrolladores. |
| **Manual de usuario** | Explica cómo usar el sistema desde el punto de vista del usuario final. |
| **Presentación ejecutiva** | Resumen de alto nivel orientado a tomadores de decisiones. Incluye "Agenda" en lugar de "Índice". |

---

## Proveedores de LLM soportados

| Proveedor | Modelos de ejemplo |
|-----------|--------------------|
| **Google AI** | Gemini 2.5 Pro, Gemini 2.0 Flash |
| **Anthropic** | Claude Opus 4, Claude Sonnet 4 |
| **OpenAI** | GPT-4o, o3 |
| **Azure AI** | Cualquier modelo desplegado en Azure AI Foundry |

Si no se configura una API key en la interfaz, se utiliza la definida en el servidor (archivo `.env`). La detección del proveedor es automática para claves con prefijos conocidos (`sk-ant-`, `sk-`).

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
- Una API Key del proveedor LLM que desees usar

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

---

### Uso paso a paso

1. **Configura el LLM** *(opcional)*: selecciona el proveedor, ingresa tu API key y haz clic en "Cargar API-key" para validarla y elegir un modelo específico.
2. **Selecciona el repositorio** haciendo clic en "Examinar" junto al campo correspondiente. Al hacerlo, se desplegará automáticamente el panel de secciones con las secciones recomendadas para el tipo de documento seleccionado.
3. *(Opcional)* Selecciona una **plantilla `.docx`** si quieres editar un documento existente en lugar de generar uno desde cero. Las secciones detectadas en la plantilla reemplazarán a las recomendadas en el panel.
4. **Gestiona las secciones** desde el panel:
   - Marca o desmarca la columna **Texto** para indicar qué secciones debe redactar el LLM (las desmarcadas se copian tal cual desde la plantilla).
   - Activa **Tablas** o **Diagramas** por sección para incluir esos elementos en el contenido generado.
   - Añade secciones nuevas con el botón **"+ Incorporar sección"**.
   - Edita el nombre de una sección con el ícono ✎, elimínala con ✕, o reordénalas arrastrándolas con el mouse (selección múltiple manteniendo el clic y luego arrastrando).
   - Deshaz cualquier cambio estructural con el botón **↺** ubicado en el encabezado del panel.
5. Elige el **tipo de documento** y el **idioma de salida** (Español o Inglés).
6. *(Opcional)* Ajusta los **colores** de la paleta para personalizar el aspecto del Word.
7. Haz clic en **"⚡ Generar Documentación"** y espera. El log mostrará el progreso en tiempo real.
8. Una vez completado, haz clic en **"Descargar"** para obtener el archivo `.docx`.

---

## Panel de secciones

El panel de secciones es la pieza central del flujo de edición. Aparece automáticamente al seleccionar un repositorio y se actualiza según el contexto:

| Contexto | Comportamiento |
|----------|----------------|
| Solo repositorio | Muestra las **secciones recomendadas** para el tipo de documento y el idioma de salida seleccionados. Se actualiza al cambiar el tipo de documento o el idioma. |
| Repositorio + plantilla `.docx` | Muestra las **secciones detectadas** en la plantilla. El LLM editará solo las secciones marcadas en la columna Texto. |

### Operaciones disponibles por sección

| Acción | Descripción |
|--------|-------------|
| Columna **Texto** | Controla si el LLM redacta esa sección. Si está desmarcada, se copia literalmente desde la plantilla. |
| Columna **Tablas** | Solicita al LLM que incluya al menos una tabla en esa sección. |
| Columna **Diagramas** | Solicita al LLM que incluya un diagrama Mermaid en esa sección. |
| ✎ Editar nombre | Permite renombrar la sección con un input inline. Confirmar con Enter o ✓, cancelar con Escape o ✕. |
| ✕ Eliminar | Elimina la sección del panel. |
| Arrastrar | Reordena las secciones arrastrando cualquier fila. Para mover varias a la vez, haz clic en cada una para seleccionarlas (se resaltan en azul) y luego arrastra cualquiera del grupo. |
| **↺ Deshacer** | Revierte el último cambio estructural (agregar, eliminar, renombrar o reordenar secciones). |

---

## Modo de edición quirúrgica (plantilla `.docx`)

Cuando se carga una plantilla `.docx`, GenDoc entra en modo de edición quirúrgica:

1. Detecta automáticamente las secciones (encabezados H1–H3) presentes en el documento.
2. Genera el contenido **únicamente** para las secciones marcadas con la columna Texto.
3. Reemplaza el contenido de esas secciones en el archivo original preservando:
   - Portada, índice y cualquier sección bloqueada.
   - Estilos de párrafo, fuentes y formato visual de la plantilla.
   - Márgenes y propiedades de página del documento original.
4. Entrega el documento editado listo para descargar.

Se realizaron pruebas exitosas de edición sobre documentos cargados como plantilla utilizando el panel de secciones de la aplicación, confirmando que los márgenes, estilos y secciones bloqueadas se preservan correctamente en el documento resultante.

---

## Personalización del documento

Desde la interfaz es posible configurar:

- **Idioma del documento**: el contenido generado puede redactarse en Español o en Inglés, de forma independiente al idioma de la interfaz.
- **Color principal**: se aplica al título, subtítulos H1/H2 y encabezados de tablas.
- **Color secundario**: se aplica a subtítulos H3 en adelante y bloques de código.

---

## Limitaciones conocidas

- El documento generado **siempre requiere revisión humana** antes de ser distribuido o utilizado.
- Los diagramas Mermaid se incluyen como bloques de código con sintaxis válida; su renderizado como imagen depende de la herramienta con la que se abra el `.docx`.
- Los resultados del LLM varían según el modelo configurado y la calidad del código fuente analizado.

---

## Estructura del proyecto

```
GenDoc/
├── app/
│   ├── generators/        # Lógica de generación por tipo de documento
│   ├── ai_service.py      # Integración multi-proveedor (Google, Anthropic, OpenAI, Azure)
│   ├── md_to_docx.py      # Conversión de Markdown a Word
│   ├── repo_reader.py     # Escaneo del repositorio
│   ├── routes.py          # Endpoints Flask
│   ├── services.py        # Capa de negocio y streaming SSE
│   └── template_editor.py # Edición quirúrgica de plantillas .docx
├── static/
│   ├── css/main.css
│   └── js/app.js
├── templates/
│   └── index.html
├── requirements.txt
└── run.py
```
