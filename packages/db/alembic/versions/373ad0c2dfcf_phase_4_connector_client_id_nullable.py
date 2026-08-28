"""phase 4: connector client_id nullable

Revision ID: 373ad0c2dfcf
Revises: 1f2cd9eda7fb
Create Date: 2026-08-28 23:15:16.961799
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = '373ad0c2dfcf'
down_revision: str | None = '1f2cd9eda7fb'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # SQLite: ALTER COLUMN tidak didukung → batch mode (recreate table)
    with op.batch_alter_table('connector_devices') as batch_op:
        batch_op.alter_column('client_id',
               existing_type=sa.VARCHAR(length=64),
               nullable=True)


def downgrade() -> None:
    with op.batch_alter_table('connector_devices') as batch_op:
        batch_op.alter_column('client_id',
               existing_type=sa.VARCHAR(length=64),
               nullable=False)
