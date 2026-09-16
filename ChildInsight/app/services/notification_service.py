from datetime import datetime, timezone, timedelta
from sqlalchemy import func
from app import db
from app.models.user import User
from app.models.child import Child
from app.models.activity import Activity, Category
from app.models.session import ActivitySession
from app.models.teacher_assignment import TeacherAssignment
from app.models.child_teacher_access import ChildTeacherAccess
from app.models.recommendation import Recommendation
from app.models.notification import Notification
from app.services import analytics_service


def get_daily_completed_count(child_id):
    """Returns count of sessions completed by a child today (UTC)."""
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    count = ActivitySession.query.filter(
        ActivitySession.child_id == child_id,
        ActivitySession.status == ActivitySession.STATUS_COMPLETED,
        ActivitySession.end_time >= today_start
    ).count()
    return max(1, count)


def compose_activity_completed_message(child, activity, session):
    """
    Builds a friendly, specific notification text from real session and category data,
    e.g. 'Aarav completed 5 activities today. Strong performance: Memory, Visual Matching. Suggested practice: Interactive Reading'
    """
    daily_count = get_daily_completed_count(child.id)
    child_name = child.name.split()[0]  # Friendly first name

    # Fetch category performance analytics
    df = analytics_service.load_child_session_dataframe(child.id)
    aggregates = analytics_service.compute_category_aggregates(df)
    
    strong_categories = []
    practice_candidates = []

    for slug, cat_data in aggregates.items():
        acc = cat_data.get('accuracy', 0)
        cat_name = cat_data.get('name', '')
        sessions_count = cat_data.get('sessions_count', 0)
        if acc >= 75.0 and sessions_count > 0:
            strong_categories.append(cat_name)
        elif acc < 60.0 and sessions_count > 0:
            practice_candidates.append(cat_name)

    # Current activity's category
    current_cat_name = activity.category.name if activity and activity.category else "Learning"

    # Find pending recommendations for practice suggestion
    pending_rec = Recommendation.query.filter_by(child_id=child.id).order_by(Recommendation.priority.asc()).first()
    suggested_practice = None
    if pending_rec and pending_rec.activity:
        suggested_practice = pending_rec.activity.title
    elif practice_candidates:
        suggested_practice = practice_candidates[0]

    # Compose specific message
    if strong_categories and suggested_practice:
        strong_str = ", ".join(strong_categories[:2])
        msg = f"{child_name} completed {daily_count} {'activity' if daily_count == 1 else 'activities'} today. Strong performance: {strong_str}. Suggested practice: {suggested_practice}."
    elif strong_categories:
        strong_str = ", ".join(strong_categories[:2])
        msg = f"{child_name} completed {daily_count} {'activity' if daily_count == 1 else 'activities'} today with strong performance in {strong_str}."
    elif suggested_practice:
        msg = f"{child_name} completed {daily_count} {'activity' if daily_count == 1 else 'activities'} today in {current_cat_name}. Suggested practice: {suggested_practice}."
    else:
        acc = int(session.accuracy) if session and session.accuracy is not None else 100
        msg = f"{child_name} completed {daily_count} {'activity' if daily_count == 1 else 'activities'} today, exploring '{activity.title}' ({acc}% accuracy)."

    return msg


