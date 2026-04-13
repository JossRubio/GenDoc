/* ── GenDoc frontend logic ─────────────────────────────────────────── */

// ── Theme ────────────────────────────────────────────────────────────

(function initTheme() {
  const saved = localStorage.getItem("gd-theme") ?? "light";
  document.documentElement.setAttribute("data-theme", saved);
  document.addEventListener("DOMContentLoaded", () => {
    document.getElementById("themeToggle").checked = saved === "dark";
  });
})();

// ── UI refs ──────────────────────────────────────────────────────────

const ui = {
  repoInput:              document.getElementById("repoPath"),
  templateInput:          document.getElementById("templatePath"),
  btnBrowseRepo:          document.getElementById("btnBrowseRepo"),
  btnBrowseTpl:           document.getElementById("btnBrowseTemplate"),
  btnGenerate:            document.getElementById("btnGenerate"),
  logArea:                document.getElementById("logArea"),
  progressBar:            document.getElementById("progressBar"),
  themeToggle:            document.getElementById("themeToggle"),
  docTypeInputs:          document.querySelectorAll('input[name="docType"]'),
  progressWrap:           document.getElementById("progressWrap"),
  progressPct:            document.getElementById("progressPct"),
  btnDownload:            document.getElementById("btnDownload"),
  btnDownloadLabel:       document.getElementById("btnDownloadLabel"),
  statusDot:              document.getElementById("statusDot"),
  statusText:             document.getElementById("statusText"),
  colorPrimary:           document.getElementById("colorPrimary"),
  colorSecondary:         document.getElementById("colorSecondary"),
  sectionsPanelWrap:      document.getElementById("sectionsPanelWrap"),
  sectionsList:           document.getElementById("sectionsList"),
  btnSelectAllSections:   document.getElementById("btnSelectAllSections"),
  btnDeselectAllSections: document.getElementById("btnDeselectAllSections"),
  outputLangSelect:       document.getElementById("outputLangSelect"),
  // LLM config
  providerSelect:         document.getElementById("providerSelect"),
  apiKeyInput:            document.getElementById("apiKeyInput"),
  btnToggleApiKey:        document.getElementById("btnToggleApiKey"),
  apiKeyEyeIcon:          document.getElementById("apiKeyEyeIcon"),
  btnLoadModels:          document.getElementById("btnLoadModels"),
  modelSelectorWrap:      document.getElementById("modelSelectorWrap"),
  modelSelect:            document.getElementById("modelSelect"),
  modelLoadStatus:        document.getElementById("modelLoadStatus"),
  keyValidStatus:         document.getElementById("keyValidStatus"),
  azureDropdownLabel:     document.getElementById("azureDropdownLabel"),
  azureDeploymentWrap:    document.getElementById("azureDeploymentWrap"),
  azureDeploymentInput:   document.getElementById("azureDeploymentInput"),
};

// ── i18n ─────────────────────────────────────────────────────────────

