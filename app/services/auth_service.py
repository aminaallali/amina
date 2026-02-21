from datetime import datetime
import uuid

from app import db
from app.models.audit_log import AuditLog
from app.models.challenge import AuthChallenge
from app.models.user import User
from app.services.crypto_service import CryptoService
from app.services.image_service import ImageService
from app.services.shuffle_engine import ShuffleEngine


class AuthService:
    def __init__(self, config):
        self.config = config
        self.shuffle = ShuffleEngine(config.WHEEL_SIZE)
        self.images = ImageService(config)
        self.crypto = CryptoService(config)

    def create_login_challenge(self, username: str, ip_address: str = None, user_agent: str = None) -> dict:
        user = User.query.filter_by(username=username, is_active=True).first()
        if not user:
            return self._generate_dummy_challenge()

        if user.is_locked():
            remaining = (user.locked_until - datetime.utcnow()).seconds
            raise PermissionError(f"الحساب مقفل. حاول بعد {remaining} ثانية")

        self._invalidate_old_challenges(user.id)

        challenge_data = self.shuffle.generate_challenge(
            base_seed=user.base_shuffle_seed,
            assigned_images=user.assigned_image_set,
            secret_offset_outer=user.secret_offset_outer,
            secret_offset_inner=user.secret_offset_inner,
        )

        canvas_data = self.images.generate_canvas_data(
            challenge_data["outer_wheel_order"],
            challenge_data["inner_wheel_order"],
            challenge_data["session_seed"],
        )

        challenge = AuthChallenge.create_for_user(
            user_id=user.id,
            shuffle_seed=challenge_data["session_seed"],
            outer_order=challenge_data["outer_wheel_order"],
            inner_order=challenge_data["inner_wheel_order"],
            expected_resp=challenge_data["expected_response_hash"],
            expiry_seconds=self.config.CHALLENGE_EXPIRY,
        )
        db.session.add(challenge)
        db.session.flush()

        db.session.add(
            AuditLog(
                user_id=user.id,
                event_type="login_attempt",
                challenge_id=challenge.id,
                ip_address=ip_address,
                user_agent=user_agent,
            )
        )
        db.session.commit()

        return {
            "challenge_id": challenge.id,
            "canvas_data": canvas_data,
            "wheel_size": self.config.WHEEL_SIZE,
            "expires_in": self.config.CHALLENGE_EXPIRY,
            "timestamp": datetime.utcnow().isoformat(),
        }

    def verify_login_response(self, challenge_id: str, user_response: dict, ip_address: str = None, user_agent: str = None) -> dict:
        challenge = AuthChallenge.query.get(challenge_id)
        if not challenge:
            return self._auth_failure("تحدي غير صالح")
        if not challenge.is_valid():
            return self._auth_failure("انتهت صلاحية التحدي", challenge=challenge)

        user = User.query.get(challenge.user_id)
        if not user or user.is_locked():
            return self._auth_failure("الحساب غير متاح", challenge=challenge)

        anti_auto_result = self._verify_anti_automation(user_response.get("interaction_data", {}), challenge)
        if not anti_auto_result["passed"]:
            return self._auth_failure(
                "نمط تفاعل مشبوه",
                challenge=challenge,
                user=user,
                metadata={"anti_automation": anti_auto_result},
            )

        verification = self.shuffle.verify_response(
            user_response={
                "inner_rotation": user_response["inner_rotation"],
                "alignment_check": user_response.get("alignment_check", 0),
            },
            expected_hash=challenge.expected_response,
            session_seed=challenge.session_shuffle_seed,
            tolerance=0,
        )

        challenge.status = "answered"
        challenge.answered_at = datetime.utcnow()
        challenge.was_successful = verification["is_valid"]
        challenge.movement_event_count = user_response.get("interaction_data", {}).get("movement_count", 0)
        challenge.interaction_duration_ms = user_response.get("interaction_data", {}).get("duration_ms")

        if verification["is_valid"]:
            return self._auth_success(user, challenge, ip_address)
        return self._auth_failure("محاذاة غير صحيحة", challenge=challenge, user=user, ip_address=ip_address)

    def _verify_anti_automation(self, interaction_data: dict, challenge: AuthChallenge) -> dict:
        issues = []
        duration_ms = interaction_data.get("duration_ms", 0)
        min_duration = self.config.MIN_INTERACTION_TIME * 1000
        if duration_ms < min_duration:
            issues.append("مدة تفاعل قصيرة جداً")

        movement_count = interaction_data.get("movement_count", 0)
        if movement_count < self.config.MIN_MOVEMENT_EVENTS:
            issues.append("حركات قليلة")

        if self.config.REQUIRE_DIRECTION_CHANGE and interaction_data.get("direction_changes", 0) < 1:
            issues.append("لم يتم تغيير اتجاه الدوران")

        return {
            "passed": len(issues) == 0,
            "issues": issues,
            "metrics": {
                "duration_ms": duration_ms,
                "movement_count": movement_count,
                "direction_changes": interaction_data.get("direction_changes", 0),
            },
        }

    def _auth_success(self, user: User, challenge: AuthChallenge, ip_address: str = None) -> dict:
        user.reset_failed_attempts()
        token = self.crypto.generate_jwt(user.id, user.username)

        db.session.add(
            AuditLog(
                user_id=user.id,
                event_type="login_success",
                challenge_id=challenge.id,
                ip_address=ip_address,
                event_metadata={"interaction_duration": challenge.interaction_duration_ms},
            )
        )
        db.session.commit()

        return {
            "success": True,
            "token": token,
            "user": {"id": user.id, "username": user.username},
            "message": "تم تسجيل الدخول بنجاح",
        }

    def _auth_failure(self, reason: str, challenge: AuthChallenge = None, user: User = None, ip_address: str = None, metadata: dict = None) -> dict:
        if user:
            user.increment_failed_attempts(
                max_attempts=self.config.MAX_LOGIN_ATTEMPTS,
                lockout_minutes=self.config.LOCKOUT_DURATION // 60,
            )

        if challenge:
            challenge.status = "answered"
            challenge.was_successful = False

        db.session.add(
            AuditLog(
                event_type="login_failure",
                user_id=user.id if user else None,
                challenge_id=challenge.id if challenge else None,
                ip_address=ip_address,
                event_metadata={"reason": reason, **(metadata or {})},
            )
        )
        db.session.commit()

        result = {"success": False, "message": "فشلت المصادقة"}
        if user and user.is_locked():
            result["locked"] = True
            result["locked_until"] = user.locked_until.isoformat()
        return result

    def _invalidate_old_challenges(self, user_id: str):
        AuthChallenge.query.filter_by(user_id=user_id, status="pending").update({"status": "invalidated"})

    def _generate_dummy_challenge(self) -> dict:
        return {
            "challenge_id": str(uuid.uuid4()),
            "canvas_data": {
                "composite_image": "",
                "tile_map": {},
                "canvas_dimensions": {"width": 0, "height": 0},
                "tile_size": {"width": 0, "height": 0},
                "outer_count": self.config.WHEEL_SIZE,
                "inner_count": self.config.WHEEL_SIZE,
            },
            "wheel_size": self.config.WHEEL_SIZE,
            "expires_in": self.config.CHALLENGE_EXPIRY,
            "timestamp": datetime.utcnow().isoformat(),
        }
