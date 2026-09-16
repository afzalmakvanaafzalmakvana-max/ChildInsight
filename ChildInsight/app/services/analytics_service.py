from datetime import datetime, timezone
import numpy as np
import pandas as pd
from app import db
from app.models.session import ActivitySession
from app.models.activity import Activity, Category
from app.models.child import Child
from app.models.progress import ProgressRecord
from app.services import engagement_service

# Configurable formula weights as decided in memory.md
ACCURACY_WEIGHT = 0.60
COMPLETION_WEIGHT = 0.20
CONSISTENCY_WEIGHT = 0.20


def load_child_session_dataframe(child_id):
    """Loads all activity sessions for a child joined with activity and category metadata into a pandas DataFrame."""
    query = db.session.query(
        ActivitySession.id.label('session_id'),
        ActivitySession.activity_id,
        Activity.title.label('activity_title'),
        Activity.category_id,
        Category.slug.label('category_slug'),
        Category.name.label('category_name'),
        ActivitySession.status,
        ActivitySession.attempts,
        ActivitySession.correct_answers,
        ActivitySession.accuracy,
        ActivitySession.duration_seconds,
        ActivitySession.start_time,
        ActivitySession.end_time
    ).join(
        Activity, ActivitySession.activity_id == Activity.id
    ).join(
        Category, Activity.category_id == Category.id
    ).filter(
        ActivitySession.child_id == child_id
    )

    records = [dict(row._mapping) for row in query.all()]
    if not records:
        return pd.DataFrame(columns=[
            'session_id', 'activity_id', 'activity_title', 'category_id',
            'category_slug', 'category_name', 'status', 'attempts',
            'correct_answers', 'accuracy', 'duration_seconds', 'start_time', 'end_time'
        ])

    df = pd.DataFrame(records)
    df['accuracy'] = pd.to_numeric(df['accuracy'], errors='coerce').fillna(0.0)
    df['attempts'] = pd.to_numeric(df['attempts'], errors='coerce').fillna(0).astype(int)
    df['correct_answers'] = pd.to_numeric(df['correct_answers'], errors='coerce').fillna(0).astype(int)
    df['duration_seconds'] = pd.to_numeric(df['duration_seconds'], errors='coerce').fillna(0).astype(int)
    return df


def compute_overall_accuracy(df):
    """Calculates weighted accuracy percentage across all sessions based on attempts and correct responses."""
    if df.empty:
        return 0.0
    total_attempts = df['attempts'].sum()
    total_correct = df['correct_answers'].sum()
    if total_attempts > 0:
        return round(float((total_correct / total_attempts) * 100.0), 2)
    return round(float(df['accuracy'].mean()), 2)


def compute_completion_rate(df):
    """Measures the proportion of started sessions that were finished without early abandonment."""
    if df.empty:
        return 0.0
    completed_count = (df['status'] == ActivitySession.STATUS_COMPLETED).sum()
    return round(float((completed_count / len(df)) * 100.0), 2)


def compute_consistency_score(df):
    """Measures performance stability across sessions by penalizing accuracy variance on a 0-100 scale."""
    if df.empty:
        return 100.0
    if len(df) < 2:
        return 100.0

    # Calculate standard deviation of accuracy across sessions
    std_dev = float(df['accuracy'].std())
    if np.isnan(std_dev):
        return 100.0

    # Maximum standard deviation for a 0-100 variable is 50.0
    variance_penalty = min(50.0, std_dev) * 2.0
    consistency = max(0.0, 100.0 - variance_penalty)
    return round(float(consistency), 2)


def compute_category_aggregates(df):
    """Aggregates average accuracy and session frequency grouped across all educational categories."""
    categories = Category.query.order_by(Category.id).all()
    aggregates = {}

    for cat in categories:
        cat_df = df[df['category_id'] == cat.id] if not df.empty else pd.DataFrame()
        if not cat_df.empty:
            cat_attempts = cat_df['attempts'].sum()
            cat_correct = cat_df['correct_answers'].sum()
            cat_acc = round(float((cat_correct / cat_attempts) * 100.0), 2) if cat_attempts > 0 else round(float(cat_df['accuracy'].mean()), 2)
            session_count = len(cat_df)
        else:
            cat_acc = 0.0
            session_count = 0

        aggregates[cat.slug] = {
            'category_id': cat.id,
            'name': cat.name,
            'slug': cat.slug,
            'icon': cat.icon,
            'accuracy': cat_acc,
            'sessions_count': session_count
        }

    return aggregates


