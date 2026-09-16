from datetime import datetime, timezone
from app import db


class AuditLog(db.Model):
    """Tracks administrative and teacher operational actions for transparency and accountability."""
    __tablename__ = 'audit_logs'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True, index=True)
    action = db.Column(db.String(100), nullable=False, index=True)
    target_type = db.Column(db.String(50), nullable=True)
    target_id = db.Column(db.Integer, nullable=True)
    timestamp = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc), index=True)

    # Relationships
    user = db.relationship('User', backref=db.backref('audit_logs', lazy='dynamic'))

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'user_name': self.user.name if self.user else 'System',
            'action': self.action,
            'target_type': self.target_type,
            'target_id': self.target_id,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None
        }

    def __repr__(self) -> str:
        return f'<AuditLog id={self.id} user_id={self.user_id} action={self.action} target={self.target_type}:{self.target_id}>'
