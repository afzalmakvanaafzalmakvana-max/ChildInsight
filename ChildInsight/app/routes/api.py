from flask import Blueprint, jsonify, request, render_template
from flask_login import current_user, login_required
from app import db, csrf
from app.utils.openapi_spec import OPENAPI_SPEC
from app.models.child import Child
from app.models.activity import Activity
from app.models.session import ActivitySession, InteractionEvent
from app.models.teacher_assignment import TeacherAssignment
from app.models.child_teacher_access import ChildTeacherAccess
from app.models.progress import ProgressRecord
from app.models.recommendation import Recommendation
from app.services import event_tracker, analytics_service, recommendation_service

api_bp = Blueprint('api', __name__)
csrf.exempt(api_bp)


def check_child_api_access(child_id):
    """Enforces authorization on child data for API requests."""
    if not current_user.is_authenticated:
        return None, (jsonify({'error': 'Unauthorized'}), 401)

    child = db.session.get(Child, child_id)
    if not child:
        return None, (jsonify({'error': 'Child not found'}), 404)

    if current_user.is_admin:
        return child, None
    if current_user.is_parent and child.parent_id == current_user.id:
        return child, None
    if current_user.is_teacher:
        is_assigned = TeacherAssignment.query.filter_by(
            teacher_id=current_user.id,
            child_id=child.id
        ).first()
        if is_assigned:
            return child, None

        is_granted = ChildTeacherAccess.query.filter_by(
            teacher_id=current_user.id,
            child_id=child.id,
            status=ChildTeacherAccess.STATUS_ACTIVE
        ).first()
        if is_granted:
            return child, None

    return None, (jsonify({'error': 'Forbidden'}), 403)


@api_bp.route('/health')
def health_check():
    return jsonify({
        'status': 'healthy',
        'service': 'ChildInsight API',
        'version': '1.0.0'
    })


@api_bp.route('/auth/status')
def auth_status():
    if current_user.is_authenticated:
        return jsonify({
            'authenticated': True,
            'user': {
                'id': current_user.id,
                'name': current_user.name,
                'email': current_user.email,
                'role': current_user.role
            }
        })
    return jsonify({
        'authenticated': False,
        'user': None
    })


@api_bp.route('/children', methods=['GET'])
def list_children():
    """List children accessible to the authenticated user."""
    if not current_user.is_authenticated:
        return jsonify({'error': 'Unauthorized'}), 401

    if current_user.is_admin:
        children = Child.query.all()
    elif current_user.is_parent:
        children = Child.query.filter_by(parent_id=current_user.id).all()
    elif current_user.is_teacher:
        assigned_ids = [a.child_id for a in TeacherAssignment.query.filter_by(teacher_id=current_user.id).all()]
        granted_ids = [g.child_id for g in ChildTeacherAccess.query.filter_by(teacher_id=current_user.id, status=ChildTeacherAccess.STATUS_ACTIVE).all()]
        all_ids = list(set(assigned_ids + granted_ids))
        children = Child.query.filter(Child.id.in_(all_ids)).all() if all_ids else []
    else:
        children = []

    return jsonify({
        'count': len(children),
        'children': [{
            'id': c.id,
            'name': c.name,
            'age': c.age,
            'grade': c.grade,
            'preferred_language': c.preferred_language
        } for c in children]
    })


@api_bp.route('/children/<int:child_id>', methods=['GET'])
def get_child(child_id):
    """Retrieve child details by ID."""
    child, err = check_child_api_access(child_id)
    if err:
        return err

    return jsonify({
        'id': child.id,
        'name': child.name,
        'age': child.age,
        'grade': child.grade,
        'preferred_language': child.preferred_language,
        'parent_id': child.parent_id
    })


@api_bp.route('/activities', methods=['GET'])
def list_activities():
    """List available active educational activities."""
    activities = Activity.query.filter_by(is_active=True).all()
    return jsonify({
        'count': len(activities),
        'activities': [{
            'id': a.id,
            'title': a.title,
            'category': a.category.name if a.category else None,
            'category_id': a.category_id,
            'difficulty': a.difficulty,
            'estimated_duration': a.estimated_duration
        } for a in activities]
    })


@api_bp.route('/activities/<int:activity_id>', methods=['GET'])
def get_activity(activity_id):
    """Get activity details including questions."""
    activity = db.session.get(Activity, activity_id)
    if not activity:
        return jsonify({'error': 'Activity not found'}), 404

    return jsonify({
        'id': activity.id,
        'title': activity.title,
        'description': activity.description,
        'category': activity.category.name if activity.category else None,
        'difficulty': activity.difficulty,
        'estimated_duration': activity.estimated_duration,
        'questions': [{
            'id': q.id,
            'question_text': q.question_text,
            'options': q.options,
            'order_num': q.order_num
        } for q in activity.questions.order_by(db.asc('order_num')).all()]
    })


@api_bp.route('/sessions', methods=['POST'])
def create_session():
    """Create a new activity session via API."""
    if not current_user.is_authenticated:
        return jsonify({'error': 'Unauthorized'}), 401

    data = request.get_json() or {}
    child_id = data.get('child_id')
    activity_id = data.get('activity_id')

    if not child_id or not activity_id:
        return jsonify({'error': 'child_id and activity_id are required'}), 400

    try:
        child_id = int(child_id)
        activity_id = int(activity_id)
        if child_id <= 0 or activity_id <= 0:
            raise ValueError()
    except (ValueError, TypeError):
        return jsonify({'error': 'child_id and activity_id must be positive integers'}), 400

    child, err = check_child_api_access(child_id)
    if err:
        return err

    activity = db.session.get(Activity, activity_id)
    if not activity:
        return jsonify({'error': 'Activity not found'}), 404

    new_session = event_tracker.start_session(child_id=child.id, activity_id=activity.id)
    return jsonify({
        'message': 'Session started',
        'session': new_session.to_dict()
    }), 201