const TRANSLATIONS = {
  es: {
    subtitle:          "Generador automático de documentación para repositorios",
    themeToggleTitle:  "Cambiar tema",
    themeToggleLabel:  "Activar modo oscuro",
    llmConfig:         "Configuración de LLM",
    optional:          "Opcional",
    apiKeyPlaceholder: "API key del proveedor seleccionado…",
    showHide:          "Mostrar / ocultar",
    loadModels:        "Cargar API-key",
    selectModel:       "— Selecciona un modelo —",
    apiKeyHint:        "Si no configuras una API key, se usará la definida en el servidor.",
    repository:        "Repositorio",
    repoPlaceholder:   "Ruta a la carpeta del repositorio…",
    browse:            "Examinar",
    template:          "Plantilla de documentación",
    templatePlaceholder: "Archivo de referencia (.txt, .md, .docx…)",
    templateHint:      "Proporciona un documento de ejemplo para guiar el estilo de la documentación generada.",
    sectionsDetected:  "Secciones detectadas en la plantilla",
    selectAll:         "Seleccionar todo",
    deselectAll:       "Deseleccionar todo",
    sectionsHint:      "Usa la columna <strong>Texto</strong> para indicar qué secciones debe editar el LLM (las no marcadas se copian exactamente desde la plantilla). Usa <strong>Tablas</strong> y <strong>Diagramas</strong> para solicitar esos elementos en cada sección.",
    colSection:        "Sección detectada",
    colText:           "Texto",
    colTables:         "Tablas",
    colDiagrams:       "Diagramas",
    docType:           "Tipo de documento",
    docTypeTechnical:  "Documentación técnica",
    docTypeUserManual: "Manual de Usuario",
    docTypeExecutive:  "Presentación Ejecutiva",
    outputLangLabel:   "Idioma del documento",
    outputLangEs:      "Español",
    outputLangEn:      "Inglés",
    outputLangHint:    "Define el idioma en que se redactará el contenido del documento generado.",
    colorPalette:      "Paleta de colores",
    primaryColor:      "Color principal",
    primaryColorDesc:  "Título, subtítulos H1/H2 y encabezados de tablas",
    secondaryColor:    "Color secundario",
    secondaryColorDesc:"H3+, código",
    generateBtn:       "Generar Documentación",
    generateHint:      "Selecciona un repositorio para habilitar este botón",
    statusIdle:        "Listo",
    statusRunning:     "Procesando...",
    statusDone:        "Completado",
    statusError:       "Error",
    logAreaLabel:      "Registro de actividad",
    progress:          "Progreso",
    downloadBtn:       "Descargar documentación",
    runningOn:         "Ejecutando en",
    // idle modal
    idleTitle:         "El servidor se cerrará automáticamente",
    idleBody:          "No se detectó actividad. GenDoc se apagará en",
    idleSeconds:       "segundos.",
    idleKeepAlive:     "Mantener activo",
    idleShutdown:      "El servidor se ha cerrado.",
    // dynamic log / status
    logReady:          "GenDoc listo. Selecciona un repositorio para comenzar.",
    logStarting:       "Iniciando generación de documentación...",
    logRepoSelected:   "Repositorio seleccionado:",
    logTemplateSelected: "Plantilla seleccionada:",
    logNoRepo:         "Selecciona un repositorio primero.",
    logNoFolder:       "No se pudo abrir el selector de carpeta.",
    logNoFile:         "No se pudo abrir el selector de archivo.",
    logSections:       "Secciones detectadas en la plantilla:",
    logNoSections:     "No se detectaron secciones en la plantilla.",
    logSectionsError:  "No se pudieron leer las secciones de la plantilla.",
    logModelsLoaded:   "Modelos cargados:",
    logApiKeyFirst:    "Ingresa una API key primero.",
    logConnectError:   "No se pudo conectar con el servidor.",
    logCommError:      "Error de comunicación:",
    logDownloading:    "Descargando",
    logDownloadError:  "Error al iniciar la descarga:",
    serverDefaultModel:"— Usar modelo del servidor —",
    loadingModels:     "Cargando…",
    noModels:          "— Sin modelos —",
    errorLoading:      "— Error al cargar —",
    modelsAvailable:   "modelo(s) disponible(s)",
    modelError:        "Error:",
    azureDeploymentPlaceholder: "Nombre del deployment (ej: gpt-4.1)…",
    azureRecommendedTitle: "Modelos recomendados",
    azureRecommendedWarn:  "(requiere deploy en Foundry)",
    azureTooltip:          "Los modelos mostrados solo funcionarán si el usuario con su api-key configuró el deploy de estos previamente en Azure AI Foundry.",
    azureManualTitle:      "Modelo",
    azureManualHint:       "(si no tienes en deploy las recomendaciones)",
    keyValid:              "✓ API-key válida",
    keyInvalid:            "✗ API-key inválida, revise la clave",
    keyValidating:         "Verificando API-key…",
  },
  en: {
    subtitle:          "Automatic documentation generator for repositories",
    themeToggleTitle:  "Change theme",
    themeToggleLabel:  "Enable dark mode",
    llmConfig:         "LLM Configuration",
    optional:          "Optional",
    apiKeyPlaceholder: "API key for the selected provider…",
    showHide:          "Show / hide",
    loadModels:        "Load API key",
    selectModel:       "— Select a model —",
    apiKeyHint:        "If you don't configure an API key, the server-defined one will be used.",
    repository:        "Repository",
    repoPlaceholder:   "Path to the repository folder…",
    browse:            "Browse",
    template:          "Documentation Template",
    templatePlaceholder: "Reference file (.txt, .md, .docx…)",
    templateHint:      "Provide a sample document to guide the style of the generated documentation.",
    sectionsDetected:  "Sections detected in the template",
    selectAll:         "Select all",
    deselectAll:       "Deselect all",
    sectionsHint:      "Use the <strong>Text</strong> column to indicate which sections the LLM should edit (unmarked ones are copied exactly from the template). Use <strong>Tables</strong> and <strong>Diagrams</strong> to request those elements per section.",
    colSection:        "Detected section",
    colText:           "Text",
    colTables:         "Tables",
    colDiagrams:       "Diagrams",
    docType:           "Document Type",
    docTypeTechnical:  "Technical Documentation",
    docTypeUserManual: "User Manual",
    docTypeExecutive:  "Executive Presentation",
    outputLangLabel:   "Document language",
    outputLangEs:      "Spanish",
    outputLangEn:      "English",
    outputLangHint:    "Sets the language in which the generated document content will be written.",
    colorPalette:      "Color Palette",
    primaryColor:      "Primary color",
    primaryColorDesc:  "Title, H1/H2 subtitles and table headers",
    secondaryColor:    "Secondary color",
    secondaryColorDesc:"H3+, code",
    generateBtn:       "Generate Documentation",
    generateHint:      "Select a repository to enable this button",
    statusIdle:        "Ready",
    statusRunning:     "Processing...",
    statusDone:        "Completed",
    statusError:       "Error",
    logAreaLabel:      "Activity log",
    progress:          "Progress",
    downloadBtn:       "Download documentation",
    runningOn:         "Running on",
    // idle modal
    idleTitle:         "The server will shut down automatically",
    idleBody:          "No activity detected. GenDoc will close in",
    idleSeconds:       "seconds.",
    idleKeepAlive:     "Keep alive",
    idleShutdown:      "The server has been closed.",
    // dynamic
    logReady:          "GenDoc ready. Select a repository to begin.",
    logStarting:       "Starting documentation generation...",
    logRepoSelected:   "Repository selected:",
    logTemplateSelected: "Template selected:",
    logNoRepo:         "Please select a repository first.",
    logNoFolder:       "Could not open the folder selector.",
    logNoFile:         "Could not open the file selector.",
    logSections:       "Sections detected in the template:",
    logNoSections:     "No sections detected in the template.",
    logSectionsError:  "Could not read template sections.",
    logModelsLoaded:   "Models loaded:",
    logApiKeyFirst:    "Please enter an API key first.",
    logConnectError:   "Could not connect to the server.",
    logCommError:      "Communication error:",
    logDownloading:    "Downloading",
    logDownloadError:  "Download error:",
    serverDefaultModel:"— Use server model —",
    loadingModels:     "Loading…",
    noModels:          "— No models —",
    errorLoading:      "— Error loading —",
    modelsAvailable:   "model(s) available",
    modelError:        "Error:",
    azureDeploymentPlaceholder: "Deployment name (e.g. gpt-4.1)…",
    azureRecommendedTitle: "Recommended models",
    azureRecommendedWarn:  "(requires deploy in Foundry)",
    azureTooltip:          "Displayed models will only work if the user with their api-key previously configured the deploy of these in Azure AI Foundry.",
    azureManualTitle:      "Model",
    azureManualHint:       "(if recommended models are not deployed)",
    keyValid:              "✓ API key valid",
    keyInvalid:            "✗ Invalid API key, please check the key",
    keyValidating:         "Verifying API key…",
  },
};

