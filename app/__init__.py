"""Application package bootstrap for JIBAS backend.

The module intentionally degrades gracefully when optional runtime dependencies
(Flask/Flask-SQLAlchemy/Flask-CORS) are unavailable so that pure-Python units
(e.g. shuffle math) can still be imported in restricted CI environments.
"""

try:
    from flask import Flask
    from flask_cors import CORS
    from flask_sqlalchemy import SQLAlchemy
except ModuleNotFoundError:  # pragma: no cover - fallback for constrained envs
    Flask = None
    CORS = None

    class SQLAlchemy:  # minimal shim for import-time compatibility
        def __init__(self):
            self.Model = object

        def init_app(self, app):
            return None

        def create_all(self):
            return None


db = SQLAlchemy()


def create_app(config_class=None):
    if Flask is None:
        raise RuntimeError(
            "Flask dependencies are not installed. Install requirements.txt "
            "to create the web application."
        )

    app = Flask(__name__)

    if config_class is None:
        from app.config import Config

        config_class = Config

    app.config.from_object(config_class)

    db.init_app(app)
    if CORS is not None:
        CORS(app, resources={r"/api/*": {"origins": app.config.get("CORS_ORIGINS", "*")}})

    from app.api.auth_routes import api

    app.register_blueprint(api)

    with app.app_context():
        db.create_all()

    return app
