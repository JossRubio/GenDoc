import json
import secrets

from flask import (
    Blueprint, Response, render_template, jsonify,
    request, send_file, stream_with_context,
)

from .services import browse_folder, browse_file, generate_documentation_stream

main = Blueprint("main", __name__)

# In-memory token → absolute file path store.
# Tokens are single-use and cleared on each new generation.
_download_tokens: dict[str, str] = {}


@main.route("/")
def index():
    return render_template("index.html")


@main.route("/api/browse/folder", methods=["POST"])
def api_browse_folder():
    path = browse_folder()
    return jsonify({"path": path})


@main.route("/api/browse/file", methods=["POST"])
def api_browse_file():
    path = browse_file()
    return jsonify({"path": path})


@main.route("/api/generate", methods=["POST"])
def api_generate():
    body          = request.get_json(silent=True) or {}
    repo_path     = (body.get("repo_path")     or "").strip()
    template_path = (body.get("template_path") or "").strip() or None
    doc_type      = (body.get("doc_type")      or "").strip() or None

    if not repo_path:
        def immediate_error():
            yield f"data: {json.dumps({'type': 'error', 'message': 'No se recibió la ruta del repositorio.'})}\n\n"
        return Response(immediate_error(), mimetype="text/event-stream")

    def event_stream():
        for event in generate_documentation_stream(repo_path, template_path, doc_type):
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