let _lang = localStorage.getItem("gd-lang") || "es";

function t(key) {
  return (TRANSLATIONS[_lang] || TRANSLATIONS.es)[key] ?? key;
}

function applyLang(lang) {
  _lang = lang;
  localStorage.setItem("gd-lang", lang);
  document.documentElement.lang = lang;

  // Update lang toggle buttons
  document.querySelectorAll(".gd-lang-btn").forEach(btn => {
    btn.classList.toggle("active", btn.dataset.lang === lang);
  });

  const tr = TRANSLATIONS[lang] || TRANSLATIONS.es;

  // textContent
  document.querySelectorAll("[data-i18n]").forEach(el => {
    const key = el.dataset.i18n;
    if (tr[key] !== undefined) el.textContent = tr[key];
  });

  // innerHTML (for hints with <strong> tags)
  document.querySelectorAll("[data-i18n-html]").forEach(el => {
    const key = el.dataset.i18nHtml;
    if (tr[key] !== undefined) el.innerHTML = tr[key];
  });

  // placeholder
  document.querySelectorAll("[data-i18n-placeholder]").forEach(el => {
    const key = el.dataset.i18nPlaceholder;
    if (tr[key] !== undefined) el.placeholder = tr[key];
  });

  // title
  document.querySelectorAll("[data-i18n-title]").forEach(el => {
    const key = el.dataset.i18nTitle;
    if (tr[key] !== undefined) el.title = tr[key];
  });

  // aria-label
  document.querySelectorAll("[data-i18n-aria-label]").forEach(el => {
    const key = el.dataset.i18nAriaLabel;
    if (tr[key] !== undefined) el.setAttribute("aria-label", tr[key]);
  });

  // Sync output language dropdown options text
  const olSelect = document.getElementById("outputLangSelect");
  if (olSelect) {
    olSelect.options[0].textContent = tr["outputLangEs"];
    olSelect.options[1].textContent = tr["outputLangEn"];
    // Default selection follows interface lang (only if user hasn't changed it)
    if (!olSelect.dataset.userSet) olSelect.value = lang;
  }

  // Update dynamic elements that are already rendered
  document.getElementById("statusText").textContent =
    { idle: t("statusIdle"), running: t("statusRunning"), done: t("statusDone"), error: t("statusError") }
    [_currentStatus] ?? t("statusIdle");
}

// Wire up language buttons
document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll(".gd-lang-btn").forEach(btn => {
    btn.addEventListener("click", () => applyLang(btn.dataset.lang));
  });

  // Mark output lang dropdown as user-set when changed manually
  const olSel = document.getElementById("outputLangSelect");
  if (olSel) olSel.addEventListener("change", () => { olSel.dataset.userSet = "1"; });

  applyLang(_lang);
});

// ── State ────────────────────────────────────────────────────────────