def notify_activity_completed(child_id, session_id):
    """
    Creates real-data notification for child's parent and assigned teachers upon activity completion.
    """
    child = db.session.get(Child, child_id)
    session = db.session.get(ActivitySession, session_id)
    if not child or not session:
        return []

    activity = session.activity or db.session.get(Activity, session.activity_id)
    message = compose_activity_completed_message(child, activity, session)
    from app.agent import compliance_agent
    message = compliance_agent.enforce_compliance(
        message,
        context={'source': 'notification', 'child_id': child.id, 'user_id': child.parent_id},
        fallback_text=f"{child.name.split()[0]} completed an engaging learning activity today!"
    )
    link = f"/parent/dashboard?child_id={child.id}"

    created_notifications = []

    # 1. Notify Parent
    if child.parent_id:
        notif = Notification(
            user_id=child.parent_id,
            child_id=child.id,
            notification_type=Notification.TYPE_ACTIVITY_COMPLETED,
            message=message,
            link=link
        )
        db.session.add(notif)
        created_notifications.append(notif)

    # 2. Notify Assigned and Parent-Granted Teachers
    assignments = TeacherAssignment.query.filter_by(child_id=child.id).all()
    teacher_ids = {a.teacher_id for a in assignments if a.teacher_id}
    grants = ChildTeacherAccess.query.filter_by(
        child_id=child.id,
        status=ChildTeacherAccess.STATUS_ACTIVE
    ).all()
    for g in grants:
        if g.teacher_id:
            teacher_ids.add(g.teacher_id)

    for tid in teacher_ids:
        teacher_notif = Notification(
            user_id=tid,
            child_id=child.id,
            notification_type=Notification.TYPE_ACTIVITY_COMPLETED,
            message=message,
            link=f"/teacher/students/{child.id}"
        )
        db.session.add(teacher_notif)
        created_notifications.append(teacher_notif)

    db.session.commit()
    return created_notifications


def notify_recommendation_generated(child_id, rec_list):
    """
    Creates notification for parent when fresh tailored recommendations are generated.
    """
    child = db.session.get(Child, child_id)
    if not child or not child.parent_id or not rec_list:
        return None

    top_rec = rec_list[0]
    act_title = top_rec.get('activity_title', 'Activity')
    cat_name = top_rec.get('category_name', '')
    difficulty = top_rec.get('difficulty', '')

    child_name = child.name.split()[0]
    raw_message = f"New learning recommendation for {child_name}: '{act_title}' ({cat_name} — {difficulty}) suggested to guide next steps."
    from app.agent import compliance_agent
    message = compliance_agent.enforce_compliance(
        raw_message,
        context={'source': 'notification', 'child_id': child.id, 'user_id': child.parent_id},
        fallback_text=f"New personalized learning recommendation available for {child_name}."
    )
    link = f"/parent/dashboard?child_id={child.id}#recommendations"

    # Avoid duplicate notification if the exact same recommendation notice is already unread
    existing = Notification.query.filter_by(
        user_id=child.parent_id,
        child_id=child.id,
        notification_type=Notification.TYPE_RECOMMENDATION_GENERATED,
        message=message,
        is_read=False
    ).first()
    if existing:
        return existing

    notif = Notification(
        user_id=child.parent_id,
        child_id=child.id,
        notification_type=Notification.TYPE_RECOMMENDATION_GENERATED,
        message=message,
        link=link
    )
    db.session.add(notif)
    db.session.commit()
    return notif


def notify_teacher_assigned(teacher_id, child_id, activity_id, note=None):
    """
    Creates notification for parent when an assigned educator assigns a guided activity.
    """
    child = db.session.get(Child, child_id)
    teacher = db.session.get(User, teacher_id)
    activity = db.session.get(Activity, activity_id)

    if not child or not child.parent_id or not teacher or not activity:
        return None

    child_name = child.name.split()[0]
    teacher_name = teacher.name.split()[0] if teacher.name else "Teacher"
    note_str = f" Note: \"{note}\"" if note else ""
    raw_message = f"Educator {teacher.name} assigned '{activity.title}' to {child_name} for guided learning.{note_str}"
    from app.agent import compliance_agent
    message = compliance_agent.enforce_compliance(
        raw_message,
        context={'source': 'notification', 'child_id': child.id, 'user_id': child.parent_id},
        fallback_text=f"Educator assigned an activity to {child_name} for guided learning."
    )
    link = f"/parent/dashboard?child_id={child.id}"

    notif = Notification(
        user_id=child.parent_id,
        child_id=child.id,
        notification_type=Notification.TYPE_TEACHER_ASSIGNED,
        message=message,
        link=link
    )
    db.session.add(notif)
    db.session.commit()
    return notif


