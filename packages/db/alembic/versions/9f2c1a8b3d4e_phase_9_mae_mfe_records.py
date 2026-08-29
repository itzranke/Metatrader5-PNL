"""phase 9: mae_mfe_records + position mae/mfe (BLUEPRINT §14)

Revision ID: 9f2c1a8b3d4e
Revises: 56abdd0ae61b
Create Date: 2026-08-29 01:20:00.000000
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = '9f2c1a8b3d4e'
down_revision: str | None = '56abdd0ae61b'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # live tick capture: MAE/MFE berjalan di posisi terbuka
    op.add_column('positions', sa.Column('mae', sa.Numeric(20, 8), nullable=True))
    op.add_column('positions', sa.Column('mfe', sa.Numeric(20, 8), nullable=True))

    op.create_table(
        'mae_mfe_records',
        sa.Column('id', sa.BigInteger().with_variant(sa.Integer(), 'sqlite'), nullable=False),
        sa.Column('user_id', sa.BigInteger().with_variant(sa.Integer(), 'sqlite'), nullable=False),
        sa.Column('trading_account_id', sa.BigInteger().with_variant(sa.Integer(), 'sqlite'), nullable=False),
        sa.Column('trade_id', sa.BigInteger().with_variant(sa.Integer(), 'sqlite'), nullable=False),
        sa.Column('mae_pts', sa.Numeric(20, 8), nullable=True),
        sa.Column('mfe_pts', sa.Numeric(20, 8), nullable=True),
        sa.Column('mae_currency', sa.Numeric(20, 8), nullable=True),
        sa.Column('mfe_currency', sa.Numeric(20, 8), nullable=True),
        sa.Column('mae_pct', sa.Numeric(10, 6), nullable=True),
        sa.Column('mfe_pct', sa.Numeric(10, 6), nullable=True),
        sa.Column('mae_r', sa.Numeric(12, 6), nullable=True),
        sa.Column('mfe_r', sa.Numeric(12, 6), nullable=True),
        sa.Column('path_source', sa.String(length=10), nullable=False),
        sa.Column('samples', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.ForeignKeyConstraint(['trading_account_id'], ['trading_accounts.id'], ),
        sa.ForeignKeyConstraint(['trade_id'], ['trades.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('trade_id', name='uq_mae_mfe_trade'),
    )
    op.create_index('ix_mae_mfe_account', 'mae_mfe_records', ['trading_account_id'])


def downgrade() -> None:
    op.drop_index('ix_mae_mfe_account', table_name='mae_mfe_records')
    op.drop_table('mae_mfe_records')
    op.drop_column('positions', 'mfe')
    op.drop_column('positions', 'mae')
