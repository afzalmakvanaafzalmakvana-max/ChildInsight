"""add translations_json to categories

Revision ID: c5e6f7a8b9c0
Revises: a1b2c3d4e5f6
Create Date: 2026-09-18 16:40:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c5e6f7a8b9c0'
down_revision = 'a1b2c3d4e5f6'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('categories', sa.Column('translations_json', sa.Text(), nullable=True))


def downgrade():
    op.drop_column('categories', 'translations_json')
