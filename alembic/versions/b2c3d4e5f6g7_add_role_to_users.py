"""add_role_to_users

Revision ID: b2c3d4e5f6g7
Revises: a1b2c3d4e5f6
Create Date: 2026-02-12 14:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b2c3d4e5f6g7'
down_revision: Union[str, Sequence[str], None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add role column to users table."""
    # Add as nullable first to handle any existing rows
    op.add_column('users', sa.Column('role', sa.String(20), nullable=True))

    # Set default role for existing users
    op.execute("UPDATE users SET role = 'user' WHERE role IS NULL")

    # Now make it non-nullable
    op.alter_column('users', 'role', nullable=False, server_default='user')

    # Add index on role for faster lookups
    op.create_index('ix_users_role', 'users', ['role'])


def downgrade() -> None:
    """Remove role column from users table."""
    op.drop_index('ix_users_role', table_name='users')
    op.drop_column('users', 'role')