let isRunning        = false;
let generatedMarkdown = null;   // stored after a successful generation
let _downloadToken   = null;    // one-time token for /api/download/<token>
let _progressTarget  = 0;
let _progressCurrent = 0;
let _progressTicker  = null;

// ── Log & progress helpers ───────────────────────────────────────────

function log(message, level = "info") {
  const prefix = { info: "  ", success: "✓ ", error: "✗ ", warn: "⚠ " }[level] ?? "  ";
  const ts = new Date().toLocaleTimeString("es", { hour12: false });
  ui.logArea.value += `[${ts}] ${prefix}${message}\n`;
  ui.logArea.scrollTop = ui.logArea.scrollHeight;
}

function setProgress(pct) {
  _progressCurrent = Math.min(100, Math.max(0, pct));
  ui.progressBar.style.width = `${_progressCurrent}%`;
  ui.progressPct.textContent = `${Math.round(_progressCurrent)}%`;

  const el = ui.progressPct;
  el.classList.remove("pct-running", "pct-done");
  if (_progressCurrent >= 100) {
    el.classList.add("pct-done");
  } else if (_progressCurrent >= 1) {
    el.classList.add("pct-running");
  }
  // 0 % → no class → inherits --gd-text (black / white per theme)
}

function setProgressTarget(pct) {
  _progressTarget = pct;
}

function startProgressTicker() {
  if (_progressTicker) return;
  _progressTicker = setInterval(() => {
    if (_progressCurrent < _progressTarget) {
      // Quickly catch up to the target set by backend events
      setProgress(_progressCurrent + Math.min(2, _progressTarget - _progressCurrent));
    } else if (_progressCurrent < 88 && isRunning) {
      // Creep slowly forward while waiting for the LLM (40 → 88)
      setProgress(_progressCurrent + 0.15);
    }
  }, 200);
}

function stopProgressTicker() {
  clearInterval(_progressTicker);
  _progressTicker = null;
}

let _currentStatus = "idle";

function setStatus(state) {
  _currentStatus = state;
  const labels = {
    idle:    t("statusIdle"),
    running: t("statusRunning"),
    done:    t("statusDone"),
    error:   t("statusError"),
  };
  ui.statusDot.className    = `gd-status-dot ${state === "idle" ? "" : state}`;
  ui.statusText.textContent = labels[state] ?? t("statusIdle");
}

// ── Download button ──────────────────────────────────────────────────

const DOC_TYPE_SUFFIX = {
  technical:   "documentacion_tecnica",
  user_manual: "manual_usuario",
  executive:   "presentacion_ejecutiva",
};

function repoName(repoPath) {
  return repoPath.replace(/[/\\]+$/, "").split(/[/\\]/).pop() || "repositorio";
}

function selectedDocType() {
  for (const input of ui.docTypeInputs) {
    if (input.checked) return input.value;
  }
  return "technical";
}

function updateDownloadButton(repoPath, enabled = false) {
  if (!repoPath) {
    ui.btnDownloadLabel.textContent = "Descargar documentación";
    ui.btnDownload.disabled = true;
    return;
  }
  const suffix   = DOC_TYPE_SUFFIX[selectedDocType()] ?? "documentacion";
  const filename = `${repoName(repoPath)}_${suffix}.docx`;
  ui.btnDownloadLabel.textContent = `Descargar ${filename}`;
  ui.btnDownload.disabled = !enabled;
}

function setButtonState(enabled) {
  ui.btnGenerate.disabled = !enabled || isRunning;
}

function setDocTypeEnabled(enabled) {
  ui.docTypeInputs.forEach(input => { input.disabled = !enabled; });
  const wrap = document.querySelector(".gd-segment");
  if (wrap) wrap.classList.toggle("gd-segment--disabled", !enabled);
}

// ── LLM config ───────────────────────────────────────────────────────

// Auto-detect provider from key prefix and sync the selector.
// Only switches for known patterns; Azure and Google keys have no standard prefix
// so the user must select those manually.
function detectProvider(key) {
  if (key.startsWith("sk-ant-")) return "anthropic";
  if (key.startsWith("sk-"))     return "openai";
  return null;  // unknown — don't auto-switch
}

function isAzure() {
  return ui.providerSelect.value === "azure";
}

function syncAzureUI() {
  const azure = isAzure();
  // Load models button always visible for all providers
  ui.btnLoadModels.style.display = "";
  // Azure-only columns: dropdown label and manual input
  ui.azureDropdownLabel.style.display  = azure ? "" : "none";
  ui.azureDeploymentWrap.style.display = azure ? "" : "none";
  // Hide model selector and clear key status whenever the provider changes
  ui.modelSelectorWrap.style.display = "none";
  ui.modelSelectorWrap.dataset.wasVisible = "";
  setKeyStatus("", "");
}

ui.providerSelect.addEventListener("change", syncAzureUI);

// Run once on load in case Azure is pre-selected
syncAzureUI();

