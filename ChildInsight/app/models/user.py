from datetime import datetime, timezone
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app import db


class User(UserMixin, db.Model):
    """User model representing parents, teachers, and administrators."""
    __tablename__ = 'users'

    ROLES = ('parent', 'teacher', 'admin')
    ASSIGNABLE_ROLES = ('parent', 'teacher', 'admin')

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, index=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='parent')
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    theme_preference = db.Column(db.String(20), nullable=False, default='light', server_default='light')
    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(
        db.DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )

    children = db.relationship(
        'Child',
        backref='parent',
        lazy='dynamic',
        cascade='all, delete-orphan'
    )

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    @property
    def is_parent(self) -> bool:
        return self.role == 'parent'

    @property
    def is_teacher(self) -> bool:
        return self.role == 'teacher'

    @property
    def is_admin(self) -> bool:
        return self.role == 'admin'

    @property
    def is_child(self) -> bool:
        return self.role == 'child'

    def __repr__(self) -> str:
        return f'<User id={self.id} email={self.email} role={self.role}>'
