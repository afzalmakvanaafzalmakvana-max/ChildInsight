from datetime import datetime, timezone
from app import db


class Recommendation(db.Model):
    """Stores generated activity recommendations with human-readable educational reasoning."""
    __tablename__ = 'recommendations'

    TYPE_LEVEL_UP = 'level_up'
    TYPE_REINFORCE = 'reinforce'
    TYPE_PRACTICE = 'practice'
    TYPE_EXPLORE = 'explore'

    id = db.Column(db.Integer, primary_key=True)
    child_id = db.Column(db.Integer, db.ForeignKey('children.id', ondelete='CASCADE'), nullable=False, index=True)
    activity_id = db.Column(db.Integer, db.ForeignKey('activities.id', ondelete='CASCADE'), nullable=False, index=True)
    reason = db.Column(db.Text, nullable=False)
    recommendation_type = db.Column(db.String(50), nullable=False, default=TYPE_REINFORCE)
    priority = db.Column(db.Integer, default=1, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc), index=True)

    # Relationships
    child = db.relationship('Child', backref=db.backref('recommendations', lazy='dynamic', cascade='all, delete-orphan'))
    activity = db.relationship('Activity', backref=db.backref('recommendations', lazy='dynamic'))

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def to_dict(self):
        return {
            'id': self.id,
            'child_id': self.child_id,
            'activity_id': self.activity_id,
            'activity_title': self.activity.title if self.activity else None,
            'category_name': self.activity.category.name if self.activity and self.activity.category else None,
            'category_slug': self.activity.category.slug if self.activity and self.activity.category else None,
            'difficulty': self.activity.difficulty if self.activity else None,
            'reason': self.reason,
            'recommendation_type': self.recommendation_type,
            'priority': self.priority,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

    def __repr__(self) -> str:
        return f'<Recommendation id={self.id} child_id={self.child_id} activity_id={self.activity_id} type={self.recommendation_type} priority={self.priority}>'
