/* ── GenDoc frontend logic ─────────────────────────────────────────── */

const ui = {
  repoInput:      document.getElementById("repoPath"),
  templateInput:  document.getElementById("templatePath"),
  btnBrowseRepo:  document.getElementById("btnBrowseRepo"),
  btnBrowseTpl:   document.getElementById("btnBrowseTemplate"),
  btnGenerate:    document.getElementById("btnGenerate"),
  logArea:        document.getElementById("logArea"),
  progressBar:    document.getElementById("progressBar"),
  progressWrap:   document.getElementById("progressWrap"),
  outputPath:     document.getElementById("outputPath"),
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

function updateOutputIndicator(repoPath) {
  if (!repoPath) {
    ui.outputPath.innerHTML =
      '<span style="color:#b0b0b8">Se mostrará cuando selecciones un repositorio</span>';
    return;
  }
  const sep = repoPath.includes("/") ? "/" : "\\";
  const docPath = repoPath.replace(/[/\\]+$/, "") + sep + "documentacion.docx";
  ui.outputPath.innerHTML =
    `<span class="output-icon">📄</span><span class="gd-output-path">${docPath}</span>`;
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
      updateOutputIndicator(data.path);
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
      body: JSON.stringify({ repo_path: repoPath, template_path: templatePath }),
    });

    clearInterval(ticker);

    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);

    const data = await resp.json();

    // Log each step returned by the backend
    (data.steps ?? [data.message]).forEach((step) => log(step));

    setProgress(100);

    if (data.output_path) {
      ui.outputPath.innerHTML =
        `<span class="output-icon">📄</span><span class="gd-output-path">${data.output_path}</span>`;
      setStatus("done");
    } else {
      setStatus("done");
    }
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

// Allow typing the repo path directly
ui.repoInput.addEventListener("input", () => {
  const hasPath = ui.repoInput.value.trim().length > 0;
  setButtonState(hasPath);
  updateOutputIndicator(ui.repoInput.value.trim());
});

// ── Init ─────────────────────────────────────────────────────────────

setStatus("idle");
setProgress(0);
log("GenDoc listo. Selecciona un repositorio para comenzar.");
