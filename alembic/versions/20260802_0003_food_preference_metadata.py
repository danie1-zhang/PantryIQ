"""Add trusted food preference metadata.

Revision ID: 20260802_0003
Revises: 20260802_0002
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "20260802_0003"
down_revision: str | None = "20260802_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    for name, length in (
        ("cuisine_tags", 50),
        ("dietary_tags", 50),
        ("allergen_tags", 50),
        ("ingredient_tags", 100),
        ("flavor_tags", 50),
    ):
        op.add_column(
            "foods",
            sa.Column(
                name,
                postgresql.ARRAY(sa.String(length)),
                server_default="{}",
                nullable=False,
            ),
        )
    op.add_column(
        "foods", sa.Column("spice_level", sa.String(20), server_default="none", nullable=False)
    )
    op.add_column(
        "foods",
        sa.Column("is_cuisine_neutral", sa.Boolean(), server_default=sa.false(), nullable=False),
    )


def downgrade() -> None:
    for name in (
        "is_cuisine_neutral",
        "spice_level",
        "flavor_tags",
        "ingredient_tags",
        "allergen_tags",
        "dietary_tags",
        "cuisine_tags",
    ):
        op.drop_column("foods", name)
