from datetime import datetime, timezone
from flask import Blueprint, render_template, redirect, url_for, flash, request, Response, abort
from flask_login import login_required, current_user
from app import db
from app.models.user import User
from app.models.child import Child
from app.models.session import ActivitySession
from app.models.child_teacher_access import ChildTeacherAccess
from app.forms.child import ChildForm
from app.utils.decorators import role_required, child_access_required
from app.services import analytics_service, recommendation_service, profile_service, report_service, audit_service

parent_bp = Blueprint('parent', __name__)


def _prepare_dashboard_data(child):
    """Assembles all data payloads needed for displaying a child's interactive dashboard."""
    if not child:
        return None

    snapshot = analytics_service.get_child_analytics_snapshot(child.id)
    recommendations = recommendation_service.get_recommendations_for_child(child.id, persist=True)
    pattern_profile = profile_service.get_child_learning_pattern_observation(child.id)
    recent_sessions = (
        ActivitySession.query.filter_by(child_id=child.id)
        .order_by(ActivitySession.start_time.desc())
        .limit(8)
        .all()
    )

    # Category chart data for Chart.js
    category_breakdown = snapshot.get('category_breakdown', {})
    category_labels = [c.get('name', k.capitalize()) for k, c in category_breakdown.items()]
    category_accuracies = [round(c.get('accuracy', 0.0), 1) for k, c in category_breakdown.items()]

    # Trend line chart data (chronological order of last 10 completed sessions)
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

    # Strengths and Practice Opportunities
    categories_sorted = sorted(
        category_breakdown.values(),
        key=lambda c: c.get('accuracy', 0.0),
        reverse=True
    )
    strengths = [c for c in categories_sorted if c.get('accuracy', 0.0) >= 70.0 and c.get('sessions_count', 0) > 0]
    practice_areas = [c for c in categories_sorted if c.get('accuracy', 0.0) < 60.0 or c.get('sessions_count', 0) == 0]

    return {
        'snapshot': snapshot,
        'recommendations': recommendations,
        'pattern_profile': pattern_profile,
        'recent_sessions': recent_sessions,
        'category_labels': category_labels,
        'category_accuracies': category_accuracies,
        'trend_labels': trend_labels,
        'trend_accuracies': trend_accuracies,
        'strengths': strengths,
        'practice_areas': practice_areas
    }


@parent_bp.route('/dashboard')
@login_required
@role_required('parent')
def dashboard():
    children = Child.query.filter_by(parent_id=current_user.id).order_by(Child.created_at.asc()).all()
    selected_child_id = request.args.get('child_id', type=int)

    selected_child = None
    if children:
        if selected_child_id:
            selected_child = next((c for c in children if c.id == selected_child_id), children[0])
        else:
            selected_child = children[0]

    dash_data = _prepare_dashboard_data(selected_child)

    return render_template(
        'parent/dashboard.html',
        children=children,
        selected_child=selected_child,
        dash_data=dash_data
    )


@parent_bp.route('/children')
@login_required
@role_required('parent')
def children_list():
    children = Child.query.filter_by(parent_id=current_user.id).order_by(Child.created_at.desc()).all()
    return render_template('parent/children_list.html', children=children)


@parent_bp.route('/children/new', methods=['GET', 'POST'])
@login_required
@role_required('parent')
def child_new():
    form = ChildForm()
    if form.validate_on_submit():
        child = Child(
            parent_id=current_user.id,
            name=form.name.data.strip(),
            age=form.age.data,
            grade=form.grade.data if form.grade.data else None,
            preferred_language=form.preferred_language.data
        )
        db.session.add(child)
        db.session.commit()
        flash(f"Profile for {child.name} created successfully.", "success")
        return redirect(url_for('parent.dashboard', child_id=child.id))

    return render_template('parent/child_form.html', form=form, title="Add Child Profile")