ui.apiKeyInput.addEventListener("input", () => {
  const key      = ui.apiKeyInput.value.trim();
  const detected = key ? detectProvider(key) : null;
  if (detected) { ui.providerSelect.value = detected; syncAzureUI(); }
});

ui.btnToggleApiKey.addEventListener("click", () => {
  const isHidden = ui.apiKeyInput.type === "password";
  ui.apiKeyInput.type = isHidden ? "text" : "password";
  ui.apiKeyEyeIcon.textContent = isHidden ? "🙈" : "👁";
});

function setModelStatus(msg, type = "info") {
  ui.modelLoadStatus.textContent = msg;
  ui.modelLoadStatus.className = `gd-model-status gd-model-status--${type}`;
}

function setKeyStatus(msg, type = "info") {
  ui.keyValidStatus.textContent = msg;
  ui.keyValidStatus.className = `gd-key-valid-status gd-key-valid-status--${type}`;
}

async function validateKey() {
  const apiKey = ui.apiKeyInput.value.trim();
  if (!apiKey) {
    setKeyStatus(t("logApiKeyFirst"), "warn");
    return;
  }

  ui.btnLoadModels.disabled = true;
  setKeyStatus(t("keyValidating"), "loading");

  // Reset dropdown while loading
  if (!isAzure()) {
    setModelStatus(t("loadingModels"), "loading");
    ui.modelSelect.innerHTML = `<option value="">${t("loadingModels")}</option>`;
  }

  try {
    const resp = await fetch("/api/validate_key", {
      method:  "POST",
      headers: { "Content-Type": "application/json" },
      body:    JSON.stringify({ api_key: apiKey, provider: ui.providerSelect.value }),
    });
    const data = await resp.json();

    if (!data.valid) {
      setKeyStatus(t("keyInvalid"), "invalid");
      if (!isAzure()) {
        setModelStatus(t("errorLoading"), "error");
        ui.modelSelect.innerHTML = `<option value="">${t("noModels")}</option>`;
      }
      return;
    }

    setKeyStatus(t("keyValid"), "valid");
    ui.modelSelectorWrap.style.display = "";
    ui.modelSelectorWrap.dataset.wasVisible = "true";

    // Populate model dropdown for all providers
    const models = data.models || [];
    ui.modelSelect.innerHTML = `<option value="">${t("selectModel")}</option>`;
    models.forEach(m => {
      const opt = document.createElement("option");
      opt.value       = m.id;
      opt.textContent = m.display_name || m.id;
      ui.modelSelect.appendChild(opt);
    });
    if (!isAzure()) {
      setModelStatus(`${models.length} ${t("modelsAvailable")}`, "success");
      log(`${t("logModelsLoaded")} ${models.length}`, "success");
    }
  } catch (err) {
    setKeyStatus(t("logConnectError"), "error");
    if (!isAzure()) {
      setModelStatus(t("errorLoading"), "error");
      ui.modelSelect.innerHTML = `<option value="">${t("errorLoading")}</option>`;
    }
  } finally {
    ui.btnLoadModels.disabled = false;
  }
}

ui.btnLoadModels.addEventListener("click", validateKey);

// ── Browse handlers ──────────────────────────────────────────────────

function setBrowseLoading(btn, loading) {
  if (loading) {
    btn.dataset.originalText = btn.innerHTML;
    btn.innerHTML = '<span class="gd-spinner"></span>';
    btn.disabled  = true;
  } else {
    btn.innerHTML = btn.dataset.originalText || btn.innerHTML;
    btn.disabled  = false;
  }
}

async function browseFolder() {
  setBrowseLoading(ui.btnBrowseRepo, true);
  try {
    const resp = await fetch("/api/browse/folder", { method: "POST" });
    const data = await resp.json();
    if (data.path) {
      ui.repoInput.value = data.path;
      updateDownloadButton(data.path);
      setButtonState(true);
      log(`${t("logRepoSelected")} ${data.path}`);
    }
  } catch {
    log(t("logNoFolder"), "error");
  } finally {
    setBrowseLoading(ui.btnBrowseRepo, false);
  }
}

async function browseFile() {
  setBrowseLoading(ui.btnBrowseTpl, true);
  try {
    const resp = await fetch("/api/browse/file", { method: "POST" });
    const data = await resp.json();
    if (data.path) {
      ui.templateInput.value = data.path;
      log(`${t("logTemplateSelected")} ${data.path}`);
      setDocTypeEnabled(false);
      await loadTemplateSections(data.path);
    }
  } catch {
    log(t("logNoFile"), "error");
  } finally {
    setBrowseLoading(ui.btnBrowseTpl, false);
  }
}

// ── Template sections panel ──────────────────────────────────────────

function clearSectionsPanel() {
  ui.sectionsList.querySelectorAll(".gd-section-item").forEach(el => el.remove());
  ui.sectionsPanelWrap.style.display = "none";
}

