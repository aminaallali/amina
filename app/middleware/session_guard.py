import functools

from flask import g, jsonify, request

from app.config import Config
from app.services.crypto_service import CryptoService

crypto = CryptoService(Config)


def require_auth(f):
    @functools.wraps(f)
    def wrapper(*args, **kwargs):
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return jsonify({"error": "مصادقة مطلوبة"}), 401

        token = auth_header[7:]
        try:
            payload = crypto.verify_jwt(token)
            g.current_user_id = payload["sub"]
            g.current_username = payload["username"]
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 401

        return f(*args, **kwargs)

    return wrapper
