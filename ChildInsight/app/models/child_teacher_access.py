from datetime import datetime, timezone
from app import db


class ChildTeacherAccess(db.Model):
    """Parent-initiated teacher access grant allowing educators to view a child's learning profile.

    Coexists with admin-managed teacher_assignments.
    """
    __tablename__ = 'child_teacher_access'

    STATUS_PENDING_VERIFICATION = 'pending_verification'
    STATUS_PENDING_APPROVAL = 'pending_teacher_approval'
    STATUS_ACTIVE = 'active'
    STATUS_REVOKED = 'revoked'
    STATUS_DECLINED = 'declined'

    VALID_STATUSES = (
        STATUS_PENDING_VERIFICATION,
        STATUS_PENDING_APPROVAL,
        STATUS_ACTIVE,
        STATUS_REVOKED,
        STATUS_DECLINED
    )

    id = db.Column(db.Integer, primary_key=True)
    child_id = db.Column(db.Integer, db.ForeignKey('children.id', ondelete='CASCADE'), nullable=False, index=True)
    teacher_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True, index=True)
    invited_email = db.Column(db.String(120), nullable=False, index=True)
    status = db.Column(db.String(40), nullable=False, default=STATUS_PENDING_APPROVAL, index=True)
    requested_by_parent_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    responded_at = db.Column(db.DateTime, nullable=True)
    revoked_at = db.Column(db.DateTime, nullable=True)

    # Relationships
    child = db.relationship('Child', backref=db.backref('teacher_access_grants', lazy='dynamic', cascade='all, delete-orphan'))
    teacher = db.relationship('User', foreign_keys=[teacher_id], backref=db.backref('granted_child_accesses', lazy='dynamic'))
    parent = db.relationship('User', foreign_keys=[requested_by_parent_id], backref=db.backref('initiated_teacher_accesses', lazy='dynamic'))

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    @property
    def is_active(self) -> bool:
        return self.status == self.STATUS_ACTIVE

    @property
    def is_pending(self) -> bool:
        return self.status in (self.STATUS_PENDING_APPROVAL, self.STATUS_PENDING_VERIFICATION)

    @property
    def can_revoke(self) -> bool:
        return self.status in (self.STATUS_ACTIVE, self.STATUS_PENDING_APPROVAL, self.STATUS_PENDING_VERIFICATION)

    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'child_id': self.child_id,
            'child_name': self.child.name if self.child else None,
            'teacher_id': self.teacher_id,
            'teacher_name': self.teacher.name if self.teacher else None,
            'invited_email': self.invited_email,
            'status': self.status,
            'requested_by_parent_id': self.requested_by_parent_id,
            'parent_name': self.parent.name if self.parent else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'responded_at': self.responded_at.isoformat() if self.responded_at else None,
            'revoked_at': self.revoked_at.isoformat() if self.revoked_at else None
        }

    def __repr__(self) -> str:
        return f'<ChildTeacherAccess id={self.id} child_id={self.child_id} teacher_id={self.teacher_id} status={self.status}>'
