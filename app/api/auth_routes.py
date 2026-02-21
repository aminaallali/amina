from flask import Blueprint, jsonify, request

from app.config import Config
from app.middleware.rate_limiter import rate_limit
from app.services.auth_service import AuthService

auth_api = Blueprint("auth_api", __name__, url_prefix="/api/v1")
# Backward compatibility with older app factory imports (`from ... import api`)
api = auth_api

auth_service = AuthService(Config)


@auth_api.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"}), 200


@auth_api.route("/auth/challenge", methods=["POST"])
@rate_limit(requests=10, window=60)
def request_challenge():
    data = request.get_json() or {}
    if "username" not in data:
        return jsonify({"error": "اسم المستخدم مطلوب"}), 400

    try:
        result = auth_service.create_login_challenge(
            username=data["username"].strip(),
            ip_address=request.remote_addr,
            user_agent=request.headers.get("User-Agent", ""),
        )
        return jsonify(result), 200
    except PermissionError as exc:
        return jsonify({"error": str(exc)}), 429


@auth_api.route("/auth/verify", methods=["POST"])
@rate_limit(requests=10, window=60)
def verify_response():
    data = request.get_json() or {}
    required = ["challenge_id", "inner_rotation"]
    if not all(k in data for k in required):
        return jsonify({"error": "بيانات ناقصة"}), 400

    result = auth_service.verify_login_response(
        challenge_id=data["challenge_id"],
        user_response={
            "inner_rotation": int(data["inner_rotation"]),
            "alignment_check": data.get("alignment_check", 0),
            "interaction_data": data.get("interaction_data", {}),
        },
        ip_address=request.remote_addr,
        user_agent=request.headers.get("User-Agent", ""),
    )

    return jsonify(result), (200 if result["success"] else 401)
