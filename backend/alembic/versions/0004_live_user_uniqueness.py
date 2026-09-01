"""Scope user email / employee-ID uniqueness to non-deleted accounts.

Deleting a user is a soft delete, so a plain UNIQUE constraint let a removed
account keep its email address and employee ID forever — re-adding a colleague
with the same address failed with "already registered". Users are never
restored, so narrowing the constraint to live rows cannot resurrect a clash.

Revision ID: 0004_live_uniqueness
Revises: 0003_suggestions
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = '0004_live_uniqueness'
down_revision: Union[str, None] = '0003_suggestions'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _where(dialect: str) -> str:
    return "is_deleted = false" if dialect == "postgresql" else "is_deleted = 0"


def upgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name
    predicate = _where(dialect)

    if dialect == "postgresql":
        # `email unique=True` produced a table constraint; the name is
        # deterministic but tolerate its absence so a re-run cannot wedge.
        constraint = bind.execute(sa.text("""
            select conname from pg_constraint
            where conrelid = 'users'::regclass and contype = 'u'
              and pg_get_constraintdef(oid) like '%(email)%'
        """)).scalar()
        if constraint:
            op.drop_constraint(constraint, 'users', type_='unique')
        op.drop_index('ix_users_employee_id', table_name='users')
    else:
        # SQLite cannot drop an inline UNIQUE without rebuilding the table, and
        # a plain batch rebuild copies the reflected schema verbatim — inline
        # UNIQUE included. Reflect it, strip the email constraint, and hand the
        # amended definition to batch mode as the shape to rebuild into.
        meta = sa.MetaData()
        users = sa.Table('users', meta, autoload_with=bind)
        users.constraints = {
            c for c in users.constraints
            if not (
                isinstance(c, sa.UniqueConstraint)
                and [col.name for col in c.columns] == ['email']
            )
        }
        users.indexes = {i for i in users.indexes if i.name != 'ix_users_employee_id'}
        users.c.email.unique = False
        with op.batch_alter_table('users', recreate='always', copy_from=users):
            pass

    op.create_index(
        'ix_users_employee_id', 'users', ['employee_id'],
        unique=True, postgresql_where=sa.text(predicate), sqlite_where=sa.text(predicate),
    )
    op.create_index(
        'uq_users_email_live', 'users', ['email'],
        unique=True, postgresql_where=sa.text(predicate), sqlite_where=sa.text(predicate),
    )


def downgrade() -> None:
    op.drop_index('uq_users_email_live', table_name='users')
    op.drop_index('ix_users_employee_id', table_name='users')
    op.create_index('ix_users_employee_id', 'users', ['employee_id'], unique=True)
    op.create_unique_constraint('users_email_key', 'users', ['email'])
