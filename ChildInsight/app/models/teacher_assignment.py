from datetime import datetime, timezone
from app import db


class TeacherAssignment(db.Model):
    """Associates teachers with assigned students for progress observation."""
    __tablename__ = 'teacher_assignments'

    id = db.Column(db.Integer, primary_key=True)
    teacher_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    child_id = db.Column(db.Integer, db.ForeignKey('children.id', ondelete='CASCADE'), nullable=False, index=True)
    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        db.UniqueConstraint('teacher_id', 'child_id', name='uq_teacher_child_assignment'),
    )

    teacher = db.relationship('User', backref=db.backref('assigned_students', lazy='dynamic', cascade='all, delete-orphan'))
    child = db.relationship('Child', backref=db.backref('assigned_teachers', lazy='dynamic', cascade='all, delete-orphan'))

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def __repr__(self) -> str:
        return f'<TeacherAssignment teacher_id={self.teacher_id} child_id={self.child_id}>'
