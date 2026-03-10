"""make refresh_tokens timestamps timezone aware

Revision ID: 8a4b2b1d9f3c
Revises: 6035bd9163df
Create Date: 2026-03-10 20:15:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "8a4b2b1d9f3c"
down_revision: Union[str, None] = "6035bd9163df"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "refresh_tokens",
        "expires_at",
        existing_type=sa.DateTime(),
        type_=sa.DateTime(timezone=True),
        existing_nullable=False,
        postgresql_using="expires_at AT TIME ZONE 'UTC'",
    )
    op.alter_column(
        "refresh_tokens",
        "revoked_at",
        existing_type=sa.DateTime(),
        type_=sa.DateTime(timezone=True),
        existing_nullable=True,
        postgresql_using="revoked_at AT TIME ZONE 'UTC'",
    )
    op.alter_column(
        "refresh_tokens",
        "created_at",
        existing_type=sa.DateTime(),
        type_=sa.DateTime(timezone=True),
        existing_nullable=False,
        existing_server_default=sa.text("now()"),
        postgresql_using="created_at AT TIME ZONE 'UTC'",
    )


def downgrade() -> None:
    op.alter_column(
        "refresh_tokens",
        "created_at",
        existing_type=postgresql.TIMESTAMP(timezone=True),
        type_=sa.DateTime(),
        existing_nullable=False,
        existing_server_default=sa.text("now()"),
        postgresql_using="created_at AT TIME ZONE 'UTC'",
    )
    op.alter_column(
        "refresh_tokens",
        "revoked_at",
        existing_type=postgresql.TIMESTAMP(timezone=True),
        type_=sa.DateTime(),
        existing_nullable=True,
        postgresql_using="revoked_at AT TIME ZONE 'UTC'",
    )
    op.alter_column(
        "refresh_tokens",
        "expires_at",
        existing_type=postgresql.TIMESTAMP(timezone=True),
        type_=sa.DateTime(),
        existing_nullable=False,
        postgresql_using="expires_at AT TIME ZONE 'UTC'",
    )

