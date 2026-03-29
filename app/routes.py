from flask import Blueprint, render_template, jsonify, request
from .services import browse_folder, browse_file, generate_documentation

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
        return jsonify({"steps": ["Error: no se recibió la ruta del repositorio."], "error": "no_path"}), 400

    result = generate_documentation(repo_path, template_path, doc_type)
    return jsonify(result)
