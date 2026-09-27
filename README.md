# GenDoc

**GenDoc** es una herramienta web local que analiza un repositorio de código y genera automáticamente un documento de documentación —Word (`.docx`), PDF o PowerPoint (`.pptx`)— usando un modelo de lenguaje (LLM) para redactar el contenido.

> **Importante:** el documento generado siempre es un **borrador (draft)**. No debe considerarse documentación final sin antes haber sido revisado en detalle por una persona. Quien lo reciba deberá leerlo completo, corregir lo que sea necesario y aprobarlo si lo encuentra suficientemente bueno, o usarlo como punto de partida para trabajar sobre él.

---

## ¿Qué hace?

1. Escanea los archivos de código fuente de un repositorio local.
2. Construye un prompt adaptado al tipo de documento solicitado y lo envía al LLM configurado.
3. Genera el documento final con estilo profesional.
4. Permite descargar el archivo directamente desde la interfaz.

El formato de salida lo determina la plantilla: sin plantilla, o con una en `.txt`/`.md`/`.docx`,
el resultado es un `.docx`; con una plantilla `.pdf` el resultado es un PDF, y con una `.pptx`
es una presentación de PowerPoint.

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
| **Google AI** | Gemini 3 Flash, Gemini 2.5 Flash |
| **Anthropic** | Claude Sonnet 4.5, Claude Opus 4 |
| **OpenAI** | GPT-4o, o3 |
| **Custom** | Cualquier modelo servido desde un endpoint propio |

La detección del proveedor es automática para claves con prefijos conocidos (`sk-ant-` → Anthropic, `sk-` → OpenAI). Para Google AI y Custom se selecciona el proveedor manualmente desde la interfaz.

### Proveedor Custom

Al elegir **Custom** aparecen dos campos: el **endpoint** donde están desplegados los modelos y la **API-key** de ese servidor. No está atado a ningún fabricante: lo que importa es el formato de API que habla el endpoint, no de quién es el modelo que sirve.

| Formato | Cubre |
|---|---|
| **OpenAI compatible** (por defecto) | Azure AI Foundry, Azure OpenAI, DeepSeek, Moonshot (Kimi), Qwen, Mistral, Groq, Together, OpenRouter, vLLM, Ollama, LM Studio, gateways corporativos |
| **Anthropic** | Proxies y gateways que hablan la Messages API |
| **Google Gemini** | Proxies que hablan `generateContent` |

El formato se detecta solo a partir del endpoint; el desplegable permite forzarlo cuando la URL no lo delata. Al pulsar **Cargar API-key** GenDoc pide al endpoint su lista de modelos: si el servidor no la publica, el campo **Modelo** permite escribir el nombre a mano.

El endpoint también puede fijarse por defecto con la variable `LLM_ENDPOINT` en el `.env` (`AZURE_AI_ENDPOINT` sigue funcionando como alias).

---

## Stack tecnológico

GenDoc es una aplicación **Flask que corre en local**: no hay servidor remoto, base de datos
ni build step de frontend. El repositorio que analizas y tu API key nunca salen de tu máquina,
salvo el contenido del prompt que se envía al proveedor LLM que hayas configurado.

### Backend

| Componente | Tecnología | Rol |
|------------|------------|-----|
| Lenguaje | **Python 3.10+** | Toda la lógica de la aplicación |
| Servidor web | **Flask 3** | Sirve la interfaz, expone los endpoints JSON y emite el progreso por streaming |
| Progreso en vivo | **Server-Sent Events** | El log y la barra de progreso se alimentan de un stream `text/event-stream` |
| Configuración | **python-dotenv** | Carga `LLM_API_KEY`, `LLM_ENDPOINT` y demás variables desde `.env` |
| Diálogos de archivo | **tkinter** (librería estándar) | Selector nativo de carpeta de repositorio y de plantilla |

### Integración con LLMs

| Librería | Proveedor |
|----------|-----------|
| **google-genai** | Google AI (Gemini) |
| **anthropic** | Anthropic (Claude) |
| **openai** | OpenAI y cualquier endpoint que hable su formato, incluido el proveedor **Custom** |

