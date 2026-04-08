import os

from flask import Flask
from dotenv import load_dotenv

load_dotenv()


def create_app(base_dir: str | None = None):
    """
    Create and configure the Flask app.

    Parameters
    ----------
    base_dir : str | None
        When running as a PyInstaller bundle, pass sys._MEIPASS so that
        Flask can locate templates/ and static/ from the extraction root.
        When None (normal Python execution), relative paths are used as usual.
    """
    if base_dir:
        app = Flask(
            __name__,
            template_folder=os.path.join(base_dir, "templates"),
            static_folder=os.path.join(base_dir, "static"),
        )
    else:
        app = Flask(__name__, template_folder="../templates", static_folder="../static")

    from .routes import main
    app.register_blueprint(main)

    return app