@parent_bp.route('/children/<int:child_id>')
@login_required
@role_required('parent')
@child_access_required(write=False)
def child_detail(child_id):
    child = db.session.get(Child, child_id)
    dash_data = _prepare_dashboard_data(child)
    active_grants = ChildTeacherAccess.query.filter_by(
        child_id=child.id,
        status=ChildTeacherAccess.STATUS_ACTIVE
    ).order_by(ChildTeacherAccess.created_at.desc()).all()
    pending_grants = ChildTeacherAccess.query.filter(
        ChildTeacherAccess.child_id == child.id,
        ChildTeacherAccess.status.in_([
            ChildTeacherAccess.STATUS_PENDING_APPROVAL,
            ChildTeacherAccess.STATUS_PENDING_VERIFICATION
        ])
    ).order_by(ChildTeacherAccess.created_at.desc()).all()
    return render_template(
        'parent/child_detail.html',
        child=child,
        dash_data=dash_data,
        active_grants=active_grants,
        pending_grants=pending_grants
    )


@parent_bp.route('/children/<int:child_id>/share')
@login_required
@role_required('parent')
@child_access_required(write=False)
def child_share(child_id):
    """Direct route alias for the share-with-teacher flow for a specific child."""
    return redirect(url_for('parent.child_detail', child_id=child_id, _anchor='share-with-teacher'))


@parent_bp.route('/children/<int:child_id>/share-teacher', methods=['POST'])
@login_required
@role_required('parent')
@child_access_required(write=True)
def share_child_teacher(child_id):
    child = db.session.get(Child, child_id)
    teacher_email = request.form.get('teacher_email', '').strip().lower()

    if not teacher_email:
        flash("Please enter a valid teacher email address.", "warning")
        return redirect(url_for('parent.child_detail', child_id=child_id, _anchor='share-with-teacher'))

    # Check: does a user with this email exist AND have role='teacher' AND is_active=True?
    teacher = User.query.filter_by(email=teacher_email).first()
    if not teacher or teacher.role != 'teacher' or not teacher.is_active:
        # Security requirement: do NOT reveal whether email exists for a different role
        flash("No active teacher account found with this email.", "danger")
        return redirect(url_for('parent.child_detail', child_id=child_id, _anchor='share-with-teacher'))

    # Check if this teacher already has active access
    existing_active = ChildTeacherAccess.query.filter_by(
        child_id=child.id,
        teacher_id=teacher.id,
        status=ChildTeacherAccess.STATUS_ACTIVE
    ).first()
    if existing_active:
        flash(f"{teacher.name} already has active access to {child.name}'s profile.", "info")
        return redirect(url_for('parent.child_detail', child_id=child_id, _anchor='share-with-teacher'))

    # Rate-limit / anti-spam: check if an invite is already pending for this child + teacher
    existing_pending = ChildTeacherAccess.query.filter(
        ChildTeacherAccess.child_id == child.id,
        (ChildTeacherAccess.teacher_id == teacher.id) | (ChildTeacherAccess.invited_email == teacher_email),
        ChildTeacherAccess.status.in_([
            ChildTeacherAccess.STATUS_PENDING_APPROVAL,
            ChildTeacherAccess.STATUS_PENDING_VERIFICATION
        ])
    ).first()
    if existing_pending:
        flash(f"An access request for {teacher.name} is already pending approval.", "warning")
        return redirect(url_for('parent.child_detail', child_id=child_id, _anchor='share-with-teacher'))

    # Create access grant row
    grant = ChildTeacherAccess(
        child_id=child.id,
        teacher_id=teacher.id,
        invited_email=teacher_email,
        status=ChildTeacherAccess.STATUS_PENDING_APPROVAL,
        requested_by_parent_id=current_user.id
    )
    db.session.add(grant)
    db.session.commit()

    # Log audit entry
    audit_service.log_action(
        user_id=current_user.id,
        action='parent_grant_teacher_access_invite',
        target_type='child_teacher_access',
        target_id=grant.id
    )

    # Notify teacher
    try:
        from app.services import notification_service
        notification_service.notify_teacher_access_request(current_user, teacher, child)
    except Exception:
        pass

    flash(f"Access request sent to {teacher.name}. They will receive a notification to review and approve access.", "success")
    return redirect(url_for('parent.child_detail', child_id=child_id, _anchor='share-with-teacher'))


