import threading
import webbrowser

from app import create_app

app = create_app()

if __name__ == "__main__":
    port = 5000
    url = f"http://localhost:{port}"

    # Only open the browser from the parent process.
    # When debug=True, Werkzeug spawns a reloader child that sets WERKZEUG_RUN_MAIN,
    # so without this guard the browser would open twice.
    import os
    if not os.environ.get("WERKZEUG_RUN_MAIN"):
        threading.Timer(1.0, lambda: webbrowser.open(url)).start()

    app.run(debug=True, port=port)
