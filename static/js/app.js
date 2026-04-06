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
  // LLM config
  providerSelect:         document.getElementById("providerSelect"),
  apiKeyInput:            document.getElementById("apiKeyInput"),
  btnToggleApiKey:        document.getElementById("btnToggleApiKey"),
  apiKeyEyeIcon:          document.getElementById("apiKeyEyeIcon"),
  btnLoadModels:          document.getElementById("btnLoadModels"),
  modelSelectorWrap:      document.getElementById("modelSelectorWrap"),
  modelSelect:            document.getElementById("modelSelect"),
  modelLoadStatus:        document.getElementById("modelLoadStatus"),
};

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

function setStatus(state) {
  const labels = { idle: "Listo", running: "Procesando...", done: "Completado", error: "Error" };
  ui.statusDot.className = `gd-status-dot ${state === "idle" ? "" : state}`;
  ui.statusText.textContent = labels[state] ?? "Listo";
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

// Auto-detect provider from key prefix and sync the selector
function detectProvider(key) {
  if (key.startsWith("sk-ant-")) return "anthropic";
  if (key.startsWith("sk-"))     return "openai";
  return "google";
}

ui.apiKeyInput.addEventListener("input", () => {
  const key = ui.apiKeyInput.value.trim();
  if (key) ui.providerSelect.value = detectProvider(key);
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

async function loadModels() {
  const apiKey = ui.apiKeyInput.value.trim();
  if (!apiKey) {
    setModelStatus("Ingresa una API key primero.", "warn");
    ui.modelSelectorWrap.style.display = "block";
    return;
  }

  ui.btnLoadModels.disabled = true;
  ui.modelSelectorWrap.style.display = "block";
  setModelStatus("Cargando modelos…", "loading");
  ui.modelSelect.innerHTML = '<option value="">Cargando…</option>';

  try {
    const resp = await fetch("/api/models", {
      method:  "POST",
      headers: { "Content-Type": "application/json" },
      body:    JSON.stringify({ api_key: apiKey, provider: ui.providerSelect.value }),
    });
    const data = await resp.json();

    if (data.error) {
      setModelStatus(`Error: ${data.error}`, "error");
      ui.modelSelect.innerHTML = '<option value="">— Sin modelos —</option>';
      return;
    }

    const models = data.models || [];
    ui.modelSelect.innerHTML = '<option value="">— Usar modelo del servidor —</option>';
    models.forEach(m => {
      const opt = document.createElement("option");
      opt.value       = m.id;
      opt.textContent = m.display_name || m.id;
      ui.modelSelect.appendChild(opt);
    });

    setModelStatus(`${models.length} modelo(s) disponible(s)`, "success");
    log(`Modelos cargados: ${models.length}`, "success");
  } catch (err) {
    setModelStatus("No se pudo conectar con el servidor.", "error");
    ui.modelSelect.innerHTML = '<option value="">— Error al cargar —</option>';
  } finally {
    ui.btnLoadModels.disabled = false;
  }
}

ui.btnLoadModels.addEventListener("click", loadModels);

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
      log(`Repositorio seleccionado: ${data.path}`);
    }
  } catch {
    log("No se pudo abrir el selector de carpeta.", "error");
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
      log(`Plantilla seleccionada: ${data.path}`);
      setDocTypeEnabled(false);
      await loadTemplateSections(data.path);
    }
  } catch {
    log("No se pudo abrir el selector de archivo.", "error");
  } finally {
    setBrowseLoading(ui.btnBrowseTpl, false);
  }
}

// ── Template sections panel ──────────────────────────────────────────

function clearSectionsPanel() {
  ui.sectionsList.innerHTML = "";
  ui.sectionsPanelWrap.style.display = "none";
}

function renderSectionsPanel(sections) {
  ui.sectionsList.innerHTML = "";

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
      log(`Secciones detectadas en la plantilla: ${data.sections.length}`);
    } else {
      log("No se detectaron secciones en la plantilla.", "warn");
    }
  } catch {
    log("No se pudieron leer las secciones de la plantilla.", "warn");
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
    log("Selecciona un repositorio primero.", "warn");
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
  log("Iniciando generación de documentación...");

  try {
    const apiKeyOverride   = ui.apiKeyInput.value.trim() || null;
    const modelOverride    = ui.modelSelect.value.trim() || null;
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
      }),
    });

    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    await consumeSSE(resp, repoPath);

  } catch (err) {
    stopProgressTicker();
    log(`Error de comunicación: ${err.message}`, "error");
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

    log(`Descargando ${filename}`, "success");
  } catch (err) {
    log(`Error al iniciar la descarga: ${err.message}`, "error");
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

// ── Init ─────────────────────────────────────────────────────────────

setStatus("idle");
setProgress(0);
log("GenDoc listo. Selecciona un repositorio para comenzar.");
