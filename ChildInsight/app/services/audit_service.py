from datetime import datetime, timezone
from app import db
from app.models.audit_log import AuditLog


def log_action(user_id, action, target_type=None, target_id=None):
    """Records an administrative or teacher operational action in the audit log.

    Args:
        user_id: ID of the user performing the action (or None for system).
        action: Descriptive action string (e.g. 'toggle_user_status', 'change_user_role').
        target_type: Entity type acted upon (e.g. 'user', 'child', 'teacher_assignment').
        target_id: ID of the target entity.

    Returns:
        The created AuditLog instance.
    """
    entry = AuditLog(
        user_id=user_id,
        action=action,
        target_type=target_type,
        target_id=target_id,
        timestamp=datetime.now(timezone.utc)
    )
    db.session.add(entry)
    db.session.commit()
    return entry


def get_recent_audit_logs(limit=50, action=None, user_id=None):
    """Retrieves recent audit log entries ordered from newest to oldest."""
    query = AuditLog.query
    if action:
        query = query.filter_by(action=action)
    if user_id:
        query = query.filter_by(user_id=user_id)
    return query.order_by(AuditLog.timestamp.desc()).limit(limit).all()
