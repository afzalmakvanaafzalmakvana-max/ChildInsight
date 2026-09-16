from datetime import datetime, timezone
from app import db


class Notification(db.Model):
    """In-dashboard notifications for parents and educators."""
    __tablename__ = 'notifications'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    child_id = db.Column(db.Integer, db.ForeignKey('children.id', ondelete='CASCADE'), nullable=True, index=True)
    notification_type = db.Column(db.String(50), nullable=False, default='general', index=True)
    message = db.Column(db.Text, nullable=False)
    link = db.Column(db.String(255), nullable=True)
    is_read = db.Column(db.Boolean, default=False, nullable=False, index=True)
    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc), index=True)

    # Relationships
    user = db.relationship('User', backref=db.backref('notifications', lazy='dynamic', cascade='all, delete-orphan'))
    child = db.relationship('Child', backref=db.backref('notifications', lazy='dynamic', cascade='all, delete-orphan'))

    TYPE_ACTIVITY_COMPLETED = 'activity_completed'
    TYPE_RECOMMENDATION_GENERATED = 'recommendation_generated'
    TYPE_TEACHER_ASSIGNED = 'teacher_assigned'
    TYPE_GENERAL = 'general'

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def mark_as_read(self):
        """Marks the notification as read."""
        self.is_read = True

    def to_dict(self):
        """Serializes notification to a JSON-ready dictionary."""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'child_id': self.child_id,
            'child_name': self.child.name if self.child else None,
            'notification_type': self.notification_type,
            'message': self.message,
            'link': self.link,
            'is_read': self.is_read,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

    def __repr__(self):
        return f'<Notification id={self.id} user_id={self.user_id} type={self.notification_type} read={self.is_read}>'
