from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

import pandas as pd

from src.database.models import MealLog, MealLogItem, PantryItem, User
from src.optimizer.best_meal import OptimizerResult
from src.optimizer.nutrition_constraints import MealEvaluation
from src.services import meal_service


def generation_payload(**overrides):
    values = {
        "calorie_goal": 300,
        "protein_goal": 30,
        "carbs_goal": 30,
        "fat_goal": 10,
        "number_of_candidates": 10,
    }
    values.update(overrides)
    return values


def add_pantry(session, user, food, servings="3", maximum="2", available=True):
    item = PantryItem(
        user=user,
        food=food,
        servings_available=Decimal(servings),
        max_servings_per_meal=Decimal(maximum),
        is_available=available,
    )
    session.add(item)
    session.commit()
    return item


def test_generate_rejects_empty_pantry(client, api_user) -> None:
    assert client.post("/api/v1/meals/generate", json=generation_payload()).status_code == 400


def test_generate_uses_scoped_available_pantry_without_deducting(
    client, api_user, food_factory, api_session, monkeypatch
) -> None:
    protein = food_factory(name="Chicken", category="protein")
    carb = food_factory(name="Rice", category="carbohydrate")
    hidden = food_factory(name="Hidden", category="protein")
    first = add_pantry(api_session, api_user, protein, servings="3", maximum="1.5")
    add_pantry(api_session, api_user, carb, servings="2", maximum="1")
    other = User(email="other@example.com", username="other", password_hash="x", name="Other")
    add_pantry(api_session, other, hidden)
    captured: dict[str, pd.DataFrame] = {}

    class FakeOptimizer:
        def __init__(self, frame, constraints):
            captured["frame"] = frame

        def find_best_meal(self, count):
            return OptimizerResult(
                meal={str(protein.id): 1.5, str(carb.id): 1},
                evaluation=MealEvaluation(
                    totals={
                        "calories": 200,
                        "protein_g": 40,
                        "carbs_g": 20,
                        "fat_g": 10,
                        "sodium_mg": 100,
                        "sugar_g": 2,
                        "cost": 2.5,
                    },
                    constraint_scores={"calories": 90, "protein": 100, "carbs": 80, "fat": 100},
                    constraints_met={"calories": True, "protein": True, "carbs": True, "fat": True},
                    feasibility_score=94.2,
                    is_feasible=True,
                ),
                candidates_generated=count,
                valid_candidates_evaluated=7,
            )

    monkeypatch.setattr(meal_service, "MealOptimizer", FakeOptimizer)
    response = client.post("/api/v1/meals/generate", json=generation_payload())

    assert response.status_code == 200
    assert response.json()["is_feasible"] is True
    assert set(captured["frame"]["food_item_id"]) == {str(protein.id), str(carb.id)}
    assert captured["frame"].set_index("food_item_id").loc[str(protein.id), "max_servings"] == 1.5
    api_session.refresh(first)
    assert first.servings_available == Decimal("3")


def test_generate_marks_near_feasible_result(
    client, api_user, food_factory, api_session, monkeypatch
) -> None:
    protein = food_factory(category="protein")
    carb = food_factory(category="carbohydrate")
    add_pantry(api_session, api_user, protein)
    add_pantry(api_session, api_user, carb)

    def fake_find(self, count):
        return OptimizerResult(
            meal={str(protein.id): 1, str(carb.id): 1},
            evaluation=MealEvaluation(
                totals={
                    "calories": 200,
                    "protein_g": 20,
                    "carbs_g": 20,
                    "fat_g": 10,
                    "sodium_mg": 100,
                    "sugar_g": 2,
                    "cost": 2,
                },
                constraint_scores={"calories": 60},
                constraints_met={"calories": False},
                feasibility_score=60,
                is_feasible=False,
            ),
            candidates_generated=count,
            valid_candidates_evaluated=1,
        )

    monkeypatch.setattr(meal_service.MealOptimizer, "find_best_meal", fake_find)
    response = client.post("/api/v1/meals/generate", json=generation_payload())
    assert response.status_code == 200
    assert response.json()["is_feasible"] is False
    assert "No fully feasible" in response.json()["disclaimer"]


