from datetime import datetime, timezone
from app import db


class Child(db.Model):
    """Child model representing a learner profile linked to a parent."""
    __tablename__ = 'children'

    id = db.Column(db.Integer, primary_key=True)
    parent_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    name = db.Column(db.String(100), nullable=False)
    age = db.Column(db.Integer, nullable=True)
    grade = db.Column(db.String(50), nullable=True)
    preferred_language = db.Column(db.String(50), nullable=True, default='English')
    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(
        db.DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def __repr__(self) -> str:
        return f'<Child id={self.id} name={self.name} parent_id={self.parent_id}>'
