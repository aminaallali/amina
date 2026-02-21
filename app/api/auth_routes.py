from flask import Blueprint, jsonify, request

from app.config import Config
from app.middleware.rate_limiter import rate_limit
from app.services.auth_service import AuthService
from app.services.registration_service import RegistrationService

api = Blueprint("api", __name__, url_prefix="/api/v1")
auth_service = AuthService(Config)
reg_service = RegistrationService(Config)


@api.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"}), 200


@api.route("/register/init", methods=["POST"])
@rate_limit(requests=5, window=300)
def register_init():
    data = request.get_json() or {}
    if "username" not in data or "email" not in data:
        return jsonify({"error": "بيانات ناقصة"}), 400

    try:
        result = reg_service.initiate_registration(username=data["username"].strip(), email=data["email"].strip().lower())
        return jsonify(result), 200
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 409


@api.route("/register/complete", methods=["POST"])
@rate_limit(requests=5, window=300)
def register_complete():
    data = request.get_json() or {}
    required = ["registration_token", "outer_rotation", "inner_rotation"]
    if not all(k in data for k in required):
        return jsonify({"error": "بيانات ناقصة"}), 400

    try:
        result = reg_service.complete_registration(
            registration_token=data["registration_token"],
            user_response={"outer_rotation": int(data["outer_rotation"]), "inner_rotation": int(data["inner_rotation"])},
        )
        return jsonify(result), 201
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400


@api.route("/auth/challenge", methods=["POST"])
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


@api.route("/auth/verify", methods=["POST"])
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

    status_code = 200 if result["success"] else 401
    return jsonify(result), status_code
