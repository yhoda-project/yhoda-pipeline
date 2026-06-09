"""Add subdomain column to indicator table.

Revision ID: f1a2b3c4d5e6
Revises: e7f8a9b0c1d2
Create Date: 2026-06-05
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "f1a2b3c4d5e6"
down_revision = "e7f8a9b0c1d2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("indicator", sa.Column("subdomain", sa.String(100), nullable=True))


def downgrade() -> None:
    op.drop_column("indicator", "subdomain")
