import os
import logging
from logging.handlers import RotatingFileHandler
from flask import Flask, render_template, request, flash, redirect, url_for, g
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager, current_user
from flask_wtf.csrf import CSRFProtect, CSRFError

from config import config

# Initialize extensions
db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
csrf = CSRFProtect()

login_manager.login_view = 'auth.login'
login_manager.login_message = 'Please log in to access this page.'
login_manager.login_message_category = 'info'


def create_app(config_name=None):
    """Application factory for ChildInsight."""
    if config_name is None:
        config_name = os.environ.get('FLASK_CONFIG', 'default')

    app = Flask(__name__)
    app.config.from_object(config[config_name])
    config[config_name].init_app(app)

    # Ensure database and logs directories exist
    basedir = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
    os.makedirs(os.path.join(basedir, 'database'), exist_ok=True)
    os.makedirs(os.path.join(basedir, 'logs'), exist_ok=True)

    # Configure logging
    _configure_logging(app)

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    csrf.init_app(app)

    from app.models.user import User

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    from app.routes.auth import auth_bp
    from app.routes.parent import parent_bp
    from app.routes.teacher import teacher_bp
    from app.routes.child import child_bp
    from app.routes.admin import admin_bp
    from app.routes.api import api_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(parent_bp, url_prefix='/parent')
    app.register_blueprint(teacher_bp, url_prefix='/teacher')
    app.register_blueprint(child_bp, url_prefix='/child')
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(api_bp, url_prefix='/api')
    from app.translations import translate, normalize_language

    @app.context_processor
    def inject_i18n():
        def t(key, default=None, lang=None, **kwargs):
            if not lang:
                lang = getattr(g, 'child_lang', 'en')
            return translate(key, lang=lang, default=default, **kwargs)
        return dict(t=t, normalize_language=normalize_language)


    _register_error_handlers(app)

    from app.agent.scheduler import register_cli_commands
    register_cli_commands(app)

    return app


def _configure_logging(app):
    if not app.testing:
        log_file = app.config.get('LOG_FILE')
        if log_file:
            log_dir = os.path.dirname(log_file)
            if log_dir:
                os.makedirs(log_dir, exist_ok=True)

            file_handler = RotatingFileHandler(
                log_file,
                maxBytes=10 * 1024 * 1024,
                backupCount=5,
                encoding='utf-8'
            )
            file_handler.setFormatter(logging.Formatter(
                '%(asctime)s %(levelname)s [%(name)s] %(message)s [in %(pathname)s:%(lineno)d]'
            ))
            level = getattr(logging, app.config.get('LOG_LEVEL', 'INFO').upper(), logging.INFO)
            file_handler.setLevel(level)

            if not any(isinstance(h, RotatingFileHandler) for h in app.logger.handlers):
                app.logger.addHandler(file_handler)
                app.logger.setLevel(level)


def _register_error_handlers(app):

    @app.errorhandler(CSRFError)
    def handle_csrf_error(error):
        app.logger.warning(
            f"CSRF validation failed | Path: {request.path} | Method: {request.method} | Reason: {error.description}"
        )
        if request.path in ('/login', '/auth/login') or request.endpoint == 'auth.login':
            flash('Bad Request: Your session or security token has expired. Please refresh the page and try again.', 'danger')
            from app.forms.auth import LoginForm
            form = LoginForm()
            return render_template('auth/login.html', form=form), 400
        return render_template('errors/400.html', error="Your security token has expired or is invalid. Please refresh and try again."), 400

    @app.errorhandler(400)
    def bad_request_error(error):
        return render_template('errors/400.html', error=error), 400

    @app.errorhandler(401)
    def unauthorized_error(error):
        return render_template('errors/401.html', error=error), 401

    @app.errorhandler(403)
    def forbidden_error(error):
        return render_template('errors/403.html', error=error), 403

    @app.errorhandler(404)
    def not_found_error(error):
        return render_template('errors/404.html', error=error), 404

    @app.errorhandler(500)
    def internal_server_error(error):
        user_id = getattr(current_user, 'id', 'anonymous') if current_user and current_user.is_authenticated else 'anonymous'
        app.logger.error(
            f"500 Internal Error | Path: {request.path} | Method: {request.method} | User: {user_id} | Exception: {error}",
            exc_info=True
        )
        return render_template('errors/500.html', error=error), 500
