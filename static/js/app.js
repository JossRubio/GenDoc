/* ── GenDoc frontend logic ─────────────────────────────────────────── */

// ── Theme ────────────────────────────────────────────────────────────

(function initTheme() {
  const saved = localStorage.getItem("gd-theme") ?? "light";
  document.documentElement.setAttribute("data-theme", saved);
  // Sync checkbox after DOM is ready
  document.addEventListener("DOMContentLoaded", () => {
    document.getElementById("themeToggle").checked = saved === "dark";
  });
})();

// ── UI refs ──────────────────────────────────────────────────────────

const ui = {
  repoInput:      document.getElementById("repoPath"),
  templateInput:  document.getElementById("templatePath"),
  btnBrowseRepo:  document.getElementById("btnBrowseRepo"),
  btnBrowseTpl:   document.getElementById("btnBrowseTemplate"),
  btnGenerate:    document.getElementById("btnGenerate"),
  logArea:        document.getElementById("logArea"),
  progressBar:    document.getElementById("progressBar"),
  themeToggle:    document.getElementById("themeToggle"),
  docTypeInputs:  document.querySelectorAll('input[name="docType"]'),
  progressWrap:   document.getElementById("progressWrap"),
  btnDownload:    document.getElementById("btnDownload"),
  btnDownloadLabel: document.getElementById("btnDownloadLabel"),
  statusDot:      document.getElementById("statusDot"),
  statusText:     document.getElementById("statusText"),
};

// ── State ───────────────────────────────────────────────────────────

let isRunning = false;

// ── Helpers ─────────────────────────────────────────────────────────

function log(message, type = "info") {
  const prefix = {
    info:    "  ",
    success: "✓ ",
    error:   "✗ ",
    warn:    "⚠ ",
  }[type] ?? "  ";

  const timestamp = new Date().toLocaleTimeString("es", { hour12: false });
  ui.logArea.value += `[${timestamp}] ${prefix}${message}\n`;
  ui.logArea.scrollTop = ui.logArea.scrollHeight;
}

function setProgress(pct) {
  ui.progressBar.style.width = `${Math.min(100, Math.max(0, pct))}%`;
}

function setStatus(state) {
  // state: "idle" | "running" | "done" | "error"
  const labels = {
    idle:    "Listo",
    running: "Procesando...",
    done:    "Completado",
    error:   "Error",
  };
  ui.statusDot.className = `gd-status-dot ${state === "idle" ? "" : state}`;
  ui.statusText.textContent = labels[state] ?? "Listo";
}

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

// ── Browse handlers ─────────────────────────────────────────────────

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
  } catch (err) {
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
    }
  } catch (err) {
    log("No se pudo abrir el selector de archivo.", "error");
  }
}

// ── Generate handler ────────────────────────────────────────────────

async function generate() {
  if (isRunning) return;

  const repoPath     = ui.repoInput.value.trim();
  const templatePath = ui.templateInput.value.trim();

  if (!repoPath) {
    log("Selecciona un repositorio primero.", "warn");
    return;
  }

  isRunning = true;
  setButtonState(false);
  setStatus("running");
  setProgress(0);
  log("Iniciando generación de documentación...");

  try {
    // Animate progress bar while waiting
    let fakePct = 0;
    const ticker = setInterval(() => {
      fakePct = Math.min(fakePct + Math.random() * 8, 85);
      setProgress(fakePct);
    }, 400);

    const resp = await fetch("/api/generate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ repo_path: repoPath, template_path: templatePath, doc_type: selectedDocType() }),
    });

    clearInterval(ticker);

    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);

    const data = await resp.json();

    // Log each step returned by the backend
    (data.steps ?? [data.message]).forEach((step) => log(step));

    setProgress(100);
    updateDownloadButton(repoPath, /* enabled */ !data.error);
    setStatus(data.error ? "error" : "done");
  } catch (err) {
    log(`Error de comunicación: ${err.message}`, "error");
    setStatus("error");
    setProgress(0);
  } finally {
    isRunning = false;
    setButtonState(!!ui.repoInput.value.trim());
  }
}

// ── Event listeners ─────────────────────────────────────────────────

ui.btnBrowseRepo.addEventListener("click", browseFolder);
ui.btnBrowseTpl.addEventListener("click", browseFile);
ui.btnGenerate.addEventListener("click", generate);

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

// Allow typing the repo path directly
ui.repoInput.addEventListener("input", () => {
  const path = ui.repoInput.value.trim();
  setButtonState(path.length > 0);
  updateDownloadButton(path);
});

// ── Init ─────────────────────────────────────────────────────────────

setStatus("idle");
setProgress(0);
log("GenDoc listo. Selecciona un repositorio para comenzar.");