function renderSectionsPanel(sections) {
  ui.sectionsList.querySelectorAll(".gd-section-item").forEach(el => el.remove());

  if (!sections || sections.length === 0) {
    ui.sectionsPanelWrap.style.display = "none";
    return;
  }

  sections.forEach((title, idx) => {
    const row = document.createElement("div");
    row.className = "gd-section-item";

    // ── Col 1: section name ────────────────────────────────────────
    const nameCell = document.createElement("div");
    nameCell.className = "gd-section-name-cell";
    const nameSpan = document.createElement("span");
    nameSpan.className   = "gd-section-title";
    nameSpan.textContent = title;
    nameCell.appendChild(nameSpan);

    // ── Col 2: Texto / edit checkbox ───────────────────────────────
    const editId = `sec-edit-${idx}`;
    const editCb = document.createElement("input");
    editCb.type            = "checkbox";
    editCb.id              = editId;
    editCb.checked         = true;
    editCb.className       = "gd-section-cb";
    editCb.dataset.section = title;
    editCb.dataset.role    = "edit";

    const editCell = document.createElement("div");
    editCell.className = "gd-enrich-cell";
    const editLabel = document.createElement("label");
    editLabel.htmlFor  = editId;
    editLabel.title    = "Generar / editar texto de esta sección";
    editCell.appendChild(editCb);
    editCell.appendChild(editLabel);

    // ── Col 3: Tabla checkbox ──────────────────────────────────────
    const tableId = `sec-tbl-${idx}`;
    const tableCb = document.createElement("input");
    tableCb.type            = "checkbox";
    tableCb.id              = tableId;
    tableCb.checked         = false;
    tableCb.className       = "gd-section-enrich-cb";
    tableCb.dataset.section = title;
    tableCb.dataset.role    = "table";

    const tableCell = document.createElement("div");
    tableCell.className = "gd-enrich-cell";
    const tableLabel = document.createElement("label");
    tableLabel.htmlFor = tableId;
    tableLabel.title   = "Incluir tabla en esta sección";
    tableCell.appendChild(tableCb);
    tableCell.appendChild(tableLabel);

    // ── Col 4: Diagrama checkbox ───────────────────────────────────
    const diagId = `sec-diag-${idx}`;
    const diagCb = document.createElement("input");
    diagCb.type            = "checkbox";
    diagCb.id              = diagId;
    diagCb.checked         = false;
    diagCb.className       = "gd-section-enrich-cb";
    diagCb.dataset.section = title;
    diagCb.dataset.role    = "diagram";

    const diagCell = document.createElement("div");
    diagCell.className = "gd-enrich-cell";
    const diagLabel = document.createElement("label");
    diagLabel.htmlFor = diagId;
    diagLabel.title   = "Incluir diagrama en esta sección";
    diagCell.appendChild(diagCb);
    diagCell.appendChild(diagLabel);

    // Disable enrichment checkboxes when edit (Texto) is unchecked
    editCb.addEventListener("change", () => {
      tableCb.disabled = !editCb.checked;
      diagCb.disabled  = !editCb.checked;
      if (!editCb.checked) { tableCb.checked = false; diagCb.checked = false; }
    });

    row.appendChild(nameCell);
    row.appendChild(editCell);
    row.appendChild(tableCell);
    row.appendChild(diagCell);
    ui.sectionsList.appendChild(row);
  });

  ui.sectionsPanelWrap.style.display = "block";
}

/**
 * Returns the list of section titles the user wants to LOCK (not edited).
 */
function getLockedSections() {
  const locked = [];
  ui.sectionsList.querySelectorAll(".gd-section-cb[data-role='edit']").forEach(cb => {
    if (!cb.checked) locked.push(cb.dataset.section);
  });
  return locked.length > 0 ? locked : null;
}

/**
 * Returns a dict { sectionTitle: ["table","diagram"] } for sections where
 * at least one enrichment (table / diagram) is checked.
 */
function getSectionEnrichments() {
  const result = {};
  ui.sectionsList.querySelectorAll(".gd-section-enrich-cb:checked").forEach(cb => {
    const sec = cb.dataset.section;
    if (!result[sec]) result[sec] = [];
    result[sec].push(cb.dataset.role);   // "table" or "diagram"
  });
  return Object.keys(result).length > 0 ? result : null;
}

async function loadTemplateSections(templatePath) {
  clearSectionsPanel();
  if (!templatePath) return;

  try {
    const resp = await fetch("/api/template/sections", {
      method:  "POST",
      headers: { "Content-Type": "application/json" },
      body:    JSON.stringify({ template_path: templatePath }),
    });
    const data = await resp.json();

    if (data.error) {
      log(`Plantilla: ${data.error}`, "warn");
      return;
    }

    if (data.sections && data.sections.length > 0) {
      renderSectionsPanel(data.sections);
      log(`${t("logSections")} ${data.sections.length}`);
    } else {
      log(t("logNoSections"), "warn");
    }
  } catch {
    log(t("logSectionsError"), "warn");
  }
}

