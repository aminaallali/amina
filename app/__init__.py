from flask import Flask
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy


db = SQLAlchemy()


def create_app(config_class=None):
    app = Flask(__name__)

    if config_class is None:
        from app.config import Config

        config_class = Config

    app.config.from_object(config_class)

    db.init_app(app)
    CORS(app, resources={r"/api/*": {"origins": app.config.get("CORS_ORIGINS", "*")}})

    from app.api.auth_routes import auth_api
    from app.api.image_routes import image_api
    from app.api.registration_routes import registration_api

    app.register_blueprint(auth_api)
    app.register_blueprint(registration_api)
    app.register_blueprint(image_api)

    with app.app_context():
        db.create_all()

    return app
