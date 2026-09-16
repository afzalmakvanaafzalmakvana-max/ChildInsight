import os
from dotenv import load_dotenv

basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, '.env'))


class Config:
    """Base configuration class with common settings."""
    SECRET_KEY = os.environ.get('SECRET_KEY', 'default-dev-secret-key-change-in-prod')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    WTF_CSRF_ENABLED = True
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
    LOG_FILE = os.environ.get('LOG_FILE', os.path.join(basedir, 'logs', 'childinsight.log'))

    @staticmethod
    def init_app(app):
        """Hook for initializing app with specific configuration."""
        pass


class DevelopmentConfig(Config):
    """Development environment configuration."""
    DEBUG = True
    _env_db = os.environ.get('DATABASE_URL')
    if _env_db and _env_db.startswith('sqlite:///'):
        _sqlite_file = _env_db.replace('sqlite:///', '')
        if not os.path.isabs(_sqlite_file):
            _sqlite_file = os.path.abspath(os.path.join(basedir, _sqlite_file))
        SQLALCHEMY_DATABASE_URI = f"sqlite:///{_sqlite_file.replace(os.sep, '/')}"
    elif not _env_db:
        _db_path = os.path.join(basedir, 'database', 'childinsight_dev.db')
        SQLALCHEMY_DATABASE_URI = f"sqlite:///{_db_path.replace(os.sep, '/')}"
    else:
        SQLALCHEMY_DATABASE_URI = _env_db


class TestingConfig(Config):
    """Testing environment configuration."""
    TESTING = True
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False


class ProductionConfig(Config):
    """Production environment configuration with strict security defaults."""
    DEBUG = False
    TESTING = False

    # Production Secret Key
    SECRET_KEY = os.environ.get('SECRET_KEY')

    # Secure Cookie Settings for HTTPS
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    REMEMBER_COOKIE_SECURE = True
    REMEMBER_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_SAMESITE = 'Lax'

    # Database Configuration (supports postgres:// to postgresql:// fix for PaaS providers)
    _raw_db = os.environ.get('DATABASE_URL')
    if _raw_db and _raw_db.startswith('postgres://'):
        _raw_db = _raw_db.replace('postgres://', 'postgresql://', 1)
    SQLALCHEMY_DATABASE_URI = _raw_db

    @classmethod
    def init_app(cls, app):
        Config.init_app(app)
        if not os.environ.get('SECRET_KEY'):
            raise ValueError("CRITICAL: Production configuration requires SECRET_KEY environment variable to be set.")
        if not os.environ.get('DATABASE_URL'):
            raise ValueError("CRITICAL: Production configuration requires DATABASE_URL environment variable to be set.")

        # Enable ProxyFix to handle X-Forwarded-For and X-Forwarded-Proto from reverse proxies (Nginx, PaaS)
        try:
            from werkzeug.middleware.proxy_fix import ProxyFix
            app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)
        except ImportError:
            pass


config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}

