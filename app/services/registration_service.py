from app import db
from app.models.audit_log import AuditLog
from app.models.user import User
from app.services.crypto_service import CryptoService
from app.services.image_service import ImageService
from app.services.shuffle_engine import ShuffleEngine


class RegistrationService:
    def __init__(self, config):
        self.config = config
        self.shuffle_engine = ShuffleEngine(config.WHEEL_SIZE)
        self.image_service = ImageService(config)
        self.crypto = CryptoService(config)

    def initiate_registration(self, username: str, email: str) -> dict:
        if User.query.filter_by(username=username).first():
            raise ValueError("اسم المستخدم موجود مسبقاً")
        if User.query.filter_by(email=email).first():
            raise ValueError("البريد الإلكتروني مسجل مسبقاً")

        base_seed = self.shuffle_engine.generate_seed()
        assigned_images = self.image_service.assign_images_to_user(self.config.WHEEL_SIZE)

        initial_outer = self.shuffle_engine.derive_permutation(f"{base_seed}:initial:outer", len(assigned_images["outer"]), self.config.WHEEL_SIZE)
        initial_inner = self.shuffle_engine.derive_permutation(f"{base_seed}:initial:inner", len(assigned_images["inner"]), self.config.WHEEL_SIZE)

        outer_display = [assigned_images["outer"][i] for i in initial_outer]
        inner_display = [assigned_images["inner"][i] for i in initial_inner]

        canvas_data = self.image_service.generate_canvas_data(outer_display, inner_display, base_seed)

        registration_token = self.crypto.generate_token()
        self.crypto.store_temp_data(
            registration_token,
            {
                "username": username,
                "email": email,
                "base_seed": base_seed,
                "assigned_images": assigned_images,
                "outer_display": outer_display,
                "inner_display": inner_display,
                "step": "awaiting_selection",
            },
            ttl=300,
        )

        return {
            "registration_token": registration_token,
            "canvas_data": canvas_data,
            "wheel_size": self.config.WHEEL_SIZE,
            "instructions": {
                "step": 1,
                "message": "اختر صورة من العجلة الخارجية وصورة من الداخلية ثم أدر العجلات لمحاذاتهما",
            },
        }

    def complete_registration(self, registration_token: str, user_response: dict) -> dict:
        reg_data = self.crypto.retrieve_temp_data(registration_token)
        if not reg_data:
            raise ValueError("انتهت صلاحية جلسة التسجيل")

        outer_offset = user_response["outer_rotation"] % self.config.WHEEL_SIZE
        inner_offset = user_response["inner_rotation"] % self.config.WHEEL_SIZE

        composite_hash = self.crypto.create_composite_hash(reg_data["base_seed"], outer_offset, inner_offset)

        user = User(
            username=reg_data["username"],
            email=reg_data["email"],
            base_shuffle_seed=reg_data["base_seed"],
            secret_offset_outer=outer_offset,
            secret_offset_inner=inner_offset,
            composite_secret_hash=composite_hash,
            assigned_image_set=reg_data["assigned_images"],
        )

        db.session.add(user)
        db.session.flush()

        db.session.add(AuditLog(user_id=user.id, event_type="registration", event_metadata={"method": "JIBAS"}))
        db.session.commit()

        self.crypto.delete_temp_data(registration_token)

        return {"success": True, "user_id": user.id, "message": "تم التسجيل بنجاح. تذكر الصورتين اللتين اخترتهما!"}
