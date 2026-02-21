from datetime import datetime, timedelta
import uuid

from app import db


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False)

    base_shuffle_seed = db.Column(db.String(64), nullable=False)
    secret_offset_outer = db.Column(db.Integer, nullable=False)
    secret_offset_inner = db.Column(db.Integer, nullable=False)
    composite_secret_hash = db.Column(db.String(128), nullable=False)

    assigned_image_set = db.Column(db.JSON, nullable=False)

    is_active = db.Column(db.Boolean, default=True)
    failed_attempts = db.Column(db.Integer, default=0)
    locked_until = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime, nullable=True)

    challenges = db.relationship("AuthChallenge", backref="user", lazy="dynamic")
    audit_logs = db.relationship("AuditLog", backref="user", lazy="dynamic")

    def is_locked(self):
        return bool(self.locked_until and self.locked_until > datetime.utcnow())

    def increment_failed_attempts(self, max_attempts=5, lockout_minutes=15):
        self.failed_attempts += 1
        if self.failed_attempts >= max_attempts:
            self.locked_until = datetime.utcnow() + timedelta(minutes=lockout_minutes)

    def reset_failed_attempts(self):
        self.failed_attempts = 0
        self.locked_until = None
        self.last_login = datetime.utcnow()
