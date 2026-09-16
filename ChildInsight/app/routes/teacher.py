from datetime import datetime, timezone
from flask import Blueprint, render_template, request, Response, flash, redirect, url_for
from flask_login import login_required, current_user
from app import db
from app.models.child import Child
from app.models.activity import Activity
from app.models.session import ActivitySession
from app.models.recommendation import Recommendation
from app.models.teacher_assignment import TeacherAssignment
from app.models.child_teacher_access import ChildTeacherAccess
from app.utils.decorators import role_required, child_access_required
from app.services import analytics_service, recommendation_service, profile_service, report_service, audit_service

teacher_bp = Blueprint('teacher', __name__)


def _compute_student_status(child_id):
    """Computes an individual non-comparative progress status badge for a student."""
    snapshot = analytics_service.get_child_analytics_snapshot(child_id)
    total_sessions = snapshot.get('total_sessions', 0)

    if total_sessions == 0:
        return {
            'label': 'New Learner',
            'badge_class': 'badge-status-new',
            'color': '#4B5563',
            'bg': '#F3F4F6',
            'note': 'Starting learning journey'
        }

    acc = snapshot.get('overall_accuracy', 0.0)
    comp = snapshot.get('completion_rate', 0.0)

    if acc >= 75.0 and comp >= 60.0:
        return {
            'label': 'Progress ↑',
            'badge_class': 'badge-status-progress',
            'color': '#166534',
            'bg': '#DCFCE7',
            'note': 'Demonstrating steady skill mastery'
        }
    elif acc >= 50.0 and comp >= 50.0:
        return {
            'label': 'Stable',
            'badge_class': 'badge-status-stable',
            'color': '#4B5563',
            'bg': '#F3F4F6',
            'note': 'Consistent participation'
        }
    else:
        return {
            'label': 'Practice Suggested',
            'badge_class': 'badge-status-practice',
            'color': '#92400E',
            'bg': '#FEF3C7',
            'note': 'Benefiting from supportive activities'
        }


def _prepare_student_dashboard_data(child):
    """Prepares analytics, recommendations, and learning pattern details for a student."""
    if not child:
        return None

    snapshot = analytics_service.get_child_analytics_snapshot(child.id)
    existing_recs = Recommendation.query.filter_by(child_id=child.id).order_by(Recommendation.priority.asc(), Recommendation.created_at.desc()).all()
    if existing_recs:
        recommendations = [r.to_dict() for r in existing_recs]
    else:
        recommendations = recommendation_service.get_recommendations_for_child(child.id, persist=True)
    pattern_profile = profile_service.get_child_learning_pattern_observation(child.id)
    recent_sessions = (
        ActivitySession.query.filter_by(child_id=child.id)
        .order_by(ActivitySession.start_time.desc())
        .limit(8)
        .all()
    )

    category_breakdown = snapshot.get('category_breakdown', {})
    category_labels = [c.get('name', k.capitalize()) for k, c in category_breakdown.items()]
    category_accuracies = [round(c.get('accuracy', 0.0), 1) for k, c in category_breakdown.items()]

    trend_sessions = (
        ActivitySession.query.filter_by(child_id=child.id, status=ActivitySession.STATUS_COMPLETED)
        .order_by(ActivitySession.start_time.asc())
        .limit(10)
        .all()
    )
    trend_labels = [
        s.start_time.strftime('%b %d') if s.start_time else f"S#{s.id}"
        for s in trend_sessions
    ]
    trend_accuracies = [round(s.accuracy, 1) for s in trend_sessions]

    status_info = _compute_student_status(child.id)

    return {
        'snapshot': snapshot,
        'recommendations': recommendations,
        'pattern_profile': pattern_profile,
        'recent_sessions': recent_sessions,
        'category_labels': category_labels,
        'category_accuracies': category_accuracies,
        'trend_labels': trend_labels,
        'trend_accuracies': trend_accuracies,
        'status_info': status_info
    }


def _get_accessible_children_for_teacher(teacher_id):
    """Retrieves all unique children accessible to a teacher via admin assignment or active parent grant."""
    admin_assigned = TeacherAssignment.query.filter_by(teacher_id=teacher_id).all()
    parent_granted = ChildTeacherAccess.query.filter_by(
        teacher_id=teacher_id,
        status=ChildTeacherAccess.STATUS_ACTIVE
    ).all()

    seen_ids = set()
    children = []
    for a in admin_assigned:
        if a.child and a.child.id not in seen_ids:
            seen_ids.add(a.child.id)
            children.append(a.child)
    for g in parent_granted:
        if g.child and g.child.id not in seen_ids:
            seen_ids.add(g.child.id)
            children.append(g.child)
    return children


