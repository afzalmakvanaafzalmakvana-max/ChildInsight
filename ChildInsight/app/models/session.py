import json
from datetime import datetime, timezone
from sqlalchemy.orm import validates
from app import db


class ActivitySession(db.Model):
    """Represents a discrete session of a child playing an activity."""
    __tablename__ = 'activity_sessions'

    STATUS_IN_PROGRESS = 'in_progress'
    STATUS_COMPLETED = 'completed'
    STATUS_ABANDONED = 'abandoned'
    VALID_STATUSES = (STATUS_IN_PROGRESS, STATUS_COMPLETED, STATUS_ABANDONED)

    id = db.Column(db.Integer, primary_key=True)
    child_id = db.Column(db.Integer, db.ForeignKey('children.id', ondelete='CASCADE'), nullable=False, index=True)
    activity_id = db.Column(db.Integer, db.ForeignKey('activities.id', ondelete='CASCADE'), nullable=False, index=True)
    start_time = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    end_time = db.Column(db.DateTime, nullable=True)
    duration_seconds = db.Column(db.Integer, default=0, nullable=False)
    attempts = db.Column(db.Integer, default=0, nullable=False)
    correct_answers = db.Column(db.Integer, default=0, nullable=False)
    accuracy = db.Column(db.Float, default=0.0, nullable=False)
    status = db.Column(db.String(20), default=STATUS_IN_PROGRESS, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(
        db.DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )

    __table_args__ = (
        db.CheckConstraint('accuracy >= 0.0 AND accuracy <= 100.0', name='ck_session_accuracy_range'),
        db.CheckConstraint('attempts >= correct_answers', name='ck_session_attempts_gte_correct'),
        db.CheckConstraint('duration_seconds >= 0', name='ck_session_duration_non_negative'),
        db.CheckConstraint("status IN ('in_progress', 'completed', 'abandoned')", name='ck_session_status_valid'),
    )

    # Relationships
    child = db.relationship('Child', backref=db.backref('activity_sessions', lazy='dynamic', cascade='all, delete-orphan'))
    activity = db.relationship('Activity', backref=db.backref('sessions', lazy='dynamic'))
    events = db.relationship('InteractionEvent', backref='session', lazy='dynamic', cascade='all, delete-orphan')

    @validates('accuracy')
    def validate_accuracy(self, key, value):
        if value is not None and not (0.0 <= float(value) <= 100.0):
            raise ValueError(f"Accuracy must be between 0.0 and 100.0, got {value}")
        return float(value) if value is not None else 0.0

    @validates('attempts')
    def validate_attempts(self, key, value):
        if value is not None and value < 0:
            raise ValueError("Attempts cannot be negative")
        if getattr(self, 'correct_answers', None) is not None and value < self.correct_answers:
            raise ValueError(f"Attempts ({value}) cannot be less than correct_answers ({self.correct_answers})")
        return value

    @validates('correct_answers')
    def validate_correct_answers(self, key, value):
        if value is not None and value < 0:
            raise ValueError("Correct answers cannot be negative")
        if getattr(self, 'attempts', None) is not None and value > self.attempts:
            raise ValueError(f"Correct answers ({value}) cannot exceed attempts ({self.attempts})")
        return value

    @validates('duration_seconds')
    def validate_duration(self, key, value):
        if value is not None and value < 0:
            raise ValueError("Duration seconds cannot be negative")
        return value

    @validates('status')
    def validate_status(self, key, value):
        if value not in self.VALID_STATUSES:
            raise ValueError(f"Status must be one of {self.VALID_STATUSES}, got {value}")
        return value

    def __init__(self, **kwargs):
        kwargs.setdefault('status', self.STATUS_IN_PROGRESS)
        kwargs.setdefault('attempts', 0)
        kwargs.setdefault('correct_answers', 0)
        kwargs.setdefault('accuracy', 0.0)
        kwargs.setdefault('duration_seconds', 0)
        super().__init__(**kwargs)

    def recalculate_accuracy(self):
        """Recalculate accuracy percentage from attempts and correct answers."""
        attempts = self.attempts or 0
        correct = self.correct_answers or 0
        if attempts > 0:
            self.accuracy = round((correct / attempts) * 100.0, 2)
        else:
            self.accuracy = 0.0
        return self.accuracy

    def to_dict(self):
        return {
            'id': self.id,
            'child_id': self.child_id,
            'activity_id': self.activity_id,
            'activity_title': self.activity.title if self.activity else None,
            'category_name': self.activity.category.name if self.activity and self.activity.category else None,
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'duration_seconds': self.duration_seconds,
            'attempts': self.attempts,
            'correct_answers': self.correct_answers,
            'accuracy': self.accuracy,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

    def __repr__(self) -> str:
        return f'<ActivitySession id={self.id} child_id={self.child_id} activity_id={self.activity_id} status={self.status}>'


class InteractionEvent(db.Model):
    """Fine-grained interaction log capturing a child's interaction event during an activity."""
    __tablename__ = 'interaction_events'

    EVENT_STARTED = 'started'
    EVENT_QUESTION_VIEWED = 'question_viewed'
    EVENT_ANSWER_SELECTED = 'answer_selected'
    EVENT_CORRECT = 'correct'
    EVENT_INCORRECT = 'incorrect'
    EVENT_HINT_USED = 'hint_used'
    EVENT_SKIPPED = 'skipped'
    EVENT_COMPLETED = 'completed'
    EVENT_ABANDONED = 'abandoned'

    ALLOWED_EVENT_TYPES = (
        EVENT_STARTED,
        EVENT_QUESTION_VIEWED,
        EVENT_ANSWER_SELECTED,
        EVENT_CORRECT,
        EVENT_INCORRECT,
        EVENT_HINT_USED,
        EVENT_SKIPPED,
        EVENT_COMPLETED,
        EVENT_ABANDONED
    )

    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey('activity_sessions.id', ondelete='CASCADE'), nullable=False, index=True)
    child_id = db.Column(db.Integer, db.ForeignKey('children.id', ondelete='CASCADE'), nullable=False, index=True)
    question_id = db.Column(db.Integer, db.ForeignKey('activity_questions.id', ondelete='SET NULL'), nullable=True, index=True)
    event_type = db.Column(db.String(50), nullable=False, index=True)
    payload = db.Column(db.Text, nullable=True)
    timestamp = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc), index=True)

    # Relationships
    child = db.relationship('Child', backref=db.backref('interaction_events', lazy='dynamic', cascade='all, delete-orphan'))
    question = db.relationship('ActivityQuestion', backref=db.backref('interaction_events', lazy='dynamic'))

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    @validates('event_type')
    def validate_event_type(self, key, value):
        if value not in self.ALLOWED_EVENT_TYPES:
            raise ValueError(f"Invalid event_type: {value}. Must be one of {self.ALLOWED_EVENT_TYPES}")
        return value

    @property
    def payload_data(self):
        if not self.payload:
            return {}
        try:
            return json.loads(self.payload)
        except (ValueError, TypeError):
            return {}

    @payload_data.setter
    def payload_data(self, val):
        if val is None:
            self.payload = None
        else:
            self.payload = json.dumps(val)

    def to_dict(self):
        return {
            'id': self.id,
            'session_id': self.session_id,
            'child_id': self.child_id,
            'question_id': self.question_id,
            'event_type': self.event_type,
            'payload': self.payload_data,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None
        }

    def __repr__(self) -> str:
        return f'<InteractionEvent id={self.id} session_id={self.session_id} event_type={self.event_type}>'
