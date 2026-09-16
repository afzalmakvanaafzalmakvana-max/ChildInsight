"""add child_teacher_access table for parent-initiated teacher access

Revision ID: 8b3e9f1a2c4d
Revises: 7d7fab82e627
Create Date: 2026-09-16 12:05:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '8b3e9f1a2c4d'
down_revision = '7d7fab82e627'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'child_teacher_access',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('child_id', sa.Integer(), nullable=False),
        sa.Column('teacher_id', sa.Integer(), nullable=True),
        sa.Column('invited_email', sa.String(length=120), nullable=False),
        sa.Column('status', sa.String(length=40), server_default='pending_teacher_approval', nullable=False),
        sa.Column('requested_by_parent_id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('responded_at', sa.DateTime(), nullable=True),
        sa.Column('revoked_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['child_id'], ['children.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['requested_by_parent_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['teacher_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('child_teacher_access', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_child_teacher_access_child_id'), ['child_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_child_teacher_access_invited_email'), ['invited_email'], unique=False)
        batch_op.create_index(batch_op.f('ix_child_teacher_access_requested_by_parent_id'), ['requested_by_parent_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_child_teacher_access_status'), ['status'], unique=False)
        batch_op.create_index(batch_op.f('ix_child_teacher_access_teacher_id'), ['teacher_id'], unique=False)


def downgrade():
    with op.batch_alter_table('child_teacher_access', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_child_teacher_access_teacher_id'))
        batch_op.drop_index(batch_op.f('ix_child_teacher_access_status'))
        batch_op.drop_index(batch_op.f('ix_child_teacher_access_requested_by_parent_id'))
        batch_op.drop_index(batch_op.f('ix_child_teacher_access_invited_email'))
        batch_op.drop_index(batch_op.f('ix_child_teacher_access_child_id'))

    op.drop_table('child_teacher_access')