@teacher_bp.route('/dashboard')
@login_required
@role_required('teacher')
def dashboard():
    assigned_children = _get_accessible_children_for_teacher(current_user.id)

    # Pending access requests from parents awaiting teacher approval
    pending_requests = ChildTeacherAccess.query.filter_by(
        teacher_id=current_user.id,
        status=ChildTeacherAccess.STATUS_PENDING_APPROVAL
    ).order_by(ChildTeacherAccess.created_at.desc()).all()

    # Compute class-wide aggregate stats (STRICTLY AGGREGATE ONLY, NO PER-STUDENT COMPARISON)
    total_students = len(assigned_children)
    total_class_sessions = 0
    total_class_engagement_sum = 0.0

    student_entries = []
    for child in assigned_children:
        status_info = _compute_student_status(child.id)
        snap = analytics_service.get_child_analytics_snapshot(child.id)
        total_class_sessions += snap.get('completed_sessions', 0)
        total_class_engagement_sum += snap.get('engagement_index', 0.0)

        student_entries.append({
            'child': child,
            'status': status_info,
            'sessions_count': snap.get('completed_sessions', 0),
            'learning_stage': child.grade or 'Stage 1'
        })

    avg_class_engagement = round(total_class_engagement_sum / total_students, 1) if total_students > 0 else 0.0

    class_summary = {
        'total_students': total_students,
        'total_completed_sessions': total_class_sessions,
        'average_engagement': avg_class_engagement
    }

    return render_template(
        'teacher/dashboard.html',
        students=student_entries,
        class_summary=class_summary,
        pending_requests=pending_requests
    )


@teacher_bp.route('/students')
@login_required
@role_required('teacher')
def students_list():
    assigned_children = _get_accessible_children_for_teacher(current_user.id)

    q = request.args.get('q', '').strip().lower()
    grade = request.args.get('grade', '').strip()
    status = request.args.get('status', '').strip()

    student_entries = []
    for child in assigned_children:
        status_info = _compute_student_status(child.id)
        snap = analytics_service.get_child_analytics_snapshot(child.id)

        # Apply search and filters
        if q and q not in child.name.lower():
            continue
        if grade and child.grade != grade:
            continue
        if status and status_info['label'] != status:
            continue

        student_entries.append({
            'child': child,
            'status': status_info,
            'sessions_count': snap.get('completed_sessions', 0),
            'learning_stage': child.grade or 'General'
        })

    # Available grades across all assigned children for filter dropdown
    available_grades = sorted(list(set(c.grade for c in assigned_children if c.grade)))

    return render_template(
        'teacher/students_list.html',
        students=student_entries,
        available_grades=available_grades,
        current_q=request.args.get('q', ''),
        current_grade=grade,
        current_status=status
    )


@teacher_bp.route('/students/<int:child_id>')
@login_required
@role_required('teacher')
@child_access_required(write=False)
def student_detail(child_id):
    child = db.session.get(Child, child_id)
    dash_data = _prepare_student_dashboard_data(child)
    activities = Activity.query.filter_by(is_active=True).order_by(Activity.title).all()
    return render_template(
        'teacher/student_detail.html',
        child=child,
        dash_data=dash_data,
        activities=activities
    )


@teacher_bp.route('/students/<int:child_id>/assign-activity', methods=['POST'])
@login_required
@role_required('teacher')
@child_access_required(write=False)
def assign_activity(child_id):
    """Allows teacher to recommend or assign an activity to an assigned student with audit logging."""
    child = db.session.get(Child, child_id)
    activity_id = request.form.get('activity_id', type=int)
    note = request.form.get('note', '').strip()

    if not activity_id:
        flash("Please select an activity to assign.", "warning")
        return redirect(url_for('teacher.student_detail', child_id=child_id))

    activity = db.session.get(Activity, activity_id)
    if not activity:
        flash("Activity not found.", "danger")
        return redirect(url_for('teacher.student_detail', child_id=child_id))

    reason_text = note if note else f"Assigned by teacher {current_user.name} for guided learning."

    rec = Recommendation(
        child_id=child.id,
        activity_id=activity.id,
        reason=reason_text,
        recommendation_type=Recommendation.TYPE_EXPLORE,
        priority=1
    )
    db.session.add(rec)
    db.session.commit()

    # Record action in audit log
    audit_service.log_action(
        user_id=current_user.id,
        action='teacher_assign_activity',
        target_type='child',
        target_id=child.id
    )

    # Trigger in-dashboard notification for parent
    try:
        from app.services import notification_service
        notification_service.notify_teacher_assigned(
            teacher_id=current_user.id,
            child_id=child.id,
            activity_id=activity.id,
            note=note
        )
    except Exception:
        pass

    flash(f"Activity '{activity.title}' assigned to {child.name}.", "success")
    return redirect(url_for('teacher.student_detail', child_id=child_id))


