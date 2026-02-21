from flask import Blueprint, jsonify, request

from app.config import Config
from app.middleware.rate_limiter import rate_limit
from app.services.registration_service import RegistrationService

registration_api = Blueprint("registration_api", __name__, url_prefix="/api/v1")
reg_service = RegistrationService(Config)


@registration_api.route("/register/init", methods=["POST"])
@rate_limit(requests=5, window=300)
def register_init():
    data = request.get_json() or {}
    if "username" not in data or "email" not in data:
        return jsonify({"error": "بيانات ناقصة"}), 400

    try:
        result = reg_service.initiate_registration(
            username=data["username"].strip(),
            email=data["email"].strip().lower(),
        )
        return jsonify(result), 200
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 409


@registration_api.route("/register/complete", methods=["POST"])
@rate_limit(requests=5, window=300)
def register_complete():
    data = request.get_json() or {}
    required = ["registration_token", "outer_rotation", "inner_rotation"]
    if not all(k in data for k in required):
        return jsonify({"error": "بيانات ناقصة"}), 400

    try:
        result = reg_service.complete_registration(
            registration_token=data["registration_token"],
            user_response={
                "outer_rotation": int(data["outer_rotation"]),
                "inner_rotation": int(data["inner_rotation"]),
            },
        )
        return jsonify(result), 201
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
