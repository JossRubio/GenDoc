import json

from flask import Blueprint, Response, render_template, jsonify, request, stream_with_context

from .services import browse_folder, browse_file, generate_documentation_stream

main = Blueprint("main", __name__)


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
    body = request.get_json(silent=True) or {}
    repo_path     = (body.get("repo_path")     or "").strip()
    template_path = (body.get("template_path") or "").strip() or None
    doc_type      = (body.get("doc_type")      or "").strip() or None

    if not repo_path:
        # Return a minimal SSE error so the client can handle it uniformly
        def immediate_error():
            yield f"data: {json.dumps({'type': 'error', 'message': 'No se recibió la ruta del repositorio.'})}\n\n"
        return Response(immediate_error(), mimetype="text/event-stream")

    def event_stream():
        for event in generate_documentation_stream(repo_path, template_path, doc_type):
            yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"

    return Response(
        stream_with_context(event_stream()),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",   # disable nginx buffering if proxied
            "Connection": "keep-alive",
        },
    )
