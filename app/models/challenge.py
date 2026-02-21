from datetime import datetime, timedelta
import uuid

from app import db


class AuthChallenge(db.Model):
    __tablename__ = "auth_challenges"

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = db.Column(db.String(36), db.ForeignKey("users.id"), nullable=False, index=True)

    session_shuffle_seed = db.Column(db.String(64), nullable=False)
    outer_wheel_order = db.Column(db.JSON, nullable=False)
    inner_wheel_order = db.Column(db.JSON, nullable=False)
    expected_response = db.Column(db.String(128), nullable=False)

    status = db.Column(db.String(20), default="pending")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=False)

    answered_at = db.Column(db.DateTime, nullable=True)
    was_successful = db.Column(db.Boolean, nullable=True)

    movement_event_count = db.Column(db.Integer, default=0)
    direction_changed = db.Column(db.Boolean, default=False)
    interaction_duration_ms = db.Column(db.Integer, nullable=True)

    def is_expired(self):
        return datetime.utcnow() > self.expires_at

    def is_valid(self):
        return self.status == "pending" and not self.is_expired()

    @staticmethod
    def create_for_user(user_id, shuffle_seed, outer_order, inner_order, expected_resp, expiry_seconds=120):
        return AuthChallenge(
            user_id=user_id,
            session_shuffle_seed=shuffle_seed,
            outer_wheel_order=outer_order,
            inner_wheel_order=inner_order,
            expected_response=expected_resp,
            expires_at=datetime.utcnow() + timedelta(seconds=expiry_seconds),
        )
