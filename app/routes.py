import json
import os
import secrets
import time

from flask import (
    Blueprint, Response, render_template, jsonify,
    request, send_file, stream_with_context,
)

from . import ai_service
from .services import browse_folder, browse_file, generate_documentation_stream, extract_template_sections

main = Blueprint("main", __name__)

# In-memory token → absolute file path store.
# Tokens are single-use and cleared on each new generation.
_download_tokens: dict[str, str] = {}

# ── Heartbeat (used only when running as GenDoc.exe) ─────────────────
# launcher.py sets this to a callable that shuts the process down.
# When running via run.py it stays None and heartbeats are ignored.
_shutdown_callback = None
_last_heartbeat: float = 0.0


def register_shutdown(callback) -> None:
    """Called by launcher.py to wire up the shutdown hook."""
    global _shutdown_callback, _last_heartbeat
    _shutdown_callback = callback
    _last_heartbeat = time.monotonic()


@main.route("/")
def index():
    return render_template("index.html", is_exe=bool(os.environ.get("GENDOC_EXE")))


@main.route("/api/browse/folder", methods=["POST"])
def api_browse_folder():
    path = browse_folder()
    return jsonify({"path": path})


@main.route("/api/browse/file", methods=["POST"])
def api_browse_file():
    path = browse_file()
    return jsonify({"path": path})


@main.route("/api/template/sections", methods=["POST"])
def api_template_sections():
    body          = request.get_json(silent=True) or {}
    template_path = (body.get("template_path") or "").strip()

    if not template_path:
        return jsonify({"sections": [], "error": "No se proporcionó ruta de plantilla."}), 400

    sections, error = extract_template_sections(template_path)
    if error:
        return jsonify({"sections": [], "error": error}), 200  # non-fatal; caller shows warning

    return jsonify({"sections": sections})


@main.route("/api/models", methods=["POST"])
def api_list_models():
    body     = request.get_json(silent=True) or {}
    api_key  = (body.get("api_key")  or "").strip()
    provider = (body.get("provider") or "").strip() or None

    if not api_key:
        return jsonify({"error": "No se proporcionó API key."}), 400

    try:
        models = ai_service.list_models(api_key, provider)
        return jsonify({"models": models, "provider": provider or ai_service.detect_provider(api_key)})
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 401
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@main.route("/api/validate_key", methods=["POST"])
def api_validate_key():
    body     = request.get_json(silent=True) or {}
    api_key  = (body.get("api_key")  or "").strip()
    provider = (body.get("provider") or "").strip() or None

    if not api_key:
        return jsonify({"valid": False, "error": "No se proporcionó API key."}), 400

    try:
        models = ai_service.validate_key(api_key, provider)
        return jsonify({"valid": True, "models": models})
    except ValueError as exc:
        return jsonify({"valid": False, "error": str(exc)})
    except Exception as exc:
        return jsonify({"valid": False, "error": str(exc)}), 500


@main.route("/api/test_model", methods=["POST"])
def api_test_model():
    body     = request.get_json(silent=True) or {}
    api_key  = (body.get("api_key")  or "").strip()
    provider = (body.get("provider") or "").strip()
    model    = (body.get("model")    or "").strip()

    if not api_key or not model:
        return jsonify({"available": False, "error": "Falta API key o nombre de modelo."}), 400

    try:
        ai_service.test_model(api_key, provider, model)
        return jsonify({"available": True})
    except (ValueError, RuntimeError) as exc:
        return jsonify({"available": False, "error": str(exc)})
    except Exception as exc:
        return jsonify({"available": False, "error": str(exc)}), 500


@main.route("/api/generate", methods=["POST"])
def api_generate():
    body             = request.get_json(silent=True) or {}
    repo_path        = (body.get("repo_path")        or "").strip()
    template_path    = (body.get("template_path")    or "").strip() or None
    doc_type         = (body.get("doc_type")          or "").strip() or None
    primary_color    = (body.get("primary_color")    or "").strip() or None
    secondary_color  = (body.get("secondary_color")  or "").strip() or None
    locked_sections     = body.get("locked_sections")      # list[str] | None
    section_enrichments = body.get("section_enrichments")  # dict[str, list[str]] | None
    api_key_override    = (body.get("api_key_override")  or "").strip() or None
    model_override      = (body.get("model_override")    or "").strip() or None
    provider_override   = (body.get("provider_override") or "").strip() or None
    lang                = (body.get("lang")              or "es").strip()
    if lang not in ("es", "en"):
        lang = "es"
    output_lang         = (body.get("output_lang")       or "es").strip()
    if output_lang not in ("es", "en"):
        output_lang = "es"

    if not isinstance(locked_sections, list):
        locked_sections = None
    if not isinstance(section_enrichments, dict):
        section_enrichments = None

    if not repo_path:
        def immediate_error():
            yield f"data: {json.dumps({'type': 'error', 'message': 'No se recibió la ruta del repositorio.'})}\n\n"
        return Response(immediate_error(), mimetype="text/event-stream")

    def event_stream():
        for event in generate_documentation_stream(repo_path, template_path, doc_type,
                                                    primary_color, secondary_color,
                                                    locked_sections, section_enrichments,
                                                    api_key_override, model_override,
                                                    provider_override, lang, output_lang):
            # When the document is ready, mint a download token and include it
            # in the event so the browser never receives the raw filesystem path.
            if event.get("type") == "ready":
                _download_tokens.clear()
                token = secrets.token_urlsafe(32)
                _download_tokens[token] = event["output_path"]
                event = {
                    "type":     "ready",
                    "token":    token,
                    "filename": event["filename"],
                }
            yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"

    return Response(
        stream_with_context(event_stream()),
        mimetype="text/event-stream",
        headers={
            "Cache-Control":    "no-cache",
            "X-Accel-Buffering": "no",
            "Connection":       "keep-alive",
        },
    )


@main.route("/api/download/<token>", methods=["GET"])
def api_download(token: str):
    file_path = _download_tokens.get(token)
    if not file_path:
        return jsonify({"error": "Token de descarga inválido o expirado."}), 404

    try:
        return send_file(
            file_path,
            as_attachment=True,
            download_name=_download_tokens.get(token + "_name")
                          or file_path.rsplit("/", 1)[-1].rsplit("\\", 1)[-1],
        )
    except FileNotFoundError:
        return jsonify({"error": "El archivo no se encontró en el servidor."}), 404
    except PermissionError:
        return jsonify({"error": "Sin permisos para leer el archivo generado."}), 403
    except OSError as exc:
        return jsonify({"error": f"Error al enviar el archivo: {exc}"}), 500


@main.route("/api/heartbeat", methods=["POST"])
def api_heartbeat():
    """
    Called by the browser every few seconds while the tab is open.
    Only has effect when running as GenDoc.exe (shutdown callback is registered).
    """
    global _last_heartbeat
    _last_heartbeat = time.monotonic()
    return "", 204
