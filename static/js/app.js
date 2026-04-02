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

// ── Browse handlers ──────────────────────────────────────────────────

async function browseFolder() {
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
  }
}

async function browseFile() {
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
    const id = `sec-${idx}`;

    const item = document.createElement("label");
    item.className = "gd-section-item";
    item.htmlFor   = id;

    const checkbox = document.createElement("input");
    checkbox.type    = "checkbox";
    checkbox.id      = id;
    checkbox.checked = true;                // checked = system will edit this section
    checkbox.className = "gd-section-cb";
    checkbox.dataset.section = title;

    const text = document.createElement("span");
    text.className   = "gd-section-title";
    text.textContent = title;

    item.appendChild(checkbox);
    item.appendChild(text);
    ui.sectionsList.appendChild(item);
  });

  ui.sectionsPanelWrap.style.display = "block";
}

/**
 * Returns the list of section titles the user wants to LOCK (not edited).
 * These are sections whose checkbox is unchecked.
 */
function getLockedSections() {
  const checkboxes = ui.sectionsList.querySelectorAll(".gd-section-cb");
  const locked = [];
  checkboxes.forEach(cb => {
    if (!cb.checked) locked.push(cb.dataset.section);
  });
  return locked.length > 0 ? locked : null;
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

// Select / deselect all
ui.btnSelectAllSections.addEventListener("click", () => {
  ui.sectionsList.querySelectorAll(".gd-section-cb").forEach(cb => cb.checked = true);
});
ui.btnDeselectAllSections.addEventListener("click", () => {
  ui.sectionsList.querySelectorAll(".gd-section-cb").forEach(cb => cb.checked = false);
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
    const resp = await fetch("/api/generate", {
      method:  "POST",
      headers: { "Content-Type": "application/json" },
      body:    JSON.stringify({
        repo_path:        repoPath,
        template_path:    templatePath,
        doc_type:         selectedDocType(),
        primary_color:    ui.colorPrimary.value,
        secondary_color:  ui.colorSecondary.value,
        locked_sections:  getLockedSections(),
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