def notify_teacher_access_request(parent_user, teacher_user, child):
    """Notifies a teacher when a parent requests them to view a child's report."""
    if not parent_user or not teacher_user or not child:
        return None

    parent_name = parent_user.name if parent_user.name else "A parent"
    raw_message = f"Parent {parent_name} has requested you view {child.name}'s learning report."
    from app.agent import compliance_agent
    message = compliance_agent.enforce_compliance(
        raw_message,
        context={'source': 'notification', 'child_id': child.id, 'user_id': teacher_user.id},
        fallback_text=f"A parent has requested you view {child.name}'s learning report."
    )
    notif = Notification(
        user_id=teacher_user.id,
        child_id=child.id,
        notification_type='teacher_access_request',
        message=message,
        link="/teacher/dashboard#access-requests"
    )
    db.session.add(notif)
    db.session.commit()
    return notif


def notify_parent_access_response(grant, accepted=True):
    """Notifies the parent when an educator accepts or declines an access request."""
    if not grant or not grant.child:
        return None

    teacher_name = grant.teacher.name if grant.teacher and grant.teacher.name else "An educator"
    child_name = grant.child.name
    if accepted:
        raw_message = f"Educator {teacher_name} accepted access to {child_name}'s learning profile."
        notif_type = 'teacher_access_accepted'
    else:
        raw_message = f"Educator {teacher_name} declined the access request for {child_name}."
        notif_type = 'teacher_access_declined'

    from app.agent import compliance_agent
    message = compliance_agent.enforce_compliance(
        raw_message,
        context={'source': 'notification', 'child_id': grant.child_id, 'user_id': grant.requested_by_parent_id},
        fallback_text=raw_message
    )
    notif = Notification(
        user_id=grant.requested_by_parent_id,
        child_id=grant.child_id,
        notification_type=notif_type,
        message=message,
        link=f"/parent/children/{grant.child_id}"
    )
    db.session.add(notif)
    db.session.commit()
    return notif


def notify_teacher_access_revoked(teacher_user, child):
    """Notifies a teacher if their parent-granted access to a child was revoked."""
    if not teacher_user or not child:
        return None

    raw_message = f"Access to {child.name}'s learning profile has been revoked by the parent."
    from app.agent import compliance_agent
    message = compliance_agent.enforce_compliance(
        raw_message,
        context={'source': 'notification', 'child_id': child.id, 'user_id': teacher_user.id},
        fallback_text=raw_message
    )
    notif = Notification(
        user_id=teacher_user.id,
        child_id=child.id,
        notification_type='teacher_access_revoked',
        message=message,
        link="/teacher/dashboard"
    )
    db.session.add(notif)
    db.session.commit()
    return notif


def get_user_notifications(user_id, limit=15, unread_only=False):
    """Fetches ordered notifications for a user."""
    query = Notification.query.filter_by(user_id=user_id)
    if unread_only:
        query = query.filter_by(is_read=False)
    return query.order_by(Notification.created_at.desc()).limit(limit).all()


def get_unread_count(user_id):
    """Returns number of unread notifications for a user."""
    return Notification.query.filter_by(user_id=user_id, is_read=False).count()


def mark_notification_read(notification_id, user_id):
    """Marks a single notification as read if owned by user."""
    notif = Notification.query.filter_by(id=notification_id, user_id=user_id).first()
    if notif:
        notif.mark_as_read()
        db.session.commit()
        return True
    return False


def mark_all_read(user_id):
    """Marks all unread notifications for a user as read."""
    unread_notifs = Notification.query.filter_by(user_id=user_id, is_read=False).all()
    for notif in unread_notifs:
        notif.mark_as_read()
    db.session.commit()
    return len(unread_notifs)
