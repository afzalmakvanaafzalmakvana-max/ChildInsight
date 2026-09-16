from datetime import datetime, timezone
from app import db
from app.models.session import ActivitySession, InteractionEvent


def start_session(child_id, activity_id):
    """Starts a new activity session and logs the started event."""
    # Close any lingering in-progress session for this child and activity
    open_sessions = ActivitySession.query.filter_by(
        child_id=child_id,
        activity_id=activity_id,
        status=ActivitySession.STATUS_IN_PROGRESS
    ).all()
    now = datetime.now(timezone.utc)
    for old_s in open_sessions:
        old_s.status = ActivitySession.STATUS_ABANDONED
        old_s.end_time = now
        if old_s.start_time:
            st = old_s.start_time.replace(tzinfo=timezone.utc) if old_s.start_time.tzinfo is None else old_s.start_time
            old_s.duration_seconds = max(0, int((now - st).total_seconds()))
        abandon_event = InteractionEvent(
            session_id=old_s.id,
            child_id=child_id,
            event_type=InteractionEvent.EVENT_ABANDONED,
            timestamp=now
        )
        abandon_event.payload_data = {'reason': 'superseded_by_new_session'}
        db.session.add(abandon_event)

    new_session = ActivitySession(
        child_id=child_id,
        activity_id=activity_id,
        start_time=now,
        status=ActivitySession.STATUS_IN_PROGRESS,
        attempts=0,
        correct_answers=0,
        accuracy=0.0,
        duration_seconds=0
    )
    db.session.add(new_session)
    db.session.flush()

    start_event = InteractionEvent(
        session_id=new_session.id,
        child_id=child_id,
        event_type=InteractionEvent.EVENT_STARTED,
        timestamp=now
    )
    start_event.payload_data = {'activity_id': activity_id}
    db.session.add(start_event)
    db.session.commit()
    return new_session


def log_question_viewed(session_id, child_id, question_id, q_idx=None):
    """Logs when a child is presented with a question on screen."""
    now = datetime.now(timezone.utc)
    event = InteractionEvent(
        session_id=session_id,
        child_id=child_id,
        question_id=question_id,
        event_type=InteractionEvent.EVENT_QUESTION_VIEWED,
        timestamp=now
    )
    event.payload_data = {'q_idx': q_idx}
    db.session.add(event)
    db.session.commit()
    return event


def log_hint_used(session_id, child_id, question_id):
    """Logs when a child requests assistance via an activity hint."""
    now = datetime.now(timezone.utc)
    event = InteractionEvent(
        session_id=session_id,
        child_id=child_id,
        question_id=question_id,
        event_type=InteractionEvent.EVENT_HINT_USED,
        timestamp=now
    )
    event.payload_data = {'question_id': question_id}
    db.session.add(event)
    db.session.commit()
    return event


def log_question_skipped(session_id, child_id, question_id):
    """Logs when a child chooses to skip a question and treats it as an attempt."""
    act_session = db.session.get(ActivitySession, session_id)
    if not act_session or act_session.child_id != child_id:
        return None

    now = datetime.now(timezone.utc)
    event = InteractionEvent(
        session_id=session_id,
        child_id=child_id,
        question_id=question_id,
        event_type=InteractionEvent.EVENT_SKIPPED,
        timestamp=now
    )
    event.payload_data = {'question_id': question_id}
    db.session.add(event)

    act_session.attempts += 1
    act_session.recalculate_accuracy()
    db.session.commit()
    return act_session


def record_answer(session_id, child_id, question_id, selected_answer, is_correct):
    """Updates session metrics and logs answer selection plus accuracy outcome."""
    act_session = db.session.get(ActivitySession, session_id)
    if not act_session or act_session.child_id != child_id:
        return None, None

    now = datetime.now(timezone.utc)

    # 1. Answer selected event
    select_event = InteractionEvent(
        session_id=session_id,
        child_id=child_id,
        question_id=question_id,
        event_type=InteractionEvent.EVENT_ANSWER_SELECTED,
        timestamp=now
    )
    select_event.payload_data = {'selected_answer': selected_answer}
    db.session.add(select_event)

    # 2. Outcome event (correct or incorrect)
    outcome_type = InteractionEvent.EVENT_CORRECT if is_correct else InteractionEvent.EVENT_INCORRECT
    outcome_event = InteractionEvent(
        session_id=session_id,
        child_id=child_id,
        question_id=question_id,
        event_type=outcome_type,
        timestamp=now
    )
    outcome_event.payload_data = {'selected_answer': selected_answer, 'is_correct': is_correct}
    db.session.add(outcome_event)

    # 3. Update session metrics
    act_session.attempts += 1
    if is_correct:
        act_session.correct_answers += 1
    act_session.recalculate_accuracy()

    db.session.commit()
    return act_session, outcome_event


def complete_session(session_id, child_id):
    """Finalizes an active session with elapsed duration and completed status."""
    act_session = db.session.get(ActivitySession, session_id)
    if not act_session or act_session.child_id != child_id:
        return None

    now = datetime.now(timezone.utc)
    if act_session.status != ActivitySession.STATUS_COMPLETED:
        act_session.end_time = now
        if act_session.start_time:
            st = act_session.start_time.replace(tzinfo=timezone.utc) if act_session.start_time.tzinfo is None else act_session.start_time
            act_session.duration_seconds = max(0, int((now - st).total_seconds()))
        act_session.status = ActivitySession.STATUS_COMPLETED
        act_session.recalculate_accuracy()

        comp_event = InteractionEvent(
            session_id=session_id,
            child_id=child_id,
            event_type=InteractionEvent.EVENT_COMPLETED,
            timestamp=now
        )
        comp_event.payload_data = {
            'accuracy': act_session.accuracy,
            'duration_seconds': act_session.duration_seconds,
            'attempts': act_session.attempts,
            'correct_answers': act_session.correct_answers
        }
        db.session.add(comp_event)
        db.session.commit()

        # Trigger in-dashboard notification for parent & assigned educators
        try:
            from app.services import notification_service
            notification_service.notify_activity_completed(child_id, session_id)
        except Exception:
            pass

    return act_session


def abandon_session(session_id, child_id, reason='user_exit'):
    """Marks an active session as abandoned and records the exit event."""
    act_session = db.session.get(ActivitySession, session_id)
    if not act_session or act_session.child_id != child_id:
        return None

    now = datetime.now(timezone.utc)
    if act_session.status == ActivitySession.STATUS_IN_PROGRESS:
        act_session.end_time = now
        if act_session.start_time:
            st = act_session.start_time.replace(tzinfo=timezone.utc) if act_session.start_time.tzinfo is None else act_session.start_time
            act_session.duration_seconds = max(0, int((now - st).total_seconds()))
        act_session.status = ActivitySession.STATUS_ABANDONED

        ab_event = InteractionEvent(
            session_id=session_id,
            child_id=child_id,
            event_type=InteractionEvent.EVENT_ABANDONED,
            timestamp=now
        )
        ab_event.payload_data = {'reason': reason}
        db.session.add(ab_event)
        db.session.commit()

    return act_session
