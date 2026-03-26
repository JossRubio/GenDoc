from flask import Blueprint, render_template, jsonify
from .services import browse_folder, browse_file, generate_documentation

main = Blueprint("main", __name__)


@main.route("/")
def index():
    return render_template("index.html")


@main.route("/api/browse/folder", methods=["POST"])
def api_browse_folder():
    path = browse_folder()
    if path:
        return jsonify({"path": path})
    return jsonify({"path": None})


@main.route("/api/browse/file", methods=["POST"])
def api_browse_file():
    path = browse_file()
    if path:
        return jsonify({"path": path})
    return jsonify({"path": None})


@main.route("/api/generate", methods=["POST"])
def api_generate():
    result = generate_documentation()
    return jsonify(result)
