"""Add per-project suggestions.

Revision ID: 0003_suggestions
Revises: 0002_repository_url
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = '0003_suggestions'
down_revision: Union[str, None] = '0002_repository_url'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'suggestions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('project_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('title', sa.String(length=200), nullable=False),
        sa.Column('body', sa.Text(), nullable=True),
        sa.Column('status', sa.String(length=32), nullable=False,
                  server_default='OPEN'),
        sa.Column('closed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('closed_by_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True),
                  server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['closed_by_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_suggestions_project_id', 'suggestions', ['project_id'])
    op.create_index('ix_suggestions_status', 'suggestions', ['status'])
    op.create_index('ix_suggestions_project_status', 'suggestions', ['project_id', 'status'])


def downgrade() -> None:
    op.drop_index('ix_suggestions_project_status', table_name='suggestions')
    op.drop_index('ix_suggestions_status', table_name='suggestions')
    op.drop_index('ix_suggestions_project_id', table_name='suggestions')
    op.drop_table('suggestions')
