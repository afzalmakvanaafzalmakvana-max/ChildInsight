"""verify no child user roles and enforce valid user roles

Revision ID: 9c2d1e4f5a6b
Revises: 8b3e9f1a2c4d
Create Date: 2026-09-16 17:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '9c2d1e4f5a6b'
down_revision = '8b3e9f1a2c4d'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    result = bind.execute(sa.text("SELECT count(*) FROM users WHERE role = 'child'")).scalar()
    if result and result > 0:
        raise ValueError(
            f"Found {result} user(s) with role='child'. ChildInsight represents children "
            f"exclusively via the separate Child model (linked to a parent's User account) "
            f"with no standalone User login. Please resolve before running migrations."
        )


def downgrade():
    pass
