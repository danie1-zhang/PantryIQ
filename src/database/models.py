from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database.base import Base


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class User(TimestampMixin, Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint("age IS NULL OR age >= 0", name="age_nonnegative"),
        CheckConstraint("height_inches IS NULL OR height_inches >= 0", name="height_nonnegative"),
        CheckConstraint("weight_pounds IS NULL OR weight_pounds >= 0", name="weight_nonnegative"),
        CheckConstraint("calorie_goal >= 0", name="calorie_goal_nonnegative"),
        CheckConstraint("protein_goal >= 0", name="protein_goal_nonnegative"),
        CheckConstraint("carbohydrate_goal >= 0", name="carb_goal_nonnegative"),
        CheckConstraint("fat_goal >= 0", name="fat_goal_nonnegative"),
        CheckConstraint(
            "sodium_maximum IS NULL OR sodium_maximum >= 0",
            name="sodium_maximum_nonnegative",
        ),
        CheckConstraint(
            "sugar_maximum IS NULL OR sugar_maximum >= 0",
            name="sugar_maximum_nonnegative",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(320), unique=True, nullable=False)
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    age: Mapped[int | None] = mapped_column(Integer)
    height_inches: Mapped[Decimal | None] = mapped_column(Numeric(6, 2))
    weight_pounds: Mapped[Decimal | None] = mapped_column(Numeric(7, 2))
    gender: Mapped[str | None] = mapped_column(String(50))
    calorie_goal: Mapped[Decimal] = mapped_column(
        Numeric(8, 2), default=2000, server_default="2000"
    )
    protein_goal: Mapped[Decimal] = mapped_column(Numeric(8, 2), default=50, server_default="50")
    carbohydrate_goal: Mapped[Decimal] = mapped_column(
        Numeric(8, 2), default=275, server_default="275"
    )
    fat_goal: Mapped[Decimal] = mapped_column(Numeric(8, 2), default=78, server_default="78")
    sodium_maximum: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    sugar_maximum: Mapped[Decimal | None] = mapped_column(Numeric(8, 2))

    pantry_items: Mapped[list[PantryItem]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    meal_logs: Mapped[list[MealLog]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class Food(TimestampMixin, Base):
    __tablename__ = "foods"
    __table_args__ = (
        UniqueConstraint("external_source", "external_id", name="uq_foods_external_identity"),
        CheckConstraint("serving_size >= 0", name="serving_size_nonnegative"),
        CheckConstraint("calories >= 0", name="calories_nonnegative"),
        CheckConstraint("protein >= 0", name="protein_nonnegative"),
        CheckConstraint("carbs >= 0", name="carbs_nonnegative"),
        CheckConstraint("fat >= 0", name="fat_nonnegative"),
        CheckConstraint("sugar >= 0", name="sugar_nonnegative"),
        CheckConstraint("fiber >= 0", name="fiber_nonnegative"),
        CheckConstraint("sodium >= 0", name="sodium_nonnegative"),
        CheckConstraint(
            "cost_per_serving IS NULL OR cost_per_serving >= 0",
            name="cost_per_serving_nonnegative",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    external_source: Mapped[str | None] = mapped_column(String(100))
    external_id: Mapped[str | None] = mapped_column(String(255))
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    brand: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[str] = mapped_column(String(100), nullable=False)
    serving_size: Mapped[Decimal] = mapped_column(Numeric(10, 3), nullable=False)
    serving_unit: Mapped[str] = mapped_column(String(50), nullable=False)
    calories: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    protein: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    carbs: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    fat: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    sugar: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    fiber: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    sodium: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    cost_per_serving: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))

    pantry_items: Mapped[list[PantryItem]] = relationship(back_populates="food")
    meal_log_items: Mapped[list[MealLogItem]] = relationship(back_populates="food")


class PantryItem(TimestampMixin, Base):
    __tablename__ = "pantry_items"
    __table_args__ = (
        UniqueConstraint("user_id", "food_id", name="uq_pantry_items_user_food"),
        CheckConstraint("servings_available >= 0", name="servings_available_nonnegative"),
        CheckConstraint("max_servings_per_meal >= 0", name="max_servings_nonnegative"),
        CheckConstraint(
            "max_servings_per_meal <= servings_available", name="max_servings_within_available"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    food_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("foods.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    servings_available: Mapped[Decimal] = mapped_column(Numeric(10, 3), nullable=False)
    max_servings_per_meal: Mapped[Decimal] = mapped_column(Numeric(10, 3), nullable=False)
    expiration_date: Mapped[date | None] = mapped_column(Date)
    notes: Mapped[str | None] = mapped_column(Text)
    is_available: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default="true", nullable=False
    )

    user: Mapped[User] = relationship(back_populates="pantry_items")
    food: Mapped[Food] = relationship(back_populates="pantry_items")


class MealLog(TimestampMixin, Base):
    __tablename__ = "meal_logs"
    __table_args__ = (
        CheckConstraint("total_calories >= 0", name="total_calories_nonnegative"),
        CheckConstraint("total_protein >= 0", name="total_protein_nonnegative"),
        CheckConstraint("total_carbs >= 0", name="total_carbs_nonnegative"),
        CheckConstraint("total_fat >= 0", name="total_fat_nonnegative"),
        CheckConstraint("total_sugar >= 0", name="total_sugar_nonnegative"),
        CheckConstraint("total_fiber >= 0", name="total_fiber_nonnegative"),
        CheckConstraint("total_sodium >= 0", name="total_sodium_nonnegative"),
        CheckConstraint("rating IS NULL OR rating BETWEEN 1 AND 5", name="rating_range"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    eaten_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    total_calories: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    total_protein: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    total_carbs: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    total_fat: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    total_sugar: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    total_fiber: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    total_sodium: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    rating: Mapped[int | None] = mapped_column(Integer)
    notes: Mapped[str | None] = mapped_column(Text)

    user: Mapped[User] = relationship(back_populates="meal_logs")
    items: Mapped[list[MealLogItem]] = relationship(
        back_populates="meal_log", cascade="all, delete-orphan"
    )


class MealLogItem(TimestampMixin, Base):
    __tablename__ = "meal_log_items"
    __table_args__ = (
        CheckConstraint("servings >= 0", name="servings_nonnegative"),
        CheckConstraint("calories_per_serving >= 0", name="calories_nonnegative"),
        CheckConstraint("protein_per_serving >= 0", name="protein_nonnegative"),
        CheckConstraint("carbs_per_serving >= 0", name="carbs_nonnegative"),
        CheckConstraint("fat_per_serving >= 0", name="fat_nonnegative"),
        CheckConstraint("sugar_per_serving >= 0", name="sugar_nonnegative"),
        CheckConstraint("fiber_per_serving >= 0", name="fiber_nonnegative"),
        CheckConstraint("sodium_per_serving >= 0", name="sodium_nonnegative"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    meal_log_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("meal_logs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    food_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("foods.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    servings: Mapped[Decimal] = mapped_column(Numeric(10, 3), nullable=False)
    food_name: Mapped[str] = mapped_column(String(255), nullable=False)
    calories_per_serving: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    protein_per_serving: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    carbs_per_serving: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    fat_per_serving: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    sugar_per_serving: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    fiber_per_serving: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    sodium_per_serving: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)

    meal_log: Mapped[MealLog] = relationship(back_populates="items")
    food: Mapped[Food] = relationship(back_populates="meal_log_items")
