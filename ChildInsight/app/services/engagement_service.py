import pandas as pd
from app import db
from app.models.session import ActivitySession, InteractionEvent
from app.models.activity import Activity, Category

# Documented component weights summing to 1.00 (100%)
WEIGHT_COMPLETION = 0.20
WEIGHT_ABANDONMENT = 0.15
WEIGHT_REPEAT = 0.15
WEIGHT_FREQUENCY = 0.15
WEIGHT_TIME_SPENT = 0.15
WEIGHT_VOLUNTARY = 0.10
WEIGHT_RETRY = 0.10


def compute_engagement_index(child_id, session_df=None):
    """Computes a composite 0-100 engagement index from 7 weighted behavioral interaction signals."""
    if session_df is None:
        sessions = ActivitySession.query.filter_by(child_id=child_id).all()
        if not sessions:
            return 0.0
        session_data = [{
            'id': s.id,
            'activity_id': s.activity_id,
            'status': s.status,
            'duration_seconds': s.duration_seconds or 0,
            'attempts': s.attempts or 0,
            'correct_answers': s.correct_answers or 0,
        } for s in sessions]
        session_df = pd.DataFrame(session_data)

    if session_df.empty:
        return 0.0

    total_sessions = len(session_df)

    # 1. Completion Rate Factor (Weight: 0.20)
    completed_sessions = (session_df['status'] == ActivitySession.STATUS_COMPLETED).sum()
    completion_score = (completed_sessions / total_sessions) * 100.0

    # 2. Abandonment Inverted Factor (Weight: 0.15)
    abandoned_sessions = (session_df['status'] == ActivitySession.STATUS_ABANDONED).sum()
    abandonment_rate = (abandoned_sessions / total_sessions) * 100.0
    abandonment_score = max(0.0, 100.0 - abandonment_rate)

    # 3. Repeat Participation Factor (Weight: 0.15)
    # Benchmark: 5 sessions represents active, sustained engagement
    repeat_score = min(100.0, (total_sessions / 5.0) * 100.0)

    # 4. Interaction Frequency Factor (Weight: 0.15)
    # Average events per session; benchmark is 4 events per session
    total_events = InteractionEvent.query.filter_by(child_id=child_id).count()
    avg_events = total_events / max(1, total_sessions)
    frequency_score = min(100.0, (avg_events / 4.0) * 100.0)

    # 5. Time Spent Factor (Weight: 0.15)
    # Benchmark: average 60+ seconds per learning session indicates deliberate engagement
    avg_duration = session_df['duration_seconds'].mean()
    time_score = min(100.0, (avg_duration / 60.0) * 100.0) if avg_duration > 0 else 0.0

    # 6. Voluntary Category Exploration Factor (Weight: 0.10)
    # Explored categories count out of the 5 standard categories
    act_ids = session_df['activity_id'].unique()
    if len(act_ids) > 0:
        distinct_categories = db.session.query(Activity.category_id).filter(Activity.id.in_(act_ids)).distinct().count()
    else:
        distinct_categories = 0
    total_categories = max(1, Category.query.count() or 5)
    voluntary_score = min(100.0, (distinct_categories / total_categories) * 100.0)

    # 7. Retry & Persistence Factor (Weight: 0.10)
    # Measures whether child persists through incorrect answers or uses hints rather than abandoning
    incorrect_events = InteractionEvent.query.filter_by(child_id=child_id, event_type=InteractionEvent.EVENT_INCORRECT).count()
    hint_events = InteractionEvent.query.filter_by(child_id=child_id, event_type=InteractionEvent.EVENT_HINT_USED).count()

    if incorrect_events == 0 and hint_events == 0:
        retry_score = 100.0 if completion_score > 50 else 50.0
    else:
        # Child encountered friction; reward active hint usage and subsequent completed sessions
        persistence_signal = (hint_events * 25.0) + (completion_score * 0.5)
        retry_score = min(100.0, max(20.0, persistence_signal))

    # Combine using documented weights
    raw_index = (
        completion_score * WEIGHT_COMPLETION +
        abandonment_score * WEIGHT_ABANDONMENT +
        repeat_score * WEIGHT_REPEAT +
        frequency_score * WEIGHT_FREQUENCY +
        time_score * WEIGHT_TIME_SPENT +
        voluntary_score * WEIGHT_VOLUNTARY +
        retry_score * WEIGHT_RETRY
    )

    return round(float(min(100.0, max(0.0, raw_index))), 2)


def compute_category_engagement(child_id, category_id):
    """Computes the engagement score focused on activities within a specific learning category."""
    # Query sessions matching the category
    sessions = db.session.query(ActivitySession).join(
        Activity, ActivitySession.activity_id == Activity.id
    ).filter(
        ActivitySession.child_id == child_id,
        Activity.category_id == category_id
    ).all()

    if not sessions:
        return 0.0

    session_data = [{
        'id': s.id,
        'activity_id': s.activity_id,
        'status': s.status,
        'duration_seconds': s.duration_seconds or 0,
        'attempts': s.attempts or 0,
        'correct_answers': s.correct_answers or 0,
    } for s in sessions]
    df = pd.DataFrame(session_data)
    return compute_engagement_index(child_id, session_df=df)
