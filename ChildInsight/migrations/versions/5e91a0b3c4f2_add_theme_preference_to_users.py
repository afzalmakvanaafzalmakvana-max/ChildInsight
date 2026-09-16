"""add theme_preference to users

Revision ID: 5e91a0b3c4f2
Revises: 40d34bbe781d
Create Date: 2026-09-12 14:57:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '5e91a0b3c4f2'
down_revision = '40d34bbe781d'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.add_column(sa.Column('theme_preference', sa.String(length=20), server_default='light', nullable=False))


def downgrade():
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.drop_column('theme_preference')
