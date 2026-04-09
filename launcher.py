"""
launcher.py — Entry point for the GenDoc executable built with PyInstaller.

Run directly:   python launcher.py
As bundled exe: GenDoc.exe
"""

from __future__ import annotations

import ctypes
import os
import sys
import threading
import time
import webbrowser


# ── Resolve base directory ────────────────────────────────────────────
# When frozen by PyInstaller, all bundled files land in sys._MEIPASS.
# When running as plain Python, the base is the project root.

if getattr(sys, "frozen", False):
    _base    = sys._MEIPASS                         # bundled extraction dir
    _exe_dir = os.path.dirname(sys.executable)      # folder containing the .exe
else:
    _base    = os.path.dirname(os.path.abspath(__file__))
    _exe_dir = _base


# ── Load .env from the exe's folder (so the user can edit it) ────────
from dotenv import load_dotenv
load_dotenv(os.path.join(_exe_dir, ".env"), override=False)


# ── Configuration ─────────────────────────────────────────────────────
PORT = 5000
URL  = f"http://localhost:{PORT}"


# ── Error helper (shows a native Windows message box) ────────────────
def _show_error(message: str) -> None:
    try:
        ctypes.windll.user32.MessageBoxW(
            0, message, "GenDoc — Error de inicio", 0x10  # MB_ICONERROR
        )
    except Exception:
        print(f"[ERROR] {message}", file=sys.stderr)


# ── Browser opener ────────────────────────────────────────────────────
def _open_browser() -> None:
    time.sleep(1.5)
    webbrowser.open(URL)


# ── Main ──────────────────────────────────────────────────────────────
def main() -> None:
    try:
        from app import create_app
        flask_app = create_app(
            base_dir=_base if getattr(sys, "frozen", False) else None
        )
    except Exception as exc:
        _show_error(
            f"No se pudo inicializar la aplicación:\n\n{exc}\n\n"
            "Verifica que el archivo .env esté en la misma carpeta que GenDoc.exe."
        )
        sys.exit(1)

    # Check if port is already in use before starting
    import socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as _s:
        if _s.connect_ex(("127.0.0.1", PORT)) == 0:
            _show_error(
                f"El puerto {PORT} ya está en uso.\n\n"
                "Puede que haya otra instancia de GenDoc corriendo.\n"
                "Ciérrala e intenta de nuevo."
            )
            sys.exit(1)

    threading.Thread(target=_open_browser, daemon=True).start()

    # Use Werkzeug's threaded server (supports SSE streaming correctly)
    flask_app.run(
        host="127.0.0.1",
        port=PORT,
        debug=False,
        use_reloader=False,
        threaded=True,
    )


if __name__ == "__main__":
    main()
