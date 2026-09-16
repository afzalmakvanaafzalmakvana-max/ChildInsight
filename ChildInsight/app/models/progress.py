from datetime import datetime, timezone
from sqlalchemy.orm import validates
from app import db


class ProgressRecord(db.Model):
    """Stores periodic or on-demand aggregated progress metrics per child and category."""
    __tablename__ = 'progress_records'

    id = db.Column(db.Integer, primary_key=True)
    child_id = db.Column(db.Integer, db.ForeignKey('children.id', ondelete='CASCADE'), nullable=False, index=True)
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id', ondelete='CASCADE'), nullable=False, index=True)
    accuracy = db.Column(db.Float, nullable=False, default=0.0)
    engagement_score = db.Column(db.Float, nullable=False, default=0.0)
    performance_score = db.Column(db.Float, nullable=False, default=0.0)
    recorded_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc), index=True)

    __table_args__ = (
        db.CheckConstraint('accuracy >= 0.0 AND accuracy <= 100.0', name='ck_progress_accuracy_range'),
        db.CheckConstraint('engagement_score >= 0.0 AND engagement_score <= 100.0', name='ck_progress_engagement_range'),
        db.CheckConstraint('performance_score >= 0.0 AND performance_score <= 100.0', name='ck_progress_performance_range'),
    )

    # Relationships
    child = db.relationship('Child', backref=db.backref('progress_records', lazy='dynamic', cascade='all, delete-orphan'))
    category = db.relationship('Category', backref=db.backref('progress_records', lazy='dynamic'))

    def __init__(self, **kwargs):
        kwargs.setdefault('accuracy', 0.0)
        kwargs.setdefault('engagement_score', 0.0)
        kwargs.setdefault('performance_score', 0.0)
        super().__init__(**kwargs)

    @validates('accuracy')
    def validate_accuracy(self, key, value):
        if value is not None and not (0.0 <= float(value) <= 100.0):
            raise ValueError(f"Accuracy must be between 0.0 and 100.0, got {value}")
        return round(float(value), 2) if value is not None else 0.0

    @validates('engagement_score')
    def validate_engagement(self, key, value):
        if value is not None and not (0.0 <= float(value) <= 100.0):
            raise ValueError(f"Engagement score must be between 0.0 and 100.0, got {value}")
        return round(float(value), 2) if value is not None else 0.0

    @validates('performance_score')
    def validate_performance(self, key, value):
        if value is not None and not (0.0 <= float(value) <= 100.0):
            raise ValueError(f"Performance score must be between 0.0 and 100.0, got {value}")
        return round(float(value), 2) if value is not None else 0.0

    def to_dict(self):
        return {
            'id': self.id,
            'child_id': self.child_id,
            'category_id': self.category_id,
            'category_name': self.category.name if self.category else None,
            'category_slug': self.category.slug if self.category else None,
            'accuracy': self.accuracy,
            'engagement_score': self.engagement_score,
            'performance_score': self.performance_score,
            'recorded_at': self.recorded_at.isoformat() if self.recorded_at else None
        }

    def __repr__(self) -> str:
        return f'<ProgressRecord id={self.id} child_id={self.child_id} category_id={self.category_id} perf={self.performance_score}>'