@parent_bp.route('/children/<int:child_id>/teacher-access/<int:access_id>/revoke', methods=['POST'])
@login_required
@role_required('parent')
@child_access_required(write=True)
def revoke_teacher_access(child_id, access_id):
    child = db.session.get(Child, child_id)
    grant = db.session.get(ChildTeacherAccess, access_id)

    if not grant or grant.child_id != child.id or grant.requested_by_parent_id != current_user.id:
        flash("Access record not found or unauthorized.", "danger")
        return redirect(url_for('parent.child_detail', child_id=child_id, _anchor='share-with-teacher'))

    teacher_name = grant.teacher.name if grant.teacher else grant.invited_email
    grant.status = ChildTeacherAccess.STATUS_REVOKED
    grant.revoked_at = datetime.now(timezone.utc)
    db.session.commit()

    # Log audit entry
    audit_service.log_action(
        user_id=current_user.id,
        action='parent_revoke_teacher_access',
        target_type='child_teacher_access',
        target_id=grant.id
    )

    if grant.teacher:
        try:
            from app.services import notification_service
            notification_service.notify_teacher_access_revoked(grant.teacher, child)
        except Exception:
            pass

    flash(f"Access for {teacher_name} has been revoked.", "info")
    return redirect(url_for('parent.child_detail', child_id=child_id, _anchor='share-with-teacher'))


@parent_bp.route('/children/<int:child_id>/edit', methods=['GET', 'POST'])
@login_required
@role_required('parent')
@child_access_required(write=True)
def child_edit(child_id):
    child = db.session.get(Child, child_id)
    form = ChildForm(obj=child)

    if form.validate_on_submit():
        child.name = form.name.data.strip()
        child.age = form.age.data
        child.grade = form.grade.data if form.grade.data else None
        child.preferred_language = form.preferred_language.data
        db.session.commit()
        flash(f"Profile for {child.name} updated.", "success")
        return redirect(url_for('parent.child_detail', child_id=child.id))

    return render_template('parent/child_form.html', form=form, title=f"Edit {child.name}'s Profile", child=child)


@parent_bp.route('/children/<int:child_id>/delete', methods=['POST'])
@login_required
@role_required('parent')
@child_access_required(write=True)
def child_delete(child_id):
    child = db.session.get(Child, child_id)
    child_name = child.name
    db.session.delete(child)
    db.session.commit()
    flash(f"Profile for {child_name} deleted.", "info")
    return redirect(url_for('parent.children_list'))


@parent_bp.route('/children/<int:child_id>/report/pdf')
@login_required
@role_required('parent')
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
        headers={
            'Content-Disposition': f'attachment; filename="{filename}"'
        }
    )


@parent_bp.route('/children/<int:child_id>/report/csv')
@login_required
@role_required('parent')
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
        headers={
            'Content-Disposition': f'attachment; filename="{filename}"'
        }
    )


@parent_bp.route('/progress')
@parent_bp.route('/progress-reports')
@login_required
@role_required('parent')
def progress_reports():
    children = Child.query.filter_by(parent_id=current_user.id).order_by(Child.created_at.asc()).all()
    selected_child_id = request.args.get('child_id', type=int)

    selected_child = None
    if selected_child_id:
        selected_child = db.session.get(Child, selected_child_id)
        if not selected_child or selected_child.parent_id != current_user.id:
            abort(403)
    elif children:
        selected_child = children[0]

    dash_data = _prepare_dashboard_data(selected_child) if selected_child else None

    return render_template(
        'parent/progress_reports.html',
        children=children,
        selected_child=selected_child,
        dash_data=dash_data
    )


@parent_bp.route('/recommendations')
@login_required
@role_required('parent')
def recommendations():
    children = Child.query.filter_by(parent_id=current_user.id).order_by(Child.created_at.asc()).all()
    selected_child_id = request.args.get('child_id', type=int)

    selected_child = None
    if selected_child_id:
        selected_child = db.session.get(Child, selected_child_id)
        if not selected_child or selected_child.parent_id != current_user.id:
            abort(403)
    elif children:
        selected_child = children[0]

    recommendations_list = []
    pattern_profile = None
    if selected_child:
        recommendations_list = recommendation_service.get_recommendations_for_child(selected_child.id, persist=True)
        pattern_profile = profile_service.get_child_learning_pattern_observation(selected_child.id)

    return render_template(
        'parent/recommendations.html',
        children=children,
        selected_child=selected_child,
        recommendations=recommendations_list,
        pattern_profile=pattern_profile
    )