@api_bp.route('/sessions/<int:session_id>', methods=['GET'])
def get_session(session_id):
    """Fetch session details with associated interaction events."""
    act_session = db.session.get(ActivitySession, session_id)
    if not act_session:
        return jsonify({'error': 'Session not found'}), 404

    _, err = check_child_api_access(act_session.child_id)
    if err:
        return err

    events = act_session.events.order_by(InteractionEvent.timestamp.asc()).all()
    session_data = act_session.to_dict()
    session_data['events'] = [e.to_dict() for e in events]

    return jsonify({'session': session_data})


@api_bp.route('/analytics/<int:child_id>', methods=['GET'])
def get_child_analytics(child_id):
    """Retrieve child's calculated analytics snapshot (accuracy, completion, consistency, engagement, categories)."""
    child, err = check_child_api_access(child_id)
    if err:
        return err

    snapshot = analytics_service.get_child_analytics_snapshot(child.id)
    return jsonify({'analytics': snapshot})


@api_bp.route('/progress/<int:child_id>', methods=['GET', 'POST'])
def get_or_update_progress(child_id):
    """Fetch or refresh progress records per category for a child."""
    child, err = check_child_api_access(child_id)
    if err:
        return err

    # If POST or refresh query parameter, re-compute and populate progress_records
    if request.method == 'POST' or request.args.get('refresh') == 'true':
        records = analytics_service.update_child_progress_records(child.id)
    else:
        records = ProgressRecord.query.filter_by(child_id=child.id).order_by(ProgressRecord.recorded_at.desc()).all()
        if not records:
            records = analytics_service.update_child_progress_records(child.id)

    return jsonify({
        'child_id': child.id,
        'count': len(records),
        'records': [r.to_dict() for r in records]
    })


@api_bp.route('/recommendations/<int:child_id>', methods=['GET'])
def get_child_recommendations(child_id):
    """Retrieve explainable, ranked activity recommendations for a child."""
    child, err = check_child_api_access(child_id)
    if err:
        return err

    recs = recommendation_service.get_recommendations_for_child(child.id, persist=True)
    return jsonify({
        'child_id': child.id,
        'count': len(recs),
        'recommendations': recs
    })


@api_bp.route('/notifications', methods=['GET'])
@login_required
def list_notifications():
    """Retrieve notifications and unread count for current user."""
    from app.services import notification_service
    unread_only = request.args.get('unread_only', 'false').lower() == 'true'
    limit = min(request.args.get('limit', 20, type=int), 50)
    notifs = notification_service.get_user_notifications(current_user.id, limit=limit, unread_only=unread_only)
    unread_count = notification_service.get_unread_count(current_user.id)
    return jsonify({
        'unread_count': unread_count,
        'notifications': [n.to_dict() for n in notifs]
    })


@api_bp.route('/notifications/<int:notification_id>/read', methods=['POST'])
@login_required
def mark_notification_read_api(notification_id):
    """Mark an individual notification as read."""
    from app.services import notification_service
    success = notification_service.mark_notification_read(notification_id, current_user.id)
    if not success:
        return jsonify({'error': 'Notification not found or unauthorized'}), 404
    return jsonify({
        'success': True,
        'notification_id': notification_id,
        'unread_count': notification_service.get_unread_count(current_user.id)
    })


@api_bp.route('/notifications/mark-all-read', methods=['POST'])
@login_required
def mark_all_notifications_read_api():
    """Mark all unread notifications as read for current user."""
    from app.services import notification_service
    count = notification_service.mark_all_read(current_user.id)
    return jsonify({
        'success': True,
        'marked_count': count,
        'unread_count': 0
    })


@api_bp.route('/openapi.json', methods=['GET'])
def get_openapi_json():
    """Returns the OpenAPI 3.0.3 specification in JSON format."""
    return jsonify(OPENAPI_SPEC)


@api_bp.route('/docs', methods=['GET'])
def api_docs():
    """Interactive Swagger UI API documentation explorer."""
    return render_template('api/docs.html')


@api_bp.route('/user/theme', methods=['GET', 'POST'])
@api_bp.route('/theme', methods=['GET', 'POST'])
def handle_theme_preference():
    """Get or update light/dark theme preference with DB and cookie persistence."""
    if request.method == 'GET':
        if current_user.is_authenticated and current_user.role != 'child':
            theme = current_user.theme_preference or 'light'
        else:
            theme = request.cookies.get('childinsight_theme', 'light')
        return jsonify({'theme': theme})

    data = request.get_json(silent=True) or request.form
    theme = data.get('theme', '').strip().lower() if data else ''
    if theme not in ('light', 'dark'):
        return jsonify({'error': 'Invalid theme. Must be "light" or "dark".'}), 400

    persisted = False
    if current_user.is_authenticated:
        current_user.theme_preference = theme
        db.session.commit()
        persisted = True

    resp = jsonify({
        'success': True,
        'theme': theme,
        'persisted_to_db': persisted
    })
    resp.set_cookie('childinsight_theme', theme, max_age=365 * 24 * 3600, path='/', samesite='Lax')
    return resp





