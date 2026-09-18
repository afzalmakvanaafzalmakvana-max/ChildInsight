import json
import re
from datetime import datetime, timezone
from flask import Blueprint, render_template, redirect, url_for, flash, request, session
from flask_login import login_required, current_user
from app import db
from app.models.user import User
from app.models.child import Child
from app.models.activity import Activity, Category, ActivityQuestion
from app.models.session import ActivitySession
from app.models.teacher_assignment import TeacherAssignment
from app.models.child_teacher_access import ChildTeacherAccess
from app.models.audit_log import AuditLog
from app.models.content_suggestion import ContentSuggestion
from app.forms.admin import AssignTeacherForm, ChangeRoleForm, CategoryForm, ActivityForm, QuestionForm
from app.services import audit_service
from app.utils.decorators import role_required

admin_bp = Blueprint('admin', __name__)


@admin_bp.route('/dashboard')
@login_required
@role_required('admin')
def dashboard():
    stats = {
        'total_users': User.query.count(),
        'total_parents': User.query.filter_by(role='parent').count(),
        'total_teachers': User.query.filter_by(role='teacher').count(),
        'total_children': Child.query.count(),
        'total_categories': Category.query.count(),
        'total_activities': Activity.query.count(),
        'completed_sessions': ActivitySession.query.filter_by(status=ActivitySession.STATUS_COMPLETED).count(),
        'total_sessions': ActivitySession.query.count(),
        'total_assignments': TeacherAssignment.query.count(),
        'total_audit_logs': AuditLog.query.count()
    }
    return render_template('base_admin.html', stats=stats)


@admin_bp.route('/users')
@login_required
@role_required('admin')
def users_list():
    query = User.query
    q = request.args.get('q', '').strip()
    role = request.args.get('role', '').strip()
    status = request.args.get('status', '').strip()

    if q:
        query = query.filter((User.name.ilike(f'%{q}%')) | (User.email.ilike(f'%{q}%')))
    if role and role in User.ASSIGNABLE_ROLES:
        query = query.filter_by(role=role)
    if status == 'active':
        query = query.filter_by(is_active=True)
    elif status == 'inactive':
        query = query.filter_by(is_active=False)

    users = query.order_by(User.created_at.desc()).all()
    role_form = ChangeRoleForm()
    return render_template(
        'admin/users_list.html',
        users=users,
        role_form=role_form,
        current_q=q,
        current_role=role,
        current_status=status
    )


@admin_bp.route('/users/<int:user_id>/toggle-status', methods=['POST'])
@login_required
@role_required('admin')
def user_toggle_status(user_id):
    user = db.session.get(User, user_id)
    if not user:
        flash("User not found.", "danger")
        return redirect(url_for('admin.users_list'))

    # Prevent accidental self-deactivation by current admin
    if user.id == current_user.id:
        flash("You cannot deactivate your own administrative account.", "warning")
        return redirect(url_for('admin.users_list'))

    user.is_active = not user.is_active
    db.session.commit()

    # Record action in audit log
    audit_service.log_action(
        user_id=current_user.id,
        action='toggle_user_status',
        target_type='user',
        target_id=user.id
    )

    status_str = "activated" if user.is_active else "deactivated"
    flash(f"User {user.name} ({user.email}) has been {status_str}.", "info")
    return redirect(url_for('admin.users_list'))


@admin_bp.route('/users/<int:user_id>/change-role', methods=['POST'])
@login_required
@role_required('admin')
def user_change_role(user_id):
    user = db.session.get(User, user_id)
    if not user:
        flash("User not found.", "danger")
        return redirect(url_for('admin.users_list'))

    form = ChangeRoleForm()
    if form.validate_on_submit():
        if form.role.data not in User.ASSIGNABLE_ROLES:
            flash("Invalid role submitted.", "danger")
            return redirect(url_for('admin.users_list'))

        if user.id == current_user.id and form.role.data != 'admin':
            flash("You cannot change your own role away from admin.", "warning")
            return redirect(url_for('admin.users_list'))

        old_role = user.role
        user.role = form.role.data
        db.session.commit()

        # Record action in audit log
        audit_service.log_action(
            user_id=current_user.id,
            action='change_user_role',
            target_type='user',
            target_id=user.id
        )

        flash(f"Role for {user.name} changed from {old_role} to {user.role}.", "success")
    else:
        flash("Invalid role submitted.", "danger")

    return redirect(url_for('admin.users_list'))


