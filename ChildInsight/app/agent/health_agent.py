from datetime import datetime, timezone
from app import db
from app.models.session import ActivitySession
from app.models.activity import Activity
from app.models.child import Child
from app.models.recommendation import Recommendation
from app.models.health import HealthSnapshot
from app.agent import compliance_agent, content_integrity_agent


AGE_BANDS = [
    ('4-6', 4, 6, 'Early Childhood (Ages 4–6)'),
    ('6-9', 6, 9, 'Early Elementary (Ages 6–9)'),
    ('9-12', 9, 12, 'Upper Elementary (Ages 9–12)'),
    ('12-14', 12, 14, 'Early Secondary (Ages 12–14)')
]


def is_activity_valid(act: Activity) -> bool:
    """Checks if an activity satisfies catalog content validity criteria."""
    q_count = act.questions.count() if hasattr(act.questions, 'count') else len(act.questions)
    has_questions = q_count > 0
    valid_diff = act.difficulty in set(Activity.DIFFICULTIES)
    min_age = getattr(act, 'min_age', None)
    max_age = getattr(act, 'max_age', None)
    valid_age = (
        min_age is not None and max_age is not None and
        3 <= min_age <= max_age <= 18
    )
    return bool(has_questions and valid_diff and valid_age)


def activity_matches_age_band(act: Activity, min_a: int, max_a: int, band_label: str) -> bool:
    """Returns True if the activity is categorized for this developmental cohort."""
    if getattr(act, 'age_band', None) == band_label:
        return True
    if act.min_age == min_a and act.max_age == max_a:
        return True
    midpoint = (act.min_age + act.max_age) / 2.0
    return bool(min_a <= midpoint <= max_a)


def compute_age_band_health_metrics() -> list:
    """
    Computes per-age-band health telemetry for each of the 4 developmental cohorts:
    (4-6, 6-9, 9-12, 12-14).
    Components scoped to children/content in that age band:
    - Session completion rate (50% weight, scoped to children in that age band)
    - Content adequacy percentage (50% weight, scoped to activities for that age band)
    - Associated content gaps from ContentSuggestion
    """
    from app.models.content_suggestion import ContentSuggestion
    from app.agent.content_suggestion_agent import gap_affects_age_band

    pending_gaps = ContentSuggestion.query.filter_by(status=ContentSuggestion.STATUS_PENDING).all()

    breakdown = []
    for band_label, min_a, max_a, name in AGE_BANDS:
        # 1. Scope children to this age band
        band_children = Child.query.filter(Child.age >= min_a, Child.age <= max_a).all()
        total_children = len(band_children)
        child_ids = [c.id for c in band_children]

        # 2. Session completion rate for children in this age band
        if child_ids:
            band_sessions = ActivitySession.query.filter(ActivitySession.child_id.in_(child_ids)).all()
            total_sessions = len(band_sessions)
            completed_sessions = sum(1 for s in band_sessions if s.status == ActivitySession.STATUS_COMPLETED)
            completion_rate = (completed_sessions / total_sessions * 100.0) if total_sessions > 0 else 100.0
        else:
            total_sessions = 0
            completed_sessions = 0
            completion_rate = 100.0

        # 3. Content adequacy for activities supporting this age band
        band_activities = [act for act in Activity.query.all() if activity_matches_age_band(act, min_a, max_a, band_label)]
        total_activities = len(band_activities)
        valid_activities = sum(1 for act in band_activities if is_activity_valid(act))
        if total_activities > 0:
            content_adequacy = (valid_activities / total_activities) * 100.0
        else:
            content_adequacy = 0.0


        # 4. Consolidated per-age-band health score (50% session completion, 50% content adequacy)
        band_score = round((completion_rate * 0.50) + (content_adequacy * 0.50), 1)

        # 5. Content gaps affecting this age band
        band_gaps = [g for g in pending_gaps if gap_affects_age_band(g.age_band, band_label)]

        breakdown.append({
            'age_band': band_label,
            'name': name,
            'min_age': min_a,
            'max_age': max_a,
            'score': band_score,
            'completion_rate': round(completion_rate, 1),
            'content_adequacy': round(content_adequacy, 1),
            'total_children': total_children,
            'total_sessions': total_sessions,
            'completed_sessions': completed_sessions,
            'total_activities': total_activities,
            'valid_activities': valid_activities,
            'content_gaps': [
                {
                    'id': g.id,
                    'suggestion_type': g.suggestion_type,
                    'title': g.suggested_title or g.suggestion_type,
                    'target_difficulty': g.target_difficulty,
                    'category_name': g.category.name if g.category else None,
                    'reason': g.reason
                } for g in band_gaps
            ],
            'gaps_count': len(band_gaps)
        })

    return breakdown


