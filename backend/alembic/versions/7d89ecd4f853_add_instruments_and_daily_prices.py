"""add_instruments_and_daily_prices

Revision ID: 7d89ecd4f853
Revises: 264c9e5f32e5
Create Date: 2026-10-22 01:02:55.437774

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '7d89ecd4f853'
down_revision: str | Sequence[str] | None = '264c9e5f32e5'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. instruments table
    op.create_table(
        'instruments',
        sa.Column('symbol', sa.String(length=50), nullable=False),
        sa.Column('isin', sa.String(length=20), nullable=True),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('series', sa.String(length=10), nullable=False, server_default='EQ'),
        sa.Column('currency', sa.String(length=10), nullable=False, server_default='INR'),
        sa.Column('exchange', sa.String(length=20), nullable=False, server_default='NSE'),
        sa.Column('sector', sa.String(length=100), nullable=True),
        sa.Column('industry', sa.String(length=100), nullable=True),
        sa.Column('listing_date', sa.String(length=20), nullable=True),
        sa.Column('cap_bucket', sa.String(length=30), nullable=True),
        sa.Column('index_memberships_json', sa.Text(), nullable=False, server_default='[]'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('aliases_json', sa.Text(), nullable=False, server_default='[]'),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('symbol')
    )
    op.create_index('ix_instruments_isin', 'instruments', ['isin'])
    op.create_index('ix_instruments_name', 'instruments', ['name'])
    op.create_index('ix_instruments_sector', 'instruments', ['sector'])
    op.create_index('ix_instruments_cap_bucket', 'instruments', ['cap_bucket'])

    # 2. daily_prices table
    op.create_table(
        'daily_prices',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('symbol', sa.String(length=50), nullable=False),
        sa.Column('date', sa.String(length=20), nullable=False),
        sa.Column('open', sa.Float(), nullable=True),
        sa.Column('high', sa.Float(), nullable=True),
        sa.Column('low', sa.Float(), nullable=True),
        sa.Column('close', sa.Float(), nullable=True),
        sa.Column('adj_close', sa.Float(), nullable=False),
        sa.Column('volume', sa.Float(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_daily_prices_symbol', 'daily_prices', ['symbol'])
    op.create_index('ix_daily_prices_date', 'daily_prices', ['date'])
    op.create_index('ix_daily_prices_symbol_date', 'daily_prices', ['symbol', 'date'], unique=True)


def downgrade() -> None:
    op.drop_index('ix_daily_prices_symbol_date', table_name='daily_prices')
    op.drop_index('ix_daily_prices_date', table_name='daily_prices')
    op.drop_index('ix_daily_prices_symbol', table_name='daily_prices')
    op.drop_table('daily_prices')

    op.drop_index('ix_instruments_cap_bucket', table_name='instruments')
    op.drop_index('ix_instruments_sector', table_name='instruments')
    op.drop_index('ix_instruments_name', table_name='instruments')
    op.drop_index('ix_instruments_isin', table_name='instruments')
    op.drop_table('instruments')
