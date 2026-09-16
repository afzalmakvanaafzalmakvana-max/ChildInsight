from app.routes.auth import auth_bp
from app.routes.parent import parent_bp
from app.routes.teacher import teacher_bp
from app.routes.child import child_bp
from app.routes.admin import admin_bp
from app.routes.api import api_bp

__all__ = [
    'auth_bp',
    'parent_bp',
    'teacher_bp',
    'child_bp',
    'admin_bp',
    'api_bp'
]