// Select / deselect all (edit column only)
ui.btnSelectAllSections.addEventListener("click", () => {
  ui.sectionsList.querySelectorAll(".gd-section-cb[data-role='edit']").forEach(cb => {
    cb.checked = true;
    // re-enable enrichment checkboxes
    const idx = cb.id.replace("sec-edit-", "");
    document.getElementById(`sec-tbl-${idx}`).disabled  = false;
    document.getElementById(`sec-diag-${idx}`).disabled = false;
  });
});
ui.btnDeselectAllSections.addEventListener("click", () => {
  ui.sectionsList.querySelectorAll(".gd-section-cb[data-role='edit']").forEach(cb => {
    cb.checked = false;
    const idx = cb.id.replace("sec-edit-", "");
    const tbl  = document.getElementById(`sec-tbl-${idx}`);
    const diag = document.getElementById(`sec-diag-${idx}`);
    tbl.checked = false;  tbl.disabled  = true;
    diag.checked = false; diag.disabled = true;
  });
});

// ── SSE stream consumer ──────────────────────────────────────────────

async function consumeSSE(resp, repoPath) {
  const reader  = resp.body.getReader();
  const decoder = new TextDecoder();
  let buffer    = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });

    // SSE lines end with \n\n; split on double newline
    const blocks = buffer.split("\n\n");
    buffer = blocks.pop();  // last (possibly incomplete) block stays in buffer

    for (const block of blocks) {
      for (const line of block.split("\n")) {
        if (!line.startsWith("data: ")) continue;
        let event;
        try { event = JSON.parse(line.slice(6)); } catch { continue; }
        handleEvent(event, repoPath);
      }
    }
  }
}

function handleEvent(event, repoPath) {
  switch (event.type) {
    case "log":
      log(event.message, event.level ?? "info");
      break;

    case "progress":
      setProgressTarget(event.pct);
      break;

    case "done":
      // Markdown is ready but docx conversion is still in progress — keep running state
      generatedMarkdown = event.markdown;
      break;

    case "ready":
      stopProgressTicker();
      setProgress(100);
      _downloadToken = event.token;
      updateDownloadButton(repoPath, true);
      setStatus("done");
      break;

    case "error":
      stopProgressTicker();
      log(event.message, "error");
      setProgress(0);
      setStatus("error");
      break;
  }
}

// ── Generate handler ─────────────────────────────────────────────────

async function generate() {
  if (isRunning) return;

  const repoPath     = ui.repoInput.value.trim();
  const templatePath = ui.templateInput.value.trim();

  if (!repoPath) {
    log(t("logNoRepo"), "warn");
    return;
  }

  isRunning         = true;
  generatedMarkdown = null;
  _downloadToken    = null;
  _progressCurrent  = 0;
  _progressTarget   = 0;

  setButtonState(false);
  updateDownloadButton(repoPath, false);
  setStatus("running");
  setProgress(0);
  startProgressTicker();
  log(t("logStarting"));

  try {
    const apiKeyOverride   = ui.apiKeyInput.value.trim() || null;
    const modelOverride    = isAzure()
      ? (ui.azureDeploymentInput.value.trim() || null)
      : (ui.modelSelect.value.trim() || null);
    const providerOverride = apiKeyOverride ? ui.providerSelect.value : null;

    const resp = await fetch("/api/generate", {
      method:  "POST",
      headers: { "Content-Type": "application/json" },
      body:    JSON.stringify({
        repo_path:            repoPath,
        template_path:        templatePath,
        doc_type:             selectedDocType(),
        primary_color:        ui.colorPrimary.value,
        secondary_color:      ui.colorSecondary.value,
        locked_sections:      getLockedSections(),
        section_enrichments:  getSectionEnrichments(),
        api_key_override:     apiKeyOverride,
        model_override:       modelOverride,
        provider_override:    providerOverride,
        lang:                 _lang,
        output_lang:          ui.outputLangSelect.value || _lang,
      }),
    });

    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    await consumeSSE(resp, repoPath);

  } catch (err) {
    stopProgressTicker();
    log(`${t("logCommError")} ${err.message}`, "error");
    setStatus("error");
    setProgress(0);
  } finally {
    isRunning = false;
    setButtonState(!!ui.repoInput.value.trim());
  }
}

// ── Event listeners ──────────────────────────────────────────────────

// ── Download handler ─────────────────────────────────────────────────

