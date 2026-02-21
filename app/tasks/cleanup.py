from datetime import datetime, timedelta

from app import db
from app.models.audit_log import AuditLog
from app.models.challenge import AuthChallenge
from app.models.user import User


def cleanup_expired_challenges():
    expired = AuthChallenge.query.filter(AuthChallenge.status == "pending", AuthChallenge.expires_at < datetime.utcnow()).all()
    for challenge in expired:
        challenge.status = "expired"
    db.session.commit()
    return len(expired)


def unlock_expired_lockouts():
    locked_users = User.query.filter(User.locked_until.isnot(None), User.locked_until < datetime.utcnow()).all()
    for user in locked_users:
        user.locked_until = None
        user.failed_attempts = 0
    db.session.commit()
    return len(locked_users)


def purge_old_audit_logs(days: int = 90):
    cutoff = datetime.utcnow() - timedelta(days=days)
    deleted = AuditLog.query.filter(AuditLog.created_at < cutoff).delete()
    db.session.commit()
    return deleted