def test_accept_meal_deducts_recalculates_and_snapshots(
    client, api_user, food_factory, api_session
) -> None:
    food = food_factory(name="Chicken", calories=Decimal("120"), protein=Decimal("25"))
    pantry_item = add_pantry(api_session, api_user, food, servings="1.5", maximum="1.5")

    response = client.post(
        "/api/v1/meals/accept",
        json={"items": [{"food_id": str(food.id), "servings": 1.5}], "rating": 5},
    )

    assert response.status_code == 201
    assert response.json()["totals"]["calories"] == 180
    api_session.refresh(pantry_item)
    assert pantry_item.servings_available == 0
    assert pantry_item.is_available is False
    assert api_session.query(MealLog).count() == 1
    snapshot = api_session.query(MealLogItem).one()
    assert snapshot.food_name == "Chicken"
    assert snapshot.calories_per_serving == Decimal("120")


def test_accept_failure_rolls_back_all_deductions(
    client, api_user, food_factory, api_session
) -> None:
    food = food_factory()
    pantry_item = add_pantry(api_session, api_user, food, servings="2", maximum="2")
    response = client.post(
        "/api/v1/meals/accept",
        json={
            "items": [
                {"food_id": str(food.id), "servings": 1},
                {"food_id": str(uuid4()), "servings": 1},
            ]
        },
    )

    assert response.status_code == 404
    api_session.refresh(pantry_item)
    assert pantry_item.servings_available == 2
    assert api_session.query(MealLog).count() == 0


def test_insufficient_servings_create_no_log(client, api_user, food_factory, api_session) -> None:
    food = food_factory()
    pantry_item = add_pantry(api_session, api_user, food, servings="1", maximum="1")

    response = client.post(
        "/api/v1/meals/accept",
        json={"items": [{"food_id": str(food.id), "servings": 2}]},
    )

    assert response.status_code == 409
    api_session.refresh(pantry_item)
    assert pantry_item.servings_available == 1
    assert api_session.query(MealLog).count() == 0


def test_accept_rejects_duplicates_and_other_users_food(
    client, api_user, food_factory, api_session
) -> None:
    food = food_factory()
    other = User(email="other@example.com", username="other", password_hash="x", name="Other")
    add_pantry(api_session, other, food)
    duplicate = {
        "items": [
            {"food_id": str(food.id), "servings": 1},
            {"food_id": str(food.id), "servings": 1},
        ]
    }
    assert client.post("/api/v1/meals/accept", json=duplicate).status_code == 422
    assert (
        client.post("/api/v1/meals/accept", json={"items": [duplicate["items"][0]]}).status_code
        == 404
    )


def test_meal_history_is_scoped_ordered_and_has_detail(
    client, api_user, food_factory, api_session
) -> None:
    food = food_factory()
    old = MealLog(
        user=api_user,
        eaten_at=datetime.now(UTC) - timedelta(days=1),
        total_calories=100,
        total_protein=20,
        total_carbs=10,
        total_fat=5,
        total_sugar=1,
        total_fiber=2,
        total_sodium=50,
    )
    new = MealLog(
        user=api_user,
        eaten_at=datetime.now(UTC),
        total_calories=100,
        total_protein=20,
        total_carbs=10,
        total_fat=5,
        total_sugar=1,
        total_fiber=2,
        total_sodium=50,
    )
    new.items.append(
        MealLogItem(
            food=food,
            servings=1,
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
    other = User(email="other@example.com", username="other", password_hash="x", name="Other")
    other_meal = MealLog(
        user=other,
        eaten_at=datetime.now(UTC) + timedelta(days=1),
        total_calories=1,
        total_protein=1,
        total_carbs=1,
        total_fat=1,
        total_sugar=1,
        total_fiber=1,
        total_sodium=1,
    )
    api_session.add_all([old, new, other_meal])
    api_session.commit()

    history = client.get("/api/v1/meals")
    assert [meal["id"] for meal in history.json()] == [str(new.id), str(old.id)]
    assert client.get(f"/api/v1/meals/{new.id}").json()["items"][0]["food_id"] == str(food.id)
    assert client.get(f"/api/v1/meals/{other_meal.id}").status_code == 404