@teacher_bp.route('/students/<int:child_id>/report/pdf')
@login_required
@role_required('teacher')
@child_access_required(write=False)
def download_pdf_report(child_id):
    child = db.session.get(Child, child_id)
    date_range = request.args.get('range', 'all')
    pdf_bytes = report_service.generate_child_pdf_report(child_id, date_range=date_range)

    safe_name = "".join(c for c in child.name if c.isalnum() or c in ('_', '-')).lower()
    filename = f"childinsight_{safe_name}_{date_range}_report.pdf"

    return Response(
        pdf_bytes,
        mimetype='application/pdf',
        headers={'Content-Disposition': f'attachment; filename="{filename}"'}
    )


@teacher_bp.route('/students/<int:child_id>/report/csv')
@login_required
@role_required('teacher')
@child_access_required(write=False)
def download_csv_report(child_id):
    child = db.session.get(Child, child_id)
    date_range = request.args.get('range', 'all')
    csv_text = report_service.generate_child_csv_report(child_id, date_range=date_range)

    safe_name = "".join(c for c in child.name if c.isalnum() or c in ('_', '-')).lower()
    filename = f"childinsight_{safe_name}_{date_range}_report.csv"

    return Response(
        csv_text,
        mimetype='text/csv; charset=utf-8',
        headers={'Content-Disposition': f'attachment; filename="{filename}"'}
    )


@teacher_bp.route('/assignments')
@login_required
@role_required('teacher')
def activity_assignments():
    assigned_children = _get_accessible_children_for_teacher(current_user.id)
    child_ids = [c.id for c in assigned_children]

    recent_assignments = []
    if child_ids:
        recent_assignments = (
            Recommendation.query.filter(Recommendation.child_id.in_(child_ids))
            .order_by(Recommendation.created_at.desc())
            .limit(30)
            .all()
        )

    activities = Activity.query.filter_by(is_active=True).order_by(Activity.title).all()

    return render_template(
        'teacher/assignments.html',
        assigned_children=assigned_children,
        recent_assignments=recent_assignments,
        activities=activities
    )


@teacher_bp.route('/access-requests/<int:access_id>/accept', methods=['POST'])
@login_required
@role_required('teacher')
def accept_access_request(access_id):
    grant = db.session.get(ChildTeacherAccess, access_id)
    if not grant or grant.teacher_id != current_user.id or grant.status != ChildTeacherAccess.STATUS_PENDING_APPROVAL:
        flash("Access request not found or already processed.", "warning")
        return redirect(url_for('teacher.dashboard'))

    grant.status = ChildTeacherAccess.STATUS_ACTIVE
    grant.responded_at = datetime.now(timezone.utc)
    db.session.commit()

    # Log action in audit log
    audit_service.log_action(
        user_id=current_user.id,
        action='teacher_accept_access_request',
        target_type='child_teacher_access',
        target_id=grant.id
    )

    # Trigger notification for parent
    try:
        from app.services import notification_service
        notification_service.notify_parent_access_response(grant, accepted=True)
    except Exception:
        pass

    child_name = grant.child.name if grant.child else "the student"
    flash(f"Access granted for {child_name}. Their profile and reports are now available in your classroom roster.", "success")
    return redirect(url_for('teacher.dashboard'))


@teacher_bp.route('/access-requests/<int:access_id>/decline', methods=['POST'])
@login_required
@role_required('teacher')
def decline_access_request(access_id):
    grant = db.session.get(ChildTeacherAccess, access_id)
    if not grant or grant.teacher_id != current_user.id or grant.status != ChildTeacherAccess.STATUS_PENDING_APPROVAL:
        flash("Access request not found or already processed.", "warning")
        return redirect(url_for('teacher.dashboard'))

    grant.status = ChildTeacherAccess.STATUS_DECLINED
    grant.responded_at = datetime.now(timezone.utc)
    db.session.commit()

    # Log action in audit log
    audit_service.log_action(
        user_id=current_user.id,
        action='teacher_decline_access_request',
        target_type='child_teacher_access',
        target_id=grant.id
    )

    # Trigger notification for parent
    try:
        from app.services import notification_service
        notification_service.notify_parent_access_response(grant, accepted=False)
    except Exception:
        pass

    child_name = grant.child.name if grant.child else "the student"
    flash(f"Access request for {child_name} declined.", "info")
    return redirect(url_for('teacher.dashboard'))

