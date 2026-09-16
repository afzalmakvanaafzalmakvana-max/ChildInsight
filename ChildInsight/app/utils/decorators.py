from functools import wraps
from flask import abort, redirect, url_for, flash
from flask_login import current_user
from app import db
from app.models.child import Child
from app.models.teacher_assignment import TeacherAssignment
from app.models.child_teacher_access import ChildTeacherAccess


def role_required(*roles):
    """Restrict route access to specified roles."""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                flash('Please log in to access this page.', 'warning')
                return redirect(url_for('auth.login'))
            if current_user.role not in roles:
                abort(403)
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def child_access_required(write=False):
    """
    Enforce ownership or assignment checks for child-related operations.
    - write=True: Only the parent (or admin) can modify/delete.
    - write=False: The parent, assigned teacher, or admin can view.
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                flash('Please log in to access this page.', 'warning')
                return redirect(url_for('auth.login'))

            child_id = kwargs.get('child_id')
            if not child_id:
                abort(400)

            child = db.session.get(Child, child_id)
            if not child:
                abort(404)

            # Admins have full oversight
            if current_user.is_admin:
                return f(*args, **kwargs)

            # Write operations: strictly parents only
            if write:
                if not current_user.is_parent or child.parent_id != current_user.id:
                    abort(403)
                return f(*args, **kwargs)

            # Read operations: parent or assigned teacher
            if current_user.is_parent and child.parent_id == current_user.id:
                return f(*args, **kwargs)

            if current_user.is_teacher:
                assignment = TeacherAssignment.query.filter_by(
                    teacher_id=current_user.id,
                    child_id=child.id
                ).first()
                if assignment:
                    return f(*args, **kwargs)

                grant = ChildTeacherAccess.query.filter_by(
                    teacher_id=current_user.id,
                    child_id=child.id,
                    status=ChildTeacherAccess.STATUS_ACTIVE
                ).first()
                if grant:
                    return f(*args, **kwargs)

            abort(403)
        return decorated_function
    return decorator
