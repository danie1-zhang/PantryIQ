from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

import pandas as pd
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload, selectinload

from src.database.models import MealLog, MealLogItem, PantryItem, User
from src.optimizer.best_meal import MealOptimizer
from src.optimizer.nutrition_constraints import NutritionConstraints
from src.schemas.meal import (
    GeneratedMealItem,
    MealAcceptRequest,
    MealGenerateRequest,
    MealGenerateResponse,
    NutritionTotals,
)


def available_pantry_statement(user: User):
    return (
        select(PantryItem)
        .options(joinedload(PantryItem.food))
        .where(
            PantryItem.user_id == user.id,
            PantryItem.is_available.is_(True),
            PantryItem.servings_available > 0,
            PantryItem.max_servings_per_meal > 0,
        )
    )


def pantry_to_optimizer_frame(items: list[PantryItem]) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "food_item_id": str(item.food_id),
                "food_nm": item.food.name,
                "category": "carb" if item.food.category == "carbohydrate" else item.food.category,
                "servings": float(item.servings_available),
                "max_servings": float(item.max_servings_per_meal),
                "is_available": item.is_available,
                "calories_per_serving": float(item.food.calories),
                "protein_g_per_serving": float(item.food.protein),
                "carbs_g_per_serving": float(item.food.carbs),
                "fat_g_per_serving": float(item.food.fat),
                "sugar_g_per_serving": float(item.food.sugar),
                "fiber_g_per_serving": float(item.food.fiber),
                "sodium_mg_per_serving": float(item.food.sodium),
                "cost_per_serving": float(item.food.cost_per_serving or 0),
            }
            for item in items
        ]
    )


def generate_meal(
    session: Session, user: User, request: MealGenerateRequest
) -> MealGenerateResponse:
    pantry_items = list(session.scalars(available_pantry_statement(user)))
    if not pantry_items:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Pantry is empty")

    frame = pantry_to_optimizer_frame(pantry_items)
    constraints = NutritionConstraints(
        calorie_goal=float(request.calorie_goal),
        protein_goal=float(request.protein_goal),
        carbs_goal=float(request.carbs_goal),
        fat_goal=float(request.fat_goal),
        sodium_max=float(request.sodium_max) if request.sodium_max is not None else None,
        sugar_max=float(request.sugar_max) if request.sugar_max is not None else None,
        cost_max=float(request.cost_max) if request.cost_max is not None else None,
    )
    try:
        result = MealOptimizer(frame, constraints).find_best_meal(request.number_of_candidates)
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    foods = {str(item.food_id): item.food for item in pantry_items}
    evaluation = result.evaluation
    disclaimer = (
        "This is the best meal found by the randomized search and is not guaranteed to be a global optimum."
        if evaluation.is_feasible
        else "No fully feasible meal was found. This is the highest-scoring near-feasible candidate found."
    )
    return MealGenerateResponse(
        is_feasible=evaluation.is_feasible,
        feasibility_score=evaluation.feasibility_score,
        items=[
            GeneratedMealItem(
                food_id=UUID(food_id), food_name=foods[food_id].name, servings=servings
            )
            for food_id, servings in result.meal.items()
        ],
        totals=NutritionTotals(**evaluation.totals),
        constraint_scores=evaluation.constraint_scores,
        constraints_met=evaluation.constraints_met,
        candidates_generated=result.candidates_generated,
        valid_candidates_evaluated=result.valid_candidates_evaluated,
        disclaimer=disclaimer,
    )


def accept_meal(session: Session, user: User, request: MealAcceptRequest) -> MealLog:
    food_ids = [item.food_id for item in request.items]
    pantry_items = list(
        session.scalars(
            select(PantryItem)
            .options(joinedload(PantryItem.food))
            .where(PantryItem.user_id == user.id, PantryItem.food_id.in_(food_ids))
            .with_for_update(of=PantryItem)
        )
    )
    pantry_by_food = {item.food_id: item for item in pantry_items}
    if len(pantry_by_food) != len(food_ids):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Food not found in pantry"
        )

    totals = {
        name: Decimal("0")
        for name in ("calories", "protein", "carbs", "fat", "sugar", "fiber", "sodium")
    }
    for requested in request.items:
        pantry_item = pantry_by_food[requested.food_id]
        if not pantry_item.is_available or requested.servings > pantry_item.servings_available:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail="Insufficient pantry servings"
            )
        food = pantry_item.food
        for name in totals:
            totals[name] += getattr(food, name) * requested.servings

    meal_log = MealLog(
        user_id=user.id,
        eaten_at=request.eaten_at or datetime.now(UTC),
        rating=request.rating,
        notes=request.notes,
        **{f"total_{name}": value for name, value in totals.items()},
    )
    for requested in request.items:
        pantry_item = pantry_by_food[requested.food_id]
        food = pantry_item.food
        pantry_item.servings_available -= requested.servings
        pantry_item.max_servings_per_meal = min(
            pantry_item.max_servings_per_meal, pantry_item.servings_available
        )
        if pantry_item.servings_available == 0:
            pantry_item.is_available = False
        meal_log.items.append(
            MealLogItem(
                food_id=food.id,
                servings=requested.servings,
                food_name=food.name,
                calories_per_serving=food.calories,
                protein_per_serving=food.protein,
                carbs_per_serving=food.carbs,
                fat_per_serving=food.fat,
                sugar_per_serving=food.sugar,
                fiber_per_serving=food.fiber,
                sodium_per_serving=food.sodium,
            )
        )
    session.add(meal_log)
    session.commit()
    return get_meal(session, user, meal_log.id)


def list_meals(session: Session, user: User, *, limit: int, offset: int) -> list[MealLog]:
    statement = (
        select(MealLog)
        .options(selectinload(MealLog.items))
        .where(MealLog.user_id == user.id)
        .order_by(MealLog.eaten_at.desc(), MealLog.id.desc())
        .limit(limit)
        .offset(offset)
    )
    return list(session.scalars(statement))


def get_meal(session: Session, user: User, meal_id: UUID) -> MealLog:
    meal = session.scalar(
        select(MealLog)
        .options(selectinload(MealLog.items))
        .where(MealLog.id == meal_id, MealLog.user_id == user.id)
    )
    if meal is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Meal not found")
    return meal
