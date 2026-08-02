from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

from src.database.models import MealLog, MealLogItem, PantryItem, User
from src.optimizer.models import OptimizerResult
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
    captured = {}

    def fake_optimize(foods, constraints, **options):
        captured["foods"] = foods
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
                    "fiber_g": 3,
                    "cost": 2.5,
                },
                constraint_scores={"calories": 90, "protein": 100, "carbs": 80, "fat": 100},
                constraints_met={"calories": True, "protein": True, "carbs": True, "fat": True},
                feasibility_score=94.2,
                is_feasible=True,
            ),
            optimization_method="cp_sat",
            solver_status="OPTIMAL",
            objective_value=12,
            best_objective_bound=12,
            solve_time_seconds=0.01,
        )

    monkeypatch.setattr(meal_service, "optimize_meal", fake_optimize)
    response = client.post("/api/v1/meals/generate", json=generation_payload())

    assert response.status_code == 200
    assert response.json()["is_feasible"] is True
    assert {food.food_id for food in captured["foods"]} == {str(protein.id), str(carb.id)}
    captured_protein = next(food for food in captured["foods"] if food.food_id == str(protein.id))
    assert captured_protein.max_servings_per_meal == Decimal("1.5")
    assert response.json()["optimization_method"] == "cp_sat"
    assert response.json()["solver_status"] == "OPTIMAL"
    api_session.refresh(first)
    assert first.servings_available == Decimal("3")


def test_generate_marks_near_feasible_result(
    client, api_user, food_factory, api_session, monkeypatch
) -> None:
    protein = food_factory(category="protein")
    carb = food_factory(category="carbohydrate")
    add_pantry(api_session, api_user, protein)
    add_pantry(api_session, api_user, carb)

    def fake_optimize(foods, constraints, **options):
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
                    "fiber_g": 1,
                    "cost": 2,
                },
                constraint_scores={"calories": 60},
                constraints_met={"calories": False},
                feasibility_score=60,
                is_feasible=False,
            ),
            optimization_method="cp_sat",
            solver_status="OPTIMAL",
            solve_time_seconds=0.01,
            constraint_violations={"calories": 100},
        )

    monkeypatch.setattr(meal_service, "optimize_meal", fake_optimize)
    response = client.post("/api/v1/meals/generate", json=generation_payload())
    assert response.status_code == 200
    assert response.json()["is_feasible"] is False
    assert "No fully feasible" in response.json()["disclaimer"]
    assert response.json()["constraint_violations"] == {"calories": 100}


def test_generate_validates_method_and_time_limit(client, api_user) -> None:
    assert (
        client.post(
            "/api/v1/meals/generate",
            json=generation_payload(optimization_method="unknown"),
        ).status_code
        == 422
    )
    assert (
        client.post(
            "/api/v1/meals/generate", json=generation_payload(time_limit_seconds=20)
        ).status_code
        == 422
    )


def test_generate_and_accept_cp_sat_meal_preserves_then_deducts_inventory(
    client, api_user, food_factory, api_session
) -> None:
    chicken = food_factory(
        name="Chicken",
        category="protein",
        calories=Decimal("200"),
        protein=Decimal("40"),
        carbs=Decimal("0"),
        fat=Decimal("5"),
    )
    rice = food_factory(
        name="Rice",
        category="carb",
        calories=Decimal("200"),
        protein=Decimal("4"),
        carbs=Decimal("45"),
        fat=Decimal("1"),
    )
    broccoli = food_factory(
        name="Broccoli",
        category="vegetable",
        calories=Decimal("50"),
        protein=Decimal("4"),
        carbs=Decimal("10"),
        fat=Decimal("0"),
    )
    pantry = [
        add_pantry(api_session, api_user, food, servings="3", maximum="2")
        for food in (chicken, rice, broccoli)
    ]
    response = client.post(
        "/api/v1/meals/generate",
        json=generation_payload(
            calorie_goal=450,
            protein_goal=48,
            carbs_goal=55,
            fat_goal=6,
            optimization_method="cp_sat",
            time_limit_seconds=1,
        ),
    )
    assert response.status_code == 200
    body = response.json()
    assert body["optimization_method"] == "cp_sat"
    assert body["solver_status"] == "OPTIMAL"
    assert body["is_feasible"] is True
    assert body["totals"]["calories"] == 450
    for item in pantry:
        api_session.refresh(item)
        assert item.servings_available == Decimal("3")

    accepted = client.post(
        "/api/v1/meals/accept",
        json={
            "items": [
                {"food_id": item["food_id"], "servings": item["servings"]} for item in body["items"]
            ]
        },
    )
    assert accepted.status_code == 201
    used = {item["food_id"]: Decimal(str(item["servings"])) for item in body["items"]}
    for item in pantry:
        api_session.refresh(item)
        assert item.servings_available == Decimal("3") - used.get(str(item.food_id), Decimal("0"))
    assert api_session.query(MealLog).count() == 1


def test_accept_meal_deducts_recalculates_and_snapshots(
    client, api_user, food_factory, api_session
) -> None:
    food = food_factory(name="Chicken", calories=Decimal("120"), protein=Decimal("25"))
    pantry_item = add_pantry(api_session, api_user, food, servings="1.5", maximum="1.5")

    response = client.post(
        "/api/v1/meals/accept",
        json={
            "items": [{"food_id": str(food.id), "servings": 1.5}],
            "rating": 5,
            "totals": {"calories": 99999},
        },
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