def compute_performance_score(accuracy, completion_rate, consistency):
    """Calculates composite performance score using configured weights: accuracy*0.60 + completion*0.20 + consistency*0.20."""
    score = (
        float(accuracy) * ACCURACY_WEIGHT +
        float(completion_rate) * COMPLETION_WEIGHT +
        float(consistency) * CONSISTENCY_WEIGHT
    )
    bounded_score = min(100.0, max(0.0, score))
    return round(float(bounded_score), 2)


def update_child_progress_records(child_id):
    """Populates progress_records table on-demand with per-category accuracy, engagement, and performance metrics."""
    df = load_child_session_dataframe(child_id)
    categories = Category.query.order_by(Category.id).all()
    created_records = []
    now = datetime.now(timezone.utc)

    for cat in categories:
        cat_df = df[df['category_id'] == cat.id] if not df.empty else pd.DataFrame()
        if not cat_df.empty:
            cat_acc = compute_overall_accuracy(cat_df)
            cat_completion = compute_completion_rate(cat_df)
            cat_consistency = compute_consistency_score(cat_df)
            cat_perf = compute_performance_score(cat_acc, cat_completion, cat_consistency)
            cat_eng = engagement_service.compute_category_engagement(child_id, cat.id)
        else:
            cat_acc = 0.0
            cat_perf = 0.0
            cat_eng = 0.0

        rec = ProgressRecord(
            child_id=child_id,
            category_id=cat.id,
            accuracy=cat_acc,
            engagement_score=cat_eng,
            performance_score=cat_perf,
            recorded_at=now
        )
        db.session.add(rec)
        created_records.append(rec)

    db.session.commit()
    return created_records


def get_child_analytics_snapshot(child_id):
    """Assembles a comprehensive, explainable analytics snapshot for dashboards and reporting."""
    df = load_child_session_dataframe(child_id)

    overall_accuracy = compute_overall_accuracy(df)
    completion_rate = compute_completion_rate(df)
    consistency = compute_consistency_score(df)
    performance_score = compute_performance_score(overall_accuracy, completion_rate, consistency)
    engagement_index = engagement_service.compute_engagement_index(child_id, session_df=df)
    category_breakdown = compute_category_aggregates(df)

    total_sessions = len(df)
    completed_sessions = int((df['status'] == ActivitySession.STATUS_COMPLETED).sum()) if not df.empty else 0
    total_duration = int(df['duration_seconds'].sum()) if not df.empty else 0

    return {
        'child_id': child_id,
        'overall_accuracy': overall_accuracy,
        'completion_rate': completion_rate,
        'consistency': consistency,
        'performance_score': performance_score,
        'engagement_index': engagement_index,
        'category_breakdown': category_breakdown,
        'total_sessions': total_sessions,
        'completed_sessions': completed_sessions,
        'total_duration_seconds': total_duration,
        'weights': {
            'accuracy': ACCURACY_WEIGHT,
            'completion': COMPLETION_WEIGHT,
            'consistency': CONSISTENCY_WEIGHT
        },
        'recorded_at': datetime.now(timezone.utc).isoformat()
    }


def compute_category_age_band_engagement_trend(category_id=None, age_band=None) -> str:
    """
    Computes engagement and performance trend ('improving', 'declining', or 'steady')
    for a given category and optional age band.
    Compares average accuracy of recent completed sessions vs earlier completed sessions.
    """
    query = ActivitySession.query.join(Activity, ActivitySession.activity_id == Activity.id)
    if category_id is not None:
        query = query.filter(Activity.category_id == category_id)

    if age_band and 'all' not in age_band.lower():
        try:
            bands = [b.strip() for b in age_band.split(',')]
            age_ranges = []
            for b in bands:
                if '-' in b:
                    parts = b.split('-')
                    min_a, max_a = int(parts[0].strip()), int(parts[1].strip())
                    age_ranges.append((min_a, max_a))
            if age_ranges:
                min_bound = min(r[0] for r in age_ranges)
                max_bound = max(r[1] for r in age_ranges)
                query = query.join(Child, ActivitySession.child_id == Child.id).filter(
                    Child.age >= min_bound, Child.age <= max_bound
                )
        except Exception:
            pass

    sessions = query.filter(
        ActivitySession.status == ActivitySession.STATUS_COMPLETED
    ).order_by(ActivitySession.start_time.asc(), ActivitySession.id.asc()).all()

    if len(sessions) < 2:
        return 'steady'

    midpoint = len(sessions) // 2
    earlier_sessions = sessions[:midpoint]
    recent_sessions = sessions[midpoint:]

    earlier_acc = sum(s.accuracy for s in earlier_sessions) / len(earlier_sessions)
    recent_acc = sum(s.accuracy for s in recent_sessions) / len(recent_sessions)

    delta = recent_acc - earlier_acc
    if delta >= 3.0:
        return 'improving'
    elif delta <= -3.0:
        return 'declining'
    return 'steady'
