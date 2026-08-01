"""Initial PostgreSQL database foundation.

Revision ID: 20260801_0001
Revises: None
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "20260801_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def timestamps() -> list[sa.Column]:
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    ]


def nutrition_checks(suffix: str = "") -> list[sa.CheckConstraint]:
    fields = ("calories", "protein", "carbs", "fat", "sugar", "fiber", "sodium")
    return [
        sa.CheckConstraint(
            f"{field}{suffix} >= 0", name=f"{field}_nonnegative"
        )
        for field in fields
    ]


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("email", sa.String(320), nullable=False),
        sa.Column("username", sa.String(50), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("age", sa.Integer()),
        sa.Column("height_inches", sa.Numeric(6, 2)),
        sa.Column("weight_pounds", sa.Numeric(7, 2)),
        sa.Column("gender", sa.String(50)),
        sa.Column("calorie_goal", sa.Numeric(8, 2), server_default="2000", nullable=False),
        sa.Column("protein_goal", sa.Numeric(8, 2), server_default="50", nullable=False),
        sa.Column("carbohydrate_goal", sa.Numeric(8, 2), server_default="275", nullable=False),
        sa.Column("fat_goal", sa.Numeric(8, 2), server_default="78", nullable=False),
        sa.Column("sodium_maximum", sa.Numeric(10, 2)),
        sa.Column("sugar_maximum", sa.Numeric(8, 2)),
        *timestamps(),
        sa.CheckConstraint("age IS NULL OR age >= 0", name="age_nonnegative"),
        sa.CheckConstraint("height_inches IS NULL OR height_inches >= 0", name="height_nonnegative"),
        sa.CheckConstraint("weight_pounds IS NULL OR weight_pounds >= 0", name="weight_nonnegative"),
        sa.CheckConstraint("calorie_goal >= 0", name="calorie_goal_nonnegative"),
        sa.CheckConstraint("protein_goal >= 0", name="protein_goal_nonnegative"),
        sa.CheckConstraint("carbohydrate_goal >= 0", name="carb_goal_nonnegative"),
        sa.CheckConstraint("fat_goal >= 0", name="fat_goal_nonnegative"),
        sa.CheckConstraint("sodium_maximum IS NULL OR sodium_maximum >= 0", name="sodium_maximum_nonnegative"),
        sa.CheckConstraint("sugar_maximum IS NULL OR sugar_maximum >= 0", name="sugar_maximum_nonnegative"),
        sa.PrimaryKeyConstraint("id", name="pk_users"),
        sa.UniqueConstraint("email", name="uq_users_email"),
        sa.UniqueConstraint("username", name="uq_users_username"),
    )

    op.create_table(
        "foods",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("external_source", sa.String(100)),
        sa.Column("external_id", sa.String(255)),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("brand", sa.String(255), nullable=False),
        sa.Column("category", sa.String(100), nullable=False),
        sa.Column("serving_size", sa.Numeric(10, 3), nullable=False),
        sa.Column("serving_unit", sa.String(50), nullable=False),
        sa.Column("calories", sa.Numeric(10, 2), nullable=False),
        sa.Column("protein", sa.Numeric(10, 2), nullable=False),
        sa.Column("carbs", sa.Numeric(10, 2), nullable=False),
        sa.Column("fat", sa.Numeric(10, 2), nullable=False),
        sa.Column("sugar", sa.Numeric(10, 2), nullable=False),
        sa.Column("fiber", sa.Numeric(10, 2), nullable=False),
        sa.Column("sodium", sa.Numeric(12, 2), nullable=False),
        sa.Column("cost_per_serving", sa.Numeric(10, 2)),
        *timestamps(),
        sa.CheckConstraint("serving_size >= 0", name="serving_size_nonnegative"),
        *nutrition_checks(),
        sa.CheckConstraint("cost_per_serving IS NULL OR cost_per_serving >= 0", name="cost_per_serving_nonnegative"),
        sa.PrimaryKeyConstraint("id", name="pk_foods"),
        sa.UniqueConstraint("external_source", "external_id", name="uq_foods_external_identity"),
    )

    op.create_table(
        "pantry_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("food_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("servings_available", sa.Numeric(10, 3), nullable=False),
        sa.Column("max_servings_per_meal", sa.Numeric(10, 3), nullable=False),
        sa.Column("expiration_date", sa.Date()),
        sa.Column("notes", sa.Text()),
        sa.Column("is_available", sa.Boolean(), server_default=sa.true(), nullable=False),
        *timestamps(),
        sa.CheckConstraint("servings_available >= 0", name="servings_available_nonnegative"),
        sa.CheckConstraint("max_servings_per_meal >= 0", name="max_servings_nonnegative"),
        sa.CheckConstraint("max_servings_per_meal <= servings_available", name="max_servings_within_available"),
        sa.ForeignKeyConstraint(["food_id"], ["foods.id"], ondelete="RESTRICT", name="fk_pantry_items_food_id_foods"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE", name="fk_pantry_items_user_id_users"),
        sa.PrimaryKeyConstraint("id", name="pk_pantry_items"),
        sa.UniqueConstraint("user_id", "food_id", name="uq_pantry_items_user_food"),
    )
    op.create_index("ix_pantry_items_food_id", "pantry_items", ["food_id"])
    op.create_index("ix_pantry_items_user_id", "pantry_items", ["user_id"])

    op.create_table(
        "meal_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("eaten_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("total_calories", sa.Numeric(12, 2), nullable=False),
        sa.Column("total_protein", sa.Numeric(12, 2), nullable=False),
        sa.Column("total_carbs", sa.Numeric(12, 2), nullable=False),
        sa.Column("total_fat", sa.Numeric(12, 2), nullable=False),
        sa.Column("total_sugar", sa.Numeric(12, 2), nullable=False),
        sa.Column("total_fiber", sa.Numeric(12, 2), nullable=False),
        sa.Column("total_sodium", sa.Numeric(14, 2), nullable=False),
        sa.Column("rating", sa.Integer()),
        sa.Column("notes", sa.Text()),
        *timestamps(),
        *[sa.CheckConstraint(f"total_{field} >= 0", name=f"total_{field}_nonnegative") for field in ("calories", "protein", "carbs", "fat", "sugar", "fiber", "sodium")],
        sa.CheckConstraint("rating IS NULL OR rating BETWEEN 1 AND 5", name="rating_range"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE", name="fk_meal_logs_user_id_users"),
        sa.PrimaryKeyConstraint("id", name="pk_meal_logs"),
    )
    op.create_index("ix_meal_logs_user_id", "meal_logs", ["user_id"])

    op.create_table(
        "meal_log_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("meal_log_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("food_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("servings", sa.Numeric(10, 3), nullable=False),
        sa.Column("food_name", sa.String(255), nullable=False),
        sa.Column("calories_per_serving", sa.Numeric(10, 2), nullable=False),
        sa.Column("protein_per_serving", sa.Numeric(10, 2), nullable=False),
        sa.Column("carbs_per_serving", sa.Numeric(10, 2), nullable=False),
        sa.Column("fat_per_serving", sa.Numeric(10, 2), nullable=False),
        sa.Column("sugar_per_serving", sa.Numeric(10, 2), nullable=False),
        sa.Column("fiber_per_serving", sa.Numeric(10, 2), nullable=False),
        sa.Column("sodium_per_serving", sa.Numeric(12, 2), nullable=False),
        *timestamps(),
        sa.CheckConstraint("servings >= 0", name="servings_nonnegative"),
        *nutrition_checks("_per_serving"),
        sa.ForeignKeyConstraint(["food_id"], ["foods.id"], ondelete="RESTRICT", name="fk_meal_log_items_food_id_foods"),
        sa.ForeignKeyConstraint(["meal_log_id"], ["meal_logs.id"], ondelete="CASCADE", name="fk_meal_log_items_meal_log_id_meal_logs"),
        sa.PrimaryKeyConstraint("id", name="pk_meal_log_items"),
    )
    op.create_index("ix_meal_log_items_food_id", "meal_log_items", ["food_id"])
    op.create_index("ix_meal_log_items_meal_log_id", "meal_log_items", ["meal_log_id"])


def downgrade() -> None:
    op.drop_table("meal_log_items")
    op.drop_table("meal_logs")
    op.drop_table("pantry_items")
    op.drop_table("foods")
    op.drop_table("users")