async function download() {
  if (!_downloadToken) return;

  try {
    const resp = await fetch(`/api/download/${_downloadToken}`);
    if (!resp.ok) {
      const data = await resp.json().catch(() => ({}));
      log(data.error ?? `Error al descargar (HTTP ${resp.status}).`, "error");
      return;
    }

    // Extract filename from Content-Disposition or fall back to button label
    const disposition = resp.headers.get("Content-Disposition") ?? "";
    const nameMatch   = disposition.match(/filename\*?=(?:UTF-8'')?["']?([^;"'\n]+)/i);
    const filename    = nameMatch ? decodeURIComponent(nameMatch[1]) : "documentacion.docx";

    const blob = await resp.blob();
    const url  = URL.createObjectURL(blob);
    const a    = document.createElement("a");
    a.href     = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);

    log(`${t("logDownloading")} ${filename}`, "success");
  } catch (err) {
    log(`${t("logDownloadError")} ${err.message}`, "error");
  }
}

ui.btnBrowseRepo.addEventListener("click", browseFolder);
ui.btnBrowseTpl.addEventListener("click", browseFile);
ui.btnGenerate.addEventListener("click", generate);
ui.btnDownload.addEventListener("click", download);

ui.docTypeInputs.forEach((input) => {
  input.addEventListener("change", () => {
    updateDownloadButton(ui.repoInput.value.trim(), !ui.btnDownload.disabled);
  });
});

ui.themeToggle.addEventListener("change", () => {
  const theme = ui.themeToggle.checked ? "dark" : "light";
  document.documentElement.setAttribute("data-theme", theme);
  localStorage.setItem("gd-theme", theme);
});

ui.repoInput.addEventListener("input", () => {
  const path = ui.repoInput.value.trim();
  setButtonState(path.length > 0);
  updateDownloadButton(path);
});

ui.templateInput.addEventListener("input", () => {
  const hasTemplate = ui.templateInput.value.trim().length > 0;
  setDocTypeEnabled(!hasTemplate);
  if (!hasTemplate) clearSectionsPanel();
});

// ── Auto-shutdown / idle tracker (exe only) ──────────────────────────
//
// Flow:
//   • While the user is active: heartbeat sent every 5 s → server stays alive.
//   • After IDLE_WARN_MS (90 s) of no interaction: heartbeats stop, countdown
//     modal appears with a 30-second timer.
//   • "Mantener activo" resets everything.
//   • If the countdown reaches 0 the server shuts down on its own (no more
//     heartbeats for ≥ HEARTBEAT_TIMEOUT = 120 s total).
//   • When NOT running as exe (window.GENDOC_IS_EXE === false) nothing happens.

(function initIdleShutdown() {
  if (!window.GENDOC_IS_EXE) return;

  const IDLE_WARN_MS  = 90_000;   // show popup after 90 s idle
  const COUNTDOWN_SEC = 30;       // countdown duration shown in modal

  const modal      = document.getElementById("idleModal");
  const countdownEl= document.getElementById("idleCountdown");
  const keepAlive  = document.getElementById("btnIdleKeepAlive");

  let lastActivity  = Date.now();
  let heartbeatActive = true;
  let countdownVal  = COUNTDOWN_SEC;
  let countdownTimer = null;

  // ── Heartbeat sender ──────────────────────────────────────────────
  async function ping() {
    try { await fetch("/api/heartbeat", { method: "POST" }); } catch {}
  }

  // Send first ping immediately, then every 5 s while active
  ping();
  setInterval(() => { if (heartbeatActive) ping(); }, 5000);

  // ── Activity tracking ─────────────────────────────────────────────
  function onActivity() {
    lastActivity = Date.now();
    if (!heartbeatActive) {
      // User came back during countdown → cancel and reset
      resetIdle();
    }
  }

  ["mousemove", "mousedown", "keydown", "touchstart", "scroll", "click"]
    .forEach(evt => window.addEventListener(evt, onActivity, { passive: true }));

  // ── Countdown modal ───────────────────────────────────────────────
  function showCountdown() {
    heartbeatActive  = false;
    countdownVal     = COUNTDOWN_SEC;
    countdownEl.textContent = countdownVal;
    modal.style.display = "flex";

    countdownTimer = setInterval(() => {
      countdownVal -= 1;
      countdownEl.textContent = countdownVal;
      countdownEl.classList.toggle("urgent", countdownVal <= 10);
      if (countdownVal <= 0) {
        clearInterval(countdownTimer);
        countdownEl.textContent = "0";
        // Server will shut down on its own — show final message
        countdownEl.closest(".gd-idle-box").querySelector(".gd-idle-title")
          .textContent = t("idleShutdown");
        keepAlive.style.display = "none";
      }
    }, 1000);
  }

  function resetIdle() {
    clearInterval(countdownTimer);
    countdownTimer = null;
    heartbeatActive = true;
    lastActivity    = Date.now();
    modal.style.display = "none";
    // Restore modal text in case it was changed
    modal.querySelector(".gd-idle-title").textContent =
      "El servidor se cerrará automáticamente";
    keepAlive.style.display = "";
    ping(); // immediate ping to reset server-side timer
  }

  keepAlive.addEventListener("click", resetIdle);

  // ── Idle checker (runs every second) ─────────────────────────────
  setInterval(() => {
    if (!heartbeatActive) return;   // already in countdown
    if (Date.now() - lastActivity >= IDLE_WARN_MS) {
      showCountdown();
    }
  }, 1000);
})();

// ── Init ─────────────────────────────────────────────────────────────

setStatus("idle");
setProgress(0);
log(t("logReady"));