@admin_bp.route('/assignments', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def assignments():
    form = AssignTeacherForm()

    # Populate choices dynamically
    teachers = User.query.filter_by(role='teacher', is_active=True).order_by(User.name).all()
    children = Child.query.order_by(Child.name).all()

    form.teacher_id.choices = [(t.id, f"{t.name} ({t.email})") for t in teachers]
    form.child_id.choices = [(c.id, f"{c.name} (Parent: {c.parent.name if c.parent else 'N/A'})") for c in children]

    if form.validate_on_submit():
        teacher_id = form.teacher_id.data
        child_id = form.child_id.data

        existing = TeacherAssignment.query.filter_by(teacher_id=teacher_id, child_id=child_id).first()
        if existing:
            flash("This teacher is already assigned to that student.", "warning")
        else:
            assignment = TeacherAssignment(teacher_id=teacher_id, child_id=child_id)
            db.session.add(assignment)
            db.session.commit()

            # Record action in audit log
            audit_service.log_action(
                user_id=current_user.id,
                action='create_teacher_assignment',
                target_type='teacher_assignment',
                target_id=assignment.id
            )

            flash("Student assignment created successfully.", "success")
        return redirect(url_for('admin.assignments'))

    all_assignments = TeacherAssignment.query.order_by(TeacherAssignment.created_at.desc()).all()
    parent_grants = ChildTeacherAccess.query.order_by(ChildTeacherAccess.created_at.desc()).all()
    return render_template(
        'admin/assignments.html',
        form=form,
        assignments=all_assignments,
        parent_grants=parent_grants
    )


@admin_bp.route('/teacher-access')
@login_required
@role_required('admin')
def teacher_access_overview():
    """Direct route for reviewing all parent-granted teacher access grants."""
    return redirect(url_for('admin.assignments', _anchor='parent-grants'))


@admin_bp.route('/teacher-access/<int:access_id>/revoke', methods=['POST'])
@login_required
@role_required('admin')
def admin_revoke_teacher_access(access_id):
    """Allows administrators to revoke any parent-granted teacher access with audit logging."""
    grant = db.session.get(ChildTeacherAccess, access_id)
    if not grant:
        flash("Access record not found.", "danger")
        return redirect(url_for('admin.assignments', _anchor='parent-grants'))

    grant.status = ChildTeacherAccess.STATUS_REVOKED
    grant.revoked_at = datetime.now(timezone.utc)
    db.session.commit()

    # Log action in audit log
    audit_service.log_action(
        user_id=current_user.id,
        action='admin_revoke_parent_teacher_access',
        target_type='child_teacher_access',
        target_id=grant.id
    )

    teacher_label = grant.teacher.name if grant.teacher else grant.invited_email
    child_name = grant.child.name if grant.child else 'the student'
    flash(f"Parent-granted educator access for {teacher_label} on {child_name} has been revoked by admin.", "info")
    return redirect(url_for('admin.assignments', _anchor='parent-grants'))


@admin_bp.route('/assignments/<int:assignment_id>/delete', methods=['POST'])
@login_required
@role_required('admin')
def assignment_delete(assignment_id):
    assignment = db.session.get(TeacherAssignment, assignment_id)
    if assignment:
        db.session.delete(assignment)
        db.session.commit()

        # Record action in audit log
        audit_service.log_action(
            user_id=current_user.id,
            action='delete_teacher_assignment',
            target_type='teacher_assignment',
            target_id=assignment_id
        )

        flash("Assignment removed.", "info")
    return redirect(url_for('admin.assignments'))


@admin_bp.route('/audit-logs')
@login_required
@role_required('admin')
def audit_logs():
    """Audit log explorer for administrative and educator activities."""
    action_filter = request.args.get('action', '').strip()
    q = request.args.get('q', '').strip()

    query = AuditLog.query.join(User, AuditLog.user_id == User.id, isouter=True)

    if action_filter:
        query = query.filter(AuditLog.action == action_filter)
    if q:
        query = query.filter(
            (User.name.ilike(f'%{q}%')) |
            (User.email.ilike(f'%{q}%')) |
            (AuditLog.action.ilike(f'%{q}%')) |
            (AuditLog.target_type.ilike(f'%{q}%'))
        )

    logs = query.order_by(AuditLog.timestamp.desc()).limit(100).all()
    distinct_actions = [r[0] for r in db.session.query(AuditLog.action).distinct().all()]

    return render_template(
        'admin/audit_logs.html',
        logs=logs,
        distinct_actions=distinct_actions,
        current_action=action_filter,
        current_q=q
    )


def generate_unique_category_slug(name: str, existing_id: int | None = None) -> str:
    """Generate a clean URL-safe slug for a category, ensuring database uniqueness."""
    base_slug = re.sub(r'[^a-zA-Z0-9]+', '-', name.strip()).strip('-').lower() or 'category'
    slug = base_slug
    counter = 1
    while True:
        query = Category.query.filter_by(slug=slug)
        if existing_id:
            query = query.filter(Category.id != existing_id)
        if not query.first():
            return slug
        slug = f"{base_slug}-{counter}"
        counter += 1


@admin_bp.route('/categories')
@login_required
@role_required('admin')
def categories_list():
    """List all activity categories in a table with linked activity counts."""
    categories = Category.query.order_by(Category.name.asc()).all()
    return render_template('admin/categories_list.html', categories=categories)


@admin_bp.route('/categories/new', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def category_create():
    """Add a new activity category through a validated administrative form."""
    form = CategoryForm()
    suggestion_id = request.args.get('suggestion_id', type=int)

    # Pre-fill fields on initial GET
    if request.method == 'GET':
        if request.args.get('name'):
            form.name.data = request.args.get('name')
        if request.args.get('description'):
            form.description.data = request.args.get('description')
        if request.args.get('icon'):
            form.icon.data = request.args.get('icon')

    if form.validate_on_submit():
        name = form.name.data.strip()
        existing = Category.query.filter(Category.name.ilike(name)).first()
        if existing:
            flash(f"A category named '{name}' already exists.", "danger")
            return render_template('admin/category_form.html', form=form, title="Add Category", is_edit=False)

        slug = generate_unique_category_slug(name)
        category = Category(
            name=name,
            slug=slug,
            icon=form.icon.data.strip() if form.icon.data else '📂',
            description=form.description.data.strip() if form.description.data else None
        )
        db.session.add(category)
        db.session.commit()

        # Mark linked suggestion as approved if provided
        if suggestion_id:
            sugg = db.session.get(ContentSuggestion, suggestion_id)
            if sugg:
                sugg.status = ContentSuggestion.STATUS_APPROVED
                db.session.commit()

        audit_service.log_action(
            user_id=current_user.id,
            action='create_category',
            target_type='category',
            target_id=category.id
        )

        flash(f"Category '{category.name}' created successfully.", "success")
        return redirect(url_for('admin.categories_list'))

    return render_template('admin/category_form.html', form=form, title="Add Category", is_edit=False)


@admin_bp.route('/categories/<int:category_id>/edit', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def category_edit(category_id):
    """Edit an existing activity category's name, description, and icon."""
    category = db.session.get(Category, category_id)
    if not category:
        flash("Category not found.", "danger")
        return redirect(url_for('admin.categories_list'))

    form = CategoryForm(obj=category)
    if form.validate_on_submit():
        new_name = form.name.data.strip()
        existing = Category.query.filter(Category.name.ilike(new_name), Category.id != category.id).first()
        if existing:
            flash(f"Another category named '{new_name}' already exists.", "danger")
            return render_template('admin/category_form.html', form=form, title="Edit Category", is_edit=True, category=category)

        category.name = new_name
        category.slug = generate_unique_category_slug(new_name, existing_id=category.id)
        category.icon = form.icon.data.strip() if form.icon.data else '📂'
        category.description = form.description.data.strip() if form.description.data else None
        db.session.commit()

        audit_service.log_action(
            user_id=current_user.id,
            action='edit_category',
            target_type='category',
            target_id=category.id
        )

        flash(f"Category '{category.name}' updated successfully.", "success")
        return redirect(url_for('admin.categories_list'))

    return render_template('admin/category_form.html', form=form, title="Edit Category", is_edit=True, category=category)


@admin_bp.route('/categories/<int:category_id>/delete', methods=['POST'])
@login_required
@role_required('admin')
def category_delete(category_id):
    """Delete a category only if zero activities are linked to it."""
    category = db.session.get(Category, category_id)
    if not category:
        flash("Category not found.", "danger")
        return redirect(url_for('admin.categories_list'))

    linked_count = category.activities.count()
    if linked_count > 0:
        flash(
            f"Cannot delete category '{category.name}' because it contains {linked_count} linked "
            f"activit{'y' if linked_count == 1 else 'ies'}. "
            f"To protect educational data integrity, please remove or reassign linked activities first.",
            "warning"
        )
        return redirect(url_for('admin.categories_list'))

    cat_name = category.name
    db.session.delete(category)
    db.session.commit()

    audit_service.log_action(
        user_id=current_user.id,
        action='delete_category',
        target_type='category',
        target_id=category_id
    )

    flash(f"Category '{cat_name}' deleted successfully.", "info")
    return redirect(url_for('admin.categories_list'))


@admin_bp.route('/activities')
@login_required
@role_required('admin')
def activities_list():
    """List all educational activities with category, difficulty, question counts, and status."""
    query = Activity.query.join(Category, Activity.category_id == Category.id)

    q = request.args.get('q', '').strip()
    category_id = request.args.get('category_id', type=int)
    difficulty = request.args.get('difficulty', '').strip()
    status = request.args.get('status', '').strip()

    if q:
        query = query.filter(Activity.title.ilike(f'%{q}%'))
    if category_id:
        query = query.filter(Activity.category_id == category_id)
    if difficulty and difficulty in Activity.DIFFICULTIES:
        query = query.filter(Activity.difficulty == difficulty)
    if status == 'active':
        query = query.filter(Activity.is_active == True)
    elif status == 'inactive':
        query = query.filter(Activity.is_active == False)

    activities = query.order_by(Category.name.asc(), Activity.title.asc()).all()
    categories = Category.query.order_by(Category.name.asc()).all()

    return render_template(
        'admin/activities_list.html',
        activities=activities,
        categories=categories,
        difficulties=Activity.DIFFICULTIES,
        current_q=q,
        current_category_id=category_id,
        current_difficulty=difficulty,
        current_status=status
    )


@admin_bp.route('/activities/new', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def activity_create():
    """Create a new activity through an administrative form."""
    form = ActivityForm()
    categories = Category.query.order_by(Category.name.asc()).all()
    form.category_id.choices = [(c.id, c.name) for c in categories]
    suggestion_id = request.args.get('suggestion_id', type=int)

    # Pre-fill fields on initial GET
    if request.method == 'GET':
        cat_arg = request.args.get('category_id', type=int)
        if cat_arg and any(c.id == cat_arg for c in categories):
            form.category_id.data = cat_arg
        if request.args.get('difficulty'):
            form.difficulty.data = request.args.get('difficulty')
        if request.args.get('title'):
            form.title.data = request.args.get('title')
        if request.args.get('min_age', type=int):
            form.min_age.data = request.args.get('min_age', type=int)
        if request.args.get('max_age', type=int):
            form.max_age.data = request.args.get('max_age', type=int)
        elif request.args.get('age_band'):
            band = request.args.get('age_band').strip()
            if '-' in band:
                try:
                    parts = band.split('-')
                    form.min_age.data = int(parts[0])
                    form.max_age.data = int(parts[1])
                except (ValueError, IndexError):
                    pass

    if form.validate_on_submit():
        if form.min_age.data > form.max_age.data:
            flash("Minimum target age cannot be greater than maximum target age.", "danger")
            return render_template('admin/activity_form.html', form=form, title="Add Activity", is_edit=False)

        activity = Activity(
            category_id=form.category_id.data,
            title=form.title.data.strip(),
            description=form.description.data.strip() if form.description.data else None,
            difficulty=form.difficulty.data,
            estimated_duration=form.estimated_duration.data,
            min_age=form.min_age.data,
            max_age=form.max_age.data,
            is_active=form.is_active.data,
            is_demo=False
        )
        db.session.add(activity)
        db.session.commit()

        # Mark linked suggestion as approved if provided
        if suggestion_id:
            sugg = db.session.get(ContentSuggestion, suggestion_id)
            if sugg:
                sugg.status = ContentSuggestion.STATUS_APPROVED
                db.session.commit()

        audit_service.log_action(
            user_id=current_user.id,
            action='create_activity',
            target_type='activity',
            target_id=activity.id
        )

        flash(f"Activity '{activity.title}' created successfully! You can now add questions.", "success")
        return redirect(url_for('admin.activity_questions', activity_id=activity.id))

    return render_template('admin/activity_form.html', form=form, title="Add Activity", is_edit=False)


@admin_bp.route('/activities/<int:activity_id>/edit', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def activity_edit(activity_id):
    """Edit an existing activity's details."""
    activity = db.session.get(Activity, activity_id)
    if not activity:
        flash("Activity not found.", "danger")
        return redirect(url_for('admin.activities_list'))

    form = ActivityForm(obj=activity)
    categories = Category.query.order_by(Category.name.asc()).all()
    form.category_id.choices = [(c.id, c.name) for c in categories]

    if form.validate_on_submit():
        if form.min_age.data > form.max_age.data:
            flash("Minimum target age cannot be greater than maximum target age.", "danger")
            return render_template('admin/activity_form.html', form=form, title="Edit Activity", is_edit=True, activity=activity)

        activity.title = form.title.data.strip()
        activity.description = form.description.data.strip() if form.description.data else None
        activity.category_id = form.category_id.data
        activity.difficulty = form.difficulty.data
        activity.estimated_duration = form.estimated_duration.data
        activity.min_age = form.min_age.data
        activity.max_age = form.max_age.data
        activity.is_active = form.is_active.data
        db.session.commit()

        audit_service.log_action(
            user_id=current_user.id,
            action='edit_activity',
            target_type='activity',
            target_id=activity.id
        )

        flash(f"Activity '{activity.title}' updated successfully.", "success")
        return redirect(url_for('admin.activities_list'))

    return render_template('admin/activity_form.html', form=form, title="Edit Activity", is_edit=True, activity=activity)


@admin_bp.route('/activities/<int:activity_id>/toggle-status', methods=['POST'])
@login_required
@role_required('admin')
def activity_toggle_status(activity_id):
    """Deactivate or activate an activity (soft-delete)."""
    activity = db.session.get(Activity, activity_id)
    if not activity:
        flash("Activity not found.", "danger")
        return redirect(url_for('admin.activities_list'))

    activity.is_active = not activity.is_active
    db.session.commit()

    status_str = "activated" if activity.is_active else "deactivated"
    audit_service.log_action(
        user_id=current_user.id,
        action='toggle_activity_status',
        target_type='activity',
        target_id=activity.id
    )

    flash(f"Activity '{activity.title}' has been {status_str}.", "info")
    return redirect(url_for('admin.activities_list'))


@admin_bp.route('/activities/<int:activity_id>/delete', methods=['POST'])
@login_required
@role_required('admin')
def activity_delete(activity_id):
    """Hard-delete an activity only if zero sessions reference it."""
    activity = db.session.get(Activity, activity_id)
    if not activity:
        flash("Activity not found.", "danger")
        return redirect(url_for('admin.activities_list'))

    session_count = activity.sessions.count()
    if session_count > 0:
        flash(
            f"Cannot delete activity '{activity.title}' because it has {session_count} session record(s) attached. "
            f"To protect educational data integrity, please deactivate it instead.",
            "warning"
        )
        return redirect(url_for('admin.activities_list'))

    title = activity.title
    db.session.delete(activity)
    db.session.commit()

    audit_service.log_action(
        user_id=current_user.id,
        action='delete_activity',
        target_type='activity',
        target_id=activity_id
    )

    flash(f"Activity '{title}' deleted successfully.", "info")
    return redirect(url_for('admin.activities_list'))


# =============================================================================
# AI-ASSISTED CONTENT DRAFTING ROUTES (HUMAN-IN-THE-LOOP)
# =============================================================================

@admin_bp.route('/activities/ai-draft', methods=['GET'])
@login_required
@role_required('admin')
def activity_ai_draft_form():
    """Initial configuration screen for AI-assisted activity drafting."""
    categories = Category.query.order_by(Category.name.asc()).all()
    suggestion_id = request.args.get('suggestion_id', type=int)
    category_id = request.args.get('category_id', type=int)
    age_band = request.args.get('age_band', '6-9')
    difficulty = request.args.get('difficulty', 'Easy')

    suggestion = None
    if suggestion_id:
        suggestion = db.session.get(ContentSuggestion, suggestion_id)
        if suggestion:
            if suggestion.category_id:
                category_id = suggestion.category_id
            if suggestion.age_band:
                age_band = suggestion.age_band
            if suggestion.target_difficulty:
                difficulty = suggestion.target_difficulty

    return render_template(
        'admin/activity_draft_form.html',
        categories=categories,
        selected_category_id=category_id,
        selected_age_band=age_band,
        selected_difficulty=difficulty,
        suggestion=suggestion
    )


@admin_bp.route('/activities/ai-draft/generate', methods=['POST'])
@login_required
@role_required('admin')
def activity_ai_draft_generate():
    """Triggers ContentDraftAgent to generate a grounded activity draft (unsaved)."""
    from app.agent import content_draft_agent

    category_id = request.form.get('category_id', type=int)
    age_band = request.form.get('age_band', '6-9').strip()
    difficulty = request.form.get('difficulty', 'Easy').strip()
    custom_guidance = request.form.get('custom_guidance', '').strip() or None
    suggestion_id = request.form.get('suggestion_id', type=int)

    category = db.session.get(Category, category_id) if category_id else None
    if not category:
        flash("Please select a valid category for AI drafting.", "danger")
        return redirect(url_for('admin.activity_ai_draft_form'))

    draft = content_draft_agent.generate_draft_activity(
        category_id=category.id,
        age_band=age_band,
        difficulty=difficulty,
        custom_guidance=custom_guidance,
        suggestion_id=suggestion_id
    )

    categories = Category.query.order_by(Category.name.asc()).all()
    return render_template(
        'admin/activity_draft_review.html',
        draft=draft,
        categories=categories
    )


@admin_bp.route('/activities/ai-draft/publish', methods=['POST'])
@login_required
@role_required('admin')
def activity_ai_draft_publish():
    """
    Persists reviewed and approved AI draft to the database.
    This is the ONLY route where drafted content is committed.
    """
    category_id = request.form.get('category_id', type=int)
    title = request.form.get('title', '').strip()
    description = request.form.get('description', '').strip() or None
    difficulty = request.form.get('difficulty', 'Easy').strip()
    min_age = request.form.get('min_age', type=int)
    max_age = request.form.get('max_age', type=int)
    duration = request.form.get('estimated_duration', type=int) or 5
    suggestion_id = request.form.get('suggestion_id', type=int)

    if not title:
        flash("Activity title is required.", "danger")
        return redirect(url_for('admin.activities_list'))

    category = db.session.get(Category, category_id)
    if not category:
        flash("Invalid category selected.", "danger")
        return redirect(url_for('admin.activities_list'))

    if min_age is None or max_age is None or min_age > max_age:
        min_age, max_age = 6, 9

    # Extract questions
    questions = []
    if request.form.get('questions_json'):
        try:
            questions = json.loads(request.form.get('questions_json'))
        except (ValueError, TypeError):
            questions = []

    if not questions:
        idx = 0
        while True:
            q_text = request.form.get(f'q_text_{idx}')
            if q_text is None:
                break
            q_text = q_text.strip()
            if q_text:
                opts = [
                    request.form.get(f'q_opt_{idx}_0', '').strip(),
                    request.form.get(f'q_opt_{idx}_1', '').strip(),
                    request.form.get(f'q_opt_{idx}_2', '').strip(),
                    request.form.get(f'q_opt_{idx}_3', '').strip(),
                ]
                opts = [o for o in opts if o]
                correct_val = request.form.get(f'q_correct_{idx}', '').strip()
                if not correct_val and opts:
                    correct_val = opts[0]
                hint = request.form.get(f'q_hint_{idx}', '').strip()
                questions.append({
                    'question_text': q_text,
                    'options': opts,
                    'correct_answer': correct_val,
                    'hint': hint or None
                })
            idx += 1

    if not questions:
        flash("At least one question is required to publish an activity.", "danger")
        return redirect(url_for('admin.activities_list'))

    hi_title = request.form.get('hi_title', '').strip()
    hi_description = request.form.get('hi_description', '').strip()
    act_translations_json = None
    if hi_title:
        act_translations_json = json.dumps({
            'hi': {
                'title': hi_title,
                'description': hi_description
            }
        }, ensure_ascii=False)

    activity = Activity(
        category_id=category.id,
        title=title,
        description=description,
        difficulty=difficulty,
        estimated_duration=duration,
        min_age=min_age,
        max_age=max_age,
        translations_json=act_translations_json,
        is_active=True,
        is_demo=False
    )
    db.session.add(activity)
    db.session.flush()

    for i, q in enumerate(questions, start=1):
        opts = q.get('options', [])
        correct = q.get('correct_answer', '')
        if correct not in opts and opts:
            correct = opts[0]

        q_translations_json = None
        if q.get('translations'):
            q_translations_json = json.dumps(q['translations'], ensure_ascii=False)

        question = ActivityQuestion(
            activity_id=activity.id,
            question_text=q.get('question_text', '').strip(),
            question_type='multiple_choice',
            options_json=json.dumps(opts),
            correct_answer=correct,
            hint=q.get('hint'),
            translations_json=q_translations_json,
            order_num=i
        )
        db.session.add(question)

    # If linked to a content suggestion, mark it as approved
    if suggestion_id:
        sugg = db.session.get(ContentSuggestion, suggestion_id)
        if sugg:
            sugg.status = ContentSuggestion.STATUS_APPROVED

    db.session.commit()

    audit_service.log_action(
        user_id=current_user.id,
        action='create_activity_ai_draft',
        target_type='activity',
        target_id=activity.id
    )

    flash(f"Activity '{activity.title}' approved and published successfully with {len(questions)} questions!", "success")
    return redirect(url_for('admin.activities_list'))


@admin_bp.route('/activities/<int:activity_id>/questions')
@login_required
@role_required('admin')
def activity_questions(activity_id):
    """View and manage questions for a specific activity."""
    activity = db.session.get(Activity, activity_id)
    if not activity:
        flash("Activity not found.", "danger")
        return redirect(url_for('admin.activities_list'))

    questions = activity.questions.order_by(ActivityQuestion.order_num.asc(), ActivityQuestion.id.asc()).all()
    return render_template('admin/activity_questions.html', activity=activity, questions=questions)


@admin_bp.route('/activities/<int:activity_id>/questions/new', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def question_create(activity_id):
    """Add a new question to an activity."""
    activity = db.session.get(Activity, activity_id)
    if not activity:
        flash("Activity not found.", "danger")
        return redirect(url_for('admin.activities_list'))

    form = QuestionForm()
    if request.method == 'GET' and not form.order_num.data:
        form.order_num.data = (activity.questions.count() or 0) + 1

    if form.validate_on_submit():
        raw_options = form.options.data or ''
        options_list = [opt.strip() for opt in raw_options.splitlines() if opt.strip()]
        if len(options_list) < 2 and ',' in raw_options:
            options_list = [opt.strip() for opt in raw_options.split(',') if opt.strip()]

        if len(options_list) < 2:
            flash("Please provide at least two choices/options (one per line).", "danger")
            return render_template('admin/question_form.html', form=form, activity=activity, title="Add Question", is_edit=False)

        correct_ans = form.correct_answer.data.strip()
        if correct_ans not in options_list:
            flash(f"The correct answer '{correct_ans}' must exactly match one of the choices: {', '.join(options_list)}", "danger")
            return render_template('admin/question_form.html', form=form, activity=activity, title="Add Question", is_edit=False)

        question = ActivityQuestion(
            activity_id=activity.id,
            question_text=form.question_text.data.strip(),
            question_type=form.question_type.data,
            options_json=json.dumps(options_list),
            correct_answer=correct_ans,
            hint=form.hint.data.strip() if form.hint.data else None,
            order_num=form.order_num.data
        )
        db.session.add(question)
        db.session.commit()

        audit_service.log_action(
            user_id=current_user.id,
            action='create_question',
            target_type='question',
            target_id=question.id
        )

        flash(f"Question #{question.order_num} added to '{activity.title}'.", "success")
        return redirect(url_for('admin.activity_questions', activity_id=activity.id))

    return render_template('admin/question_form.html', form=form, activity=activity, title="Add Question", is_edit=False)


@admin_bp.route('/activities/<int:activity_id>/questions/<int:question_id>/edit', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def question_edit(activity_id, question_id):
    """Edit an existing activity question."""
    activity = db.session.get(Activity, activity_id)
    if not activity:
        flash("Activity not found.", "danger")
        return redirect(url_for('admin.activities_list'))

    question = db.session.get(ActivityQuestion, question_id)
    if not question or question.activity_id != activity.id:
        flash("Question not found.", "danger")
        return redirect(url_for('admin.activity_questions', activity_id=activity.id))

    form = QuestionForm(obj=question)
    if request.method == 'GET':
        form.options.data = "\n".join(question.options)

    if form.validate_on_submit():
        raw_options = form.options.data or ''
        options_list = [opt.strip() for opt in raw_options.splitlines() if opt.strip()]
        if len(options_list) < 2 and ',' in raw_options:
            options_list = [opt.strip() for opt in raw_options.split(',') if opt.strip()]

        if len(options_list) < 2:
            flash("Please provide at least two choices/options (one per line).", "danger")
            return render_template('admin/question_form.html', form=form, activity=activity, question=question, title="Edit Question", is_edit=True)

        correct_ans = form.correct_answer.data.strip()
        if correct_ans not in options_list:
            flash(f"The correct answer '{correct_ans}' must exactly match one of the choices: {', '.join(options_list)}", "danger")
            return render_template('admin/question_form.html', form=form, activity=activity, question=question, title="Edit Question", is_edit=True)

        question.question_text = form.question_text.data.strip()
        question.question_type = form.question_type.data
        question.options_json = json.dumps(options_list)
        question.correct_answer = correct_ans
        question.hint = form.hint.data.strip() if form.hint.data else None
        question.order_num = form.order_num.data
        db.session.commit()

        audit_service.log_action(
            user_id=current_user.id,
            action='edit_question',
            target_type='question',
            target_id=question.id
        )

        flash(f"Question #{question.order_num} updated successfully.", "success")
        return redirect(url_for('admin.activity_questions', activity_id=activity.id))

    return render_template('admin/question_form.html', form=form, activity=activity, question=question, title="Edit Question", is_edit=True)


@admin_bp.route('/activities/<int:activity_id>/questions/<int:question_id>/delete', methods=['POST'])
@login_required
@role_required('admin')
def question_delete(activity_id, question_id):
    """Delete a question from an activity."""
    activity = db.session.get(Activity, activity_id)
    if not activity:
        flash("Activity not found.", "danger")
        return redirect(url_for('admin.activities_list'))

    question = db.session.get(ActivityQuestion, question_id)
    if not question or question.activity_id != activity.id:
        flash("Question not found.", "danger")
        return redirect(url_for('admin.activity_questions', activity_id=activity.id))

    db.session.delete(question)
    db.session.commit()

    audit_service.log_action(
        user_id=current_user.id,
        action='delete_question',
        target_type='question',
        target_id=question_id
    )

    flash("Question removed from activity.", "info")
    return redirect(url_for('admin.activity_questions', activity_id=activity.id))


@admin_bp.route('/agents')
@login_required
@role_required('admin')
def agents_dashboard():
    """System Agents read-only status, health telemetry, and orchestrator action center."""
    from app.agent import scheduler, health_agent, content_integrity_agent, compliance_agent, orchestrator_agent

    dismissed_keys = set(session.get('orchestrator_dismissed_keys', []))
    all_action_items = orchestrator_agent.get_action_items(dismissed_keys=dismissed_keys)
    action_items = [i for i in all_action_items if not i.get('is_dismissed')]
    dismissed_count = len(all_action_items) - len(action_items)

    last_run = scheduler.get_last_run_status()
    health_metrics = health_agent.compute_health_metrics()
    health_snapshots = health_agent.get_health_trend(limit=15)
    integrity_issues = content_integrity_agent.run_audit()
    recent_incidents_count = compliance_agent.get_recent_incident_count(since_hours=24)
    recent_incidents = compliance_agent.get_recent_incidents_summary(limit=10)

    trend_labels = [s.created_at.strftime('%m/%d %H:%M') for s in health_snapshots]
    trend_scores = [round(s.score, 1) for s in health_snapshots]

    # If no snapshots exist yet, initialize with the current computed score
    if not trend_labels:
        from datetime import datetime, timezone
        trend_labels = [datetime.now(timezone.utc).strftime('%m/%d %H:%M')]
        trend_scores = [health_metrics['score']]

    return render_template(
        'admin/agents.html',
        action_items=action_items,
        dismissed_count=dismissed_count,
        last_run=last_run,
        health_metrics=health_metrics,
        trend_labels_json=json.dumps(trend_labels),
        trend_scores_json=json.dumps(trend_scores),
        integrity_issues=integrity_issues,
        recent_incidents_count=recent_incidents_count,
        recent_incidents=recent_incidents
    )


@admin_bp.route('/agents/run', methods=['POST'])
@login_required
@role_required('admin')
def run_agents_pipeline():
    """Triggers the internal maintenance agent pipeline from admin UI."""
    from app.agent import scheduler

    result = scheduler.run_maintenance_pipeline(triggered_by='admin_ui')

    audit_service.log_action(
        user_id=current_user.id,
        action='run_agents_pipeline',
        target_type='system_agents',
        target_id=None
    )

    if result['status'] == 'skipped':
        flash("Maintenance run was skipped because another run is already in progress.", "warning")
    elif result['status'] == 'partial_failure':
        flash("Agent pipeline executed with one or more step warnings. Check step status below.", "warning")
    else:
        flash(f"Agent pipeline executed successfully (Score: {result.get('health_score')}/100 in {result.get('duration_seconds')}s).", "success")

    return redirect(url_for('admin.agents_dashboard'))


@admin_bp.route('/action-center')
@login_required
@role_required('admin')
def action_center():
    """Route alias to the Orchestrator Action Center on the System Agents dashboard."""
    return redirect(url_for('admin.agents_dashboard') + '#action-center')


@admin_bp.route('/action-center/dismiss', methods=['POST'])
@login_required
@role_required('admin')
def action_center_dismiss():
    """Dismisses an action item from the orchestrator view (decluttering only; zero database mutations)."""
    from app.agent import orchestrator_agent
    item_key = request.form.get('item_key', '').strip()
    if item_key:
        dismissed = set(session.get('orchestrator_dismissed_keys', []))
        dismissed.add(item_key)
        session['orchestrator_dismissed_keys'] = list(dismissed)
        orchestrator_agent.dismiss_action_item(item_key)
        flash("Item dismissed from Action Center view.", "info")
    return redirect(url_for('admin.agents_dashboard') + '#action-center')


@admin_bp.route('/action-center/restore', methods=['POST'])
@login_required
@role_required('admin')
def action_center_restore():
    """Restores all dismissed action items back into the orchestrator view."""
    from app.agent import orchestrator_agent
    session.pop('orchestrator_dismissed_keys', None)
    orchestrator_agent.clear_dismissed_items()
    flash("All dismissed items restored to Action Center view.", "success")
    return redirect(url_for('admin.agents_dashboard') + '#action-center')


# =============================================================================
# ADAPTIVE CONTENT SUGGESTIONS ROUTES
# =============================================================================

@admin_bp.route('/content-suggestions')
@login_required
@role_required('admin')
def content_suggestions():
    """Adaptive Content Suggestions dashboard reviewing automated gap analysis."""
    status_filter = request.args.get('status', 'all').strip().lower()
    query = ContentSuggestion.query.order_by(
        ContentSuggestion.priority_score.desc(),
        ContentSuggestion.created_at.desc()
    )

    if status_filter in (ContentSuggestion.STATUS_PENDING, ContentSuggestion.STATUS_APPROVED, ContentSuggestion.STATUS_DISMISSED):
        query = query.filter(ContentSuggestion.status == status_filter)

    suggestions = query.all()

    pending_count = ContentSuggestion.query.filter_by(status=ContentSuggestion.STATUS_PENDING).count()
    approved_count = ContentSuggestion.query.filter_by(status=ContentSuggestion.STATUS_APPROVED).count()
    dismissed_count = ContentSuggestion.query.filter_by(status=ContentSuggestion.STATUS_DISMISSED).count()
    total_count = ContentSuggestion.query.count()

    return render_template(
        'admin/content_suggestions.html',
        suggestions=suggestions,
        current_status=status_filter,
        pending_count=pending_count,
        approved_count=approved_count,
        dismissed_count=dismissed_count,
        total_count=total_count
    )


@admin_bp.route('/content-suggestions/<int:suggestion_id>/dismiss', methods=['POST'])
@login_required
@role_required('admin')
def content_suggestion_dismiss(suggestion_id):
    """Mark a content suggestion as dismissed without action."""
    suggestion = db.session.get(ContentSuggestion, suggestion_id)
    if not suggestion:
        flash("Suggestion not found.", "danger")
        return redirect(url_for('admin.content_suggestions'))

    suggestion.status = ContentSuggestion.STATUS_DISMISSED
    db.session.commit()

    audit_service.log_action(
        user_id=current_user.id,
        action='dismiss_content_suggestion',
        target_type='content_suggestion',
        target_id=suggestion_id
    )

    flash("Content suggestion dismissed.", "info")
    return redirect(url_for('admin.content_suggestions'))


@admin_bp.route('/content-suggestions/run', methods=['POST'])
@login_required
@role_required('admin')
def content_suggestions_run():
    """Manually trigger Adaptive Content Suggestion analysis."""
    from app.agent import content_suggestion_agent
    try:
        new_suggestions = content_suggestion_agent.generate_suggestions(persist=True)
        flash(f"Content gap analysis complete: {len(new_suggestions)} active suggestion(s) evaluated.", "success")
    except Exception as e:
        flash(f"Error analyzing content gaps: {str(e)}", "danger")
    return redirect(url_for('admin.content_suggestions'))

