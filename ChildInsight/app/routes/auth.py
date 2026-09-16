from urllib.parse import urlparse
from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import login_user, logout_user, login_required, current_user
from app import db
from app.models.user import User
from app.models.password_reset_token import PasswordResetToken
from app.forms.auth import LoginForm, RegisterForm, ForgotPasswordRequestForm, ResetPasswordForm

auth_bp = Blueprint('auth', __name__)


def is_safe_redirect_url(target: str, user_role: str = None) -> bool:
    """
    Validate that a redirect target URL belongs to the same host,
    does not cause auth loops or unwanted logouts, and is appropriate for the user's role.
    """
    if not target:
        return False
    ref_url = urlparse(request.host_url)
    test_url = urlparse(target)
    
    # Must be relative or match current host
    is_same_host = test_url.scheme in ('', 'http', 'https') and (
        test_url.netloc == '' or test_url.netloc == ref_url.netloc
    )
    if not is_same_host:
        return False

    path = test_url.path or ''
    # Normalize path (remove trailing slash for comparison if not root)
    norm_path = path.rstrip('/') if len(path) > 1 else path

    # Disallow auth entry/exit endpoints to prevent redirect loops or instant logouts
    if norm_path in ('/login', '/auth/login', '/logout', '/auth/logout'):
        return False

    # Check role compatibility if role is provided
    if user_role:
        if norm_path.startswith('/admin') and user_role != 'admin':
            return False
        if norm_path.startswith('/teacher') and user_role not in ('teacher', 'admin'):
            return False
        if norm_path.startswith('/parent') and user_role not in ('parent', 'admin'):
            return False

    return True


def get_role_dashboard_url(role: str) -> str:
    """Return the default landing dashboard URL for a given role."""
    if role == 'parent':
        return url_for('parent.dashboard')
    elif role == 'teacher':
        return url_for('teacher.dashboard')
    elif role == 'admin':
        return url_for('admin.dashboard')
    elif role == 'child':
        return url_for('child.home')
    return url_for('auth.index')


@auth_bp.route('/')
def index():
    return render_template('index.html')


@auth_bp.route('/login', methods=['GET', 'POST'])
@auth_bp.route('/auth/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated and request.method == 'GET':
        return redirect(get_role_dashboard_url(current_user.role))

    form = LoginForm()

    # Pre-populate next in form if provided in GET request
    if request.method == 'GET' and request.args.get('next'):
        form.next.data = request.args.get('next')

    if form.validate_on_submit():
        normalized_email = form.email.data.strip().lower()
        user = User.query.filter_by(email=normalized_email).first()

        if user and user.check_password(form.password.data):
            if not user.is_active:
                flash('Your account has been deactivated. Please contact support or an administrator.', 'danger')
                return render_template('auth/login.html', form=form), 403

            if current_user.is_authenticated:
                logout_user()

            login_user(user, remember=form.remember_me.data)
            flash(f'Welcome back, {user.name}!', 'success')

            # Retrieve next target from form field, query args, or form post data
            next_page = form.next.data or request.args.get('next') or request.form.get('next')
            if next_page and is_safe_redirect_url(next_page, user_role=user.role):
                return redirect(next_page)
            return redirect(get_role_dashboard_url(user.role))
        else:
            flash('Invalid email address or password. Please try again.', 'danger')
            return render_template('auth/login.html', form=form)

    elif request.method == 'POST':
        # form.validate_on_submit() returned False
        if hasattr(form, 'csrf_token') and form.csrf_token.errors:
            for error in form.csrf_token.errors:
                msg = error if 'expired' in str(error).lower() else 'Your session or security token has expired. Please refresh the page and try again.'
                flash(msg, 'danger')
        elif form.email.errors:
            flash(form.email.errors[0], 'danger')
        elif form.password.errors:
            flash(form.password.errors[0], 'danger')
        else:
            flash('Please check the form for errors and try again.', 'danger')

    return render_template('auth/login.html', form=form)


@auth_bp.route('/register', methods=['GET', 'POST'])
@auth_bp.route('/auth/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(get_role_dashboard_url(current_user.role))

    form = RegisterForm()
    if form.validate_on_submit():
        user = User(
            name=form.name.data.strip(),
            email=form.email.data.strip().lower(),
            role=form.role.data
        )
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()

        flash('Your account has been created successfully! Please sign in.', 'success')
        return redirect(url_for('auth.login'))

    return render_template('auth/register.html', form=form)


@auth_bp.route('/logout')
@auth_bp.route('/auth/logout')
@login_required
def logout():
    logout_user()
    flash('You have been signed out successfully.', 'info')
    return redirect(url_for('auth.index'))


@auth_bp.route('/forgot-password', methods=['GET', 'POST'])
@auth_bp.route('/auth/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if current_user.is_authenticated:
        return redirect(get_role_dashboard_url(current_user.role))

    form = ForgotPasswordRequestForm()
    demo_reset_url = None

    if form.validate_on_submit():
        normalized_email = form.email.data.strip().lower()
        user = User.query.filter_by(email=normalized_email).first()

        if user and user.is_active:
            # Invalidate any existing unused reset tokens for this user
            for old_token in PasswordResetToken.query.filter_by(user_id=user.id, used_at=None).all():
                old_token.mark_used()

            token_record, raw_token = PasswordResetToken.create_token(user, expires_in_minutes=30)
            db.session.commit()

            demo_reset_url = url_for('auth.reset_password', token=raw_token, _external=True)
            current_app.logger.info(f"DEMO MODE: Password reset link generated for {user.email}: {demo_reset_url}")

        flash("If an account exists for this email address, password reset instructions have been generated.", "info")

    return render_template('auth/forgot_password.html', form=form, demo_reset_url=demo_reset_url)


@auth_bp.route('/reset-password/<token>', methods=['GET', 'POST'])
@auth_bp.route('/auth/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    if current_user.is_authenticated:
        return redirect(get_role_dashboard_url(current_user.role))

    is_valid, reason, token_record = PasswordResetToken.verify_token(token)
    if not is_valid:
        flash("This password reset link is invalid or has expired. Please request a new one.", "danger")
        return redirect(url_for('auth.forgot_password'))

    form = ResetPasswordForm()
    if form.validate_on_submit():
        user = token_record.user
        user.set_password(form.password.data)
        token_record.mark_used()

        try:
            from app.services.audit_service import log_action
            log_action(user_id=user.id, action='password_reset_completed', target_type='user', target_id=user.id)
        except Exception:
            pass

        db.session.commit()
        flash("Your password has been reset successfully! Please sign in with your new password.", "success")
        return redirect(url_for('auth.login'))

    return render_template('auth/reset_password.html', form=form, token=token)
