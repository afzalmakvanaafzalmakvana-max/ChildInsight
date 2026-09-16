import hashlib
import secrets
from datetime import datetime, timezone, timedelta
from app import db


class PasswordResetToken(db.Model):
    """Stores secure, time-limited tokens for password reset requests."""
    __tablename__ = 'password_reset_tokens'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    token_hash = db.Column(db.String(64), nullable=False, index=True)
    expires_at = db.Column(db.DateTime, nullable=False, index=True)
    used_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

    # Relationships
    user = db.relationship('User', backref=db.backref('reset_tokens', lazy='dynamic', cascade='all, delete-orphan'))

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    @property
    def is_used(self) -> bool:
        """Returns True if this token has already been consumed."""
        return self.used_at is not None

    @property
    def is_expired(self) -> bool:
        """Returns True if this token has passed its expiration timestamp."""
        now = datetime.now(timezone.utc)
        record_expires = self.expires_at
        if record_expires.tzinfo is None:
            record_expires = record_expires.replace(tzinfo=timezone.utc)
        return record_expires < now

    @staticmethod
    def hash_token(raw_token: str) -> str:
        """Computes SHA-256 hash of a raw token string."""
        return hashlib.sha256(raw_token.encode('utf-8')).hexdigest()

    @classmethod
    def create_token(cls, user, expires_in_minutes: int = 30) -> tuple['PasswordResetToken', str]:
        """
        Generates a high-entropy random URL-safe token, hashes it for database storage,
        and returns both the saved token record and the raw token string for the URL.
        """
        raw_token = secrets.token_urlsafe(32)
        hashed = cls.hash_token(raw_token)
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(minutes=expires_in_minutes)

        token_record = cls(
            user_id=user.id,
            token_hash=hashed,
            expires_at=expires_at,
            created_at=now
        )
        db.session.add(token_record)
        return token_record, raw_token

    @classmethod
    def verify_token(cls, raw_token: str) -> tuple[bool, str, 'PasswordResetToken | None']:
        """
        Verifies a raw token against the database.
        Returns (is_valid, reason, token_record).
        """
        if not raw_token or len(raw_token) < 16:
            return False, "Invalid token format.", None

        hashed = cls.hash_token(raw_token)
        record = cls.query.filter_by(token_hash=hashed).first()

        if not record:
            return False, "Reset link not found.", None

        if record.used_at is not None:
            return False, "This reset link has already been used.", record

        now = datetime.now(timezone.utc)
        record_expires = record.expires_at
        if record_expires.tzinfo is None:
            record_expires = record_expires.replace(tzinfo=timezone.utc)

        if record_expires < now:
            return False, "This reset link has expired.", record

        return True, "Token is valid.", record

    def mark_used(self):
        """Marks the token as used, invalidating it for subsequent attempts."""
        self.used_at = datetime.now(timezone.utc)

    def __repr__(self) -> str:
        return f'<PasswordResetToken id={self.id} user_id={self.user_id} used={self.used_at is not None}>'