def compute_health_metrics() -> dict:
    """
    Computes platform health indicators, a consolidated 0-100 overall health score,
    and granular per-age-band breakdowns (4-6, 6-9, 9-12, 12-14).
    Components:
    - Session completion rate (35% weight)
    - Valid activity content percentage (35% weight)
    - Learner recommendation coverage percentage (30% weight)
    - Deductions for compliance incidents and content integrity anomalies
    - Per-age-band breakdown (completion rate and content adequacy)
    """
    # 1. Session completion rate
    total_sessions = ActivitySession.query.count()
    if total_sessions > 0:
        completed_sessions = ActivitySession.query.filter_by(status=ActivitySession.STATUS_COMPLETED).count()
        completion_rate = (completed_sessions / total_sessions) * 100.0
    else:
        completed_sessions = 0
        completion_rate = 100.0

    # 2. Percentage of activities with valid content
    total_activities = Activity.query.count()
    if total_activities > 0:
        valid_activities = sum(1 for act in Activity.query.all() if is_activity_valid(act))
        valid_activities_pct = (valid_activities / total_activities) * 100.0
    else:
        valid_activities = 0
        valid_activities_pct = 100.0

    # 3. Percentage of children with at least one recommendation
    total_children = Child.query.count()
    if total_children > 0:
        children_with_recs = db.session.query(Recommendation.child_id).distinct().count()
        children_with_rec_pct = (children_with_recs / total_children) * 100.0
    else:
        children_with_recs = 0
        children_with_rec_pct = 100.0

    # 4. Compliance incidents & Content integrity issues
    recent_incidents = compliance_agent.get_recent_incident_count(since_hours=24)
    integrity_issues_count = content_integrity_agent.get_issue_count()

    # Penalties
    compliance_penalty = min(20.0, float(recent_incidents) * 2.0)
    integrity_penalty = min(20.0, float(integrity_issues_count) * 1.5)

    # Consolidated score
    base_score = (completion_rate * 0.35) + (valid_activities_pct * 0.35) + (children_with_rec_pct * 0.30)
    final_score = round(max(0.0, min(100.0, base_score - compliance_penalty - integrity_penalty)), 1)

    # 5. Granular per-age-band breakdown
    age_band_breakdown = compute_age_band_health_metrics()
    age_bands = {b['age_band']: b for b in age_band_breakdown}

    details = {
        'total_sessions': total_sessions,
        'completed_sessions': completed_sessions,
        'total_activities': total_activities,
        'valid_activities': valid_activities,
        'total_children': total_children,
        'children_with_recs': children_with_recs,
        'base_score': round(base_score, 1),
        'compliance_penalty': round(compliance_penalty, 1),
        'integrity_penalty': round(integrity_penalty, 1),
        'age_bands': age_bands
    }

    return {
        'score': final_score,
        'completion_rate': round(completion_rate, 1),
        'valid_activities_pct': round(valid_activities_pct, 1),
        'children_with_rec_pct': round(children_with_rec_pct, 1),
        'compliance_incidents_count': recent_incidents,
        'integrity_issues_count': integrity_issues_count,
        'age_band_breakdown': age_band_breakdown,
        'age_bands': age_bands,
        'details': details
    }



def record_snapshot() -> HealthSnapshot:
    """
    Computes the current platform health metrics and persists a HealthSnapshot row in the database.
    """
    metrics = compute_health_metrics()
    snapshot = HealthSnapshot(
        score=metrics['score'],
        completion_rate=metrics['completion_rate'],
        valid_activities_pct=metrics['valid_activities_pct'],
        children_with_rec_pct=metrics['children_with_rec_pct'],
        compliance_incidents_count=metrics['compliance_incidents_count'],
        integrity_issues_count=metrics['integrity_issues_count'],
        details_json=None,
        created_at=datetime.now(timezone.utc)
    )
    snapshot.details = metrics['details']
    db.session.add(snapshot)
    db.session.commit()
    return snapshot


def get_health_trend(limit: int = 15) -> list:
    """
    Retrieves the most recent health snapshots in chronological order for trend charting.
    """
    snapshots = HealthSnapshot.query.order_by(HealthSnapshot.created_at.desc()).limit(limit).all()
    snapshots.reverse()
    return snapshots


def get_latest_health() -> dict:
    """
    Fetches the latest snapshot or calculates metrics on the fly if none exist yet.
    """
    latest = HealthSnapshot.query.order_by(HealthSnapshot.created_at.desc()).first()
    if latest:
        return latest.to_dict()
    return compute_health_metrics()
