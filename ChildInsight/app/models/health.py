from datetime import datetime, timezone
import json
from app import db


class HealthSnapshot(db.Model):
    """Stores platform health evaluation snapshots over time."""
    __tablename__ = 'health_snapshots'

    id = db.Column(db.Integer, primary_key=True)
    score = db.Column(db.Float, nullable=False)
    completion_rate = db.Column(db.Float, nullable=False, default=0.0)
    valid_activities_pct = db.Column(db.Float, nullable=False, default=0.0)
    children_with_rec_pct = db.Column(db.Float, nullable=False, default=0.0)
    compliance_incidents_count = db.Column(db.Integer, nullable=False, default=0)
    integrity_issues_count = db.Column(db.Integer, nullable=False, default=0)
    details_json = db.Column(db.Text, nullable=True)
    created_at = db.Column(
        db.DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        index=True
    )

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    @property
    def details(self):
        if not self.details_json:
            return {}
        try:
            return json.loads(self.details_json)
        except (ValueError, TypeError):
            return {}

    @details.setter
    def details(self, value):
        self.details_json = json.dumps(value) if value is not None else None

    def to_dict(self):
        return {
            'id': self.id,
            'score': round(self.score, 1),
            'completion_rate': round(self.completion_rate, 1),
            'valid_activities_pct': round(self.valid_activities_pct, 1),
            'children_with_rec_pct': round(self.children_with_rec_pct, 1),
            'compliance_incidents_count': self.compliance_incidents_count,
            'integrity_issues_count': self.integrity_issues_count,
            'details': self.details,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

    def __repr__(self):
        return f"<HealthSnapshot id={self.id} score={self.score} created_at={self.created_at}>"
