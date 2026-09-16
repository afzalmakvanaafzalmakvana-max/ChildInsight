"""add translations_json to activities and activity_questions

Revision ID: a1b2c3d4e5f6
Revises: 9c2d1e4f5a6b
Create Date: 2026-09-16 17:20:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a1b2c3d4e5f6'
down_revision = '9c2d1e4f5a6b'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('activities', sa.Column('translations_json', sa.Text(), nullable=True))
    op.add_column('activity_questions', sa.Column('translations_json', sa.Text(), nullable=True))


def downgrade():
    op.drop_column('activity_questions', 'translations_json')
    op.drop_column('activities', 'translations_json')