El proveedor Custom reutiliza estas tres librerías apuntándolas a un `base_url` propio, según
el formato de API que hable el endpoint. Ver [Proveedor Custom](#proveedor-custom).

### Generación de documentos

| Librería | Rol |
|----------|-----|
| **python-docx** | Construcción del `.docx`: portada, índice, estilos, tablas e imágenes |
| **python-pptx** | Generación de presentaciones `.pptx` y lectura de secciones de plantillas PowerPoint |
| **docx2pdf** | Salida en PDF, convirtiendo el `.docx` intermedio |
| **pypdf** | Lectura de secciones de plantillas PDF |
| **Mermaid CLI** (`mmdc`) | Renderizado de diagramas Mermaid a PNG — externo y opcional |

> **Dos dependencias externas al ecosistema Python:** la salida en **PDF** requiere
> **Microsoft Word** instalado (docx2pdf lo automatiza vía COM, solo Windows), y los diagramas
> como imagen requieren **Node.js** con `@mermaid-js/mermaid-cli`. Sin ellas, el resto de la
> herramienta funciona con normalidad: la salida `.docx`/`.pptx` no se ve afectada y los
> diagramas caen a bloque de código.

### Frontend

| Componente | Tecnología |
|------------|------------|
| Plantillas | **Jinja2**, servidas por Flask (una sola página) |
| Estilos base | **Bootstrap 5.3.3** vía CDN, únicamente para layout y reset; el aspecto se define en `static/css/main.css` |
| Lógica de interfaz | **JavaScript vanilla** — sin framework, sin bundler, sin paso de compilación |
| Temas e idioma | Preferencias en `localStorage`; los textos se traducen desde un diccionario en `app.js` |

### Empaquetado

| Herramienta | Rol |
|-------------|-----|
| **PyInstaller** | Empaqueta la aplicación completa en `GenDoc.exe` |
| **Pillow** | Genera el ícono del ejecutable (`build/create_icon.py`) |

Ambas se instalan solo para construir el `.exe`; están comentadas en `requirements.txt`.

---

## Cómo usarla

### Opción A — Ejecutable (recomendada)

1. Descarga el archivo `GenDoc.exe`.
2. Haz doble clic en **`GenDoc.exe`**.  
   El navegador se abrirá automáticamente en `http://localhost:5000`.
3. Ingresa tu API key directamente en la interfaz (campo **Configuración de LLM**).

> **La API key es obligatoria cuando se usa el ejecutable.** El `.exe` no carga claves desde ningún archivo de configuración; cada usuario debe ingresar la suya en la interfaz antes de generar.

No se requiere Python ni ninguna dependencia adicional. El ejecutable puede ubicarse en cualquier carpeta del sistema.

#### Cierre automático del proceso

Cuando se ejecuta como `.exe`, el servidor se apaga automáticamente si detecta inactividad prolongada:

- Mientras el usuario interactúa con la interfaz, se envían señales de actividad cada 5 segundos.
- Tras **90 segundos** sin interacción (sin mover el mouse, escribir, hacer scroll ni hacer clic), aparece un modal de cuenta regresiva de 30 segundos.
- Si el usuario no hace clic en **"Mantener activo"** antes de que el contador llegue a cero, el proceso del servidor se cierra solo.
- Esto también cubre el caso de cerrar la pestaña del navegador: al no recibir señales de actividad durante 120 segundos en total, el proceso termina sin necesidad de hacerlo manualmente.

---

### Opción B — Desde el código fuente

#### Requisitos

- Python 3.10 o superior
- Una API key del proveedor LLM que desees usar

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

# 4. (Opcional) Configurar una API key por defecto en el archivo .env
LLM_API_KEY=tu_api_key_aqui
```

#### Ejecución

```bash
python run.py
```

Se abrirá automáticamente el navegador en `http://localhost:5000`.

> En modo código fuente, si se configura `LLM_API_KEY` en el archivo `.env`, esa clave se usa como fallback cuando no se ingresa ninguna en la interfaz. Si se ingresa una key en la interfaz, esta tiene prioridad.

---

### Uso paso a paso

1. **Configura el LLM**: selecciona el proveedor, ingresa tu API key y haz clic en **"Cargar API-key"** para validarla y elegir un modelo específico.
   - Al usar el ejecutable, este paso es **obligatorio**.
   - Al usar el código fuente con `.env` configurado, puede omitirse si ya hay una clave definida en el servidor.
2. **Selecciona el repositorio** haciendo clic en **"Examinar"** junto al campo correspondiente.
3. *(Opcional)* Selecciona una **plantilla** si quieres partir de un documento existente en lugar de generar uno desde cero. Con una plantilla `.docx` se activa la edición quirúrgica; con `.pdf` o `.pptx` se determina el formato de salida. Las secciones detectadas en la plantilla reemplazarán a las recomendadas en el panel.
4. Elige el **idioma del documento** (Español o Inglés) y el **tipo de documento**. Ambos campos están sobre el panel de secciones porque lo determinan: al cambiarlos, el panel se recarga con las secciones y las sugerencias que correspondan.
5. **Gestiona las secciones** desde el panel, que se despliega automáticamente:
   - Marca o desmarca la columna **Texto** para indicar qué secciones debe redactar el LLM (las desmarcadas se copian tal cual desde la plantilla).
   - Revisa las casillas **Tablas** y **Diagramas**. Las que llegan marcadas de inicio (señaladas con un punto) son las que la IA sugiere para esa sección; desmarcarlas prohíbe ese elemento allí.
   - Añade secciones nuevas con el botón **"+ Incorporar sección"**.
   - Edita el nombre de una sección con el ícono ✎, elimínala con ✕, o reordénalas arrastrándolas con el mouse (selección múltiple manteniendo el clic y luego arrastrando).
   - Deshaz cualquier cambio estructural con el botón **↺** ubicado en el encabezado del panel.
6. *(Opcional)* Ajusta los **colores** de la paleta para personalizar el aspecto del documento.
7. Haz clic en **"⚡ Generar Documentación"** y espera. El log mostrará el progreso en tiempo real.
8. Una vez completado, haz clic en **"Descargar"** para obtener el archivo.

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
| Columna **Tablas** | Solicita al LLM que incluya al menos una tabla en esa sección. Si está desmarcada, el LLM tiene **prohibido** usar tablas ahí. |
| Columna **Diagramas** | Solicita al LLM que incluya un diagrama Mermaid en esa sección. Si está desmarcada, el LLM tiene **prohibido** usar diagramas ahí. |
| ✎ Editar nombre | Permite renombrar la sección con un input inline. Confirmar con Enter o ✓, cancelar con Escape o ✕. |
| ✕ Eliminar | Elimina la sección del panel. |
| Arrastrar | Reordena las secciones arrastrando cualquier fila. Para mover varias a la vez, haz clic en cada una para seleccionarlas (se resaltan en azul) y luego arrastra cualquiera del grupo. |
| **↺ Deshacer** | Revierte el último cambio estructural (agregar, eliminar, renombrar o reordenar secciones). |

### Sugerencias de la IA

Cada tipo de documento declara qué secciones se benefician de una tabla o un diagrama
(por ejemplo, *Variables de entorno* → tabla, *Arquitectura general del sistema* → diagrama).
Esas casillas aparecen **marcadas de inicio** y se señalan con un punto, de modo que el
usuario vea la sugerencia antes de generar en lugar de descubrirla en el `.docx`.

Las casillas son **vinculantes en ambos sentidos**: el prompt instruye al LLM a incluir
los elementos marcados y le prohíbe explícitamente usar tablas o diagramas en cualquier
sección donde la casilla esté desmarcada. Esta prohibición tiene prioridad sobre el
resto de instrucciones del prompt.

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

---

## Personalización del documento

Desde la interfaz es posible configurar:

- **Idioma del documento**: el contenido generado puede redactarse en Español o en Inglés, de forma independiente al idioma de la interfaz.
- **Idioma de la interfaz**: la interfaz puede cambiarse entre Español e Inglés mediante los botones **ES / EN** en la esquina superior derecha.
- **Color principal**: se aplica al título, subtítulos H1/H2 y encabezados de tablas.
- **Color secundario**: se aplica a subtítulos H3 en adelante y bloques de código.

---

## Limitaciones conocidas

- El documento generado **siempre requiere revisión humana** antes de ser distribuido o utilizado.
- Los diagramas Mermaid se renderizan como imagen y se incrustan en el documento, pero esto requiere tener instalado el **Mermaid CLI** (`npm install -g @mermaid-js/mermaid-cli`), que a su vez necesita Node.js. Si `mmdc` no está disponible en el sistema, el diagrama se inserta como bloque de código etiquetado y el documento sigue siendo utilizable.
- Los resultados del LLM varían según el modelo configurado y la calidad del código fuente analizado.

---

## Estructura del proyecto

```
GenDoc/
├── app/
│   ├── generators/        # Lógica de generación por tipo de documento
│   ├── ai_service.py      # Integración multi-proveedor (Google, Anthropic, OpenAI, Custom)
│   ├── md_to_docx.py      # Conversión de Markdown a Word
│   ├── md_to_pdf.py       # Conversión de Markdown a PDF
│   ├── md_to_pptx.py      # Conversión de Markdown a PowerPoint
│   ├── repo_reader.py     # Escaneo del repositorio
│   ├── routes.py          # Endpoints Flask
│   ├── services.py        # Capa de negocio y streaming SSE
│   └── template_editor.py # Edición quirúrgica de plantillas .docx
├── build/
│   ├── build.bat          # Script de build del ejecutable
│   └── create_icon.py     # Generación del ícono
├── static/
│   ├── css/main.css
│   └── js/app.js
├── templates/
│   └── index.html
├── dist/
│   └── GenDoc.exe         # Ejecutable listo para distribuir
├── gendoc.spec            # Configuración de PyInstaller
├── launcher.py            # Entry point del ejecutable
├── requirements.txt
└── run.py                 # Entry point para desarrollo
```
