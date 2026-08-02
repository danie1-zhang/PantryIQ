import uuid

from src.database.models import Food, PantryItem, User


def pantry_payload(food_id, servings=4, maximum=2):
    return {
        "food_id": str(food_id),
        "servings_available": servings,
        "max_servings_per_meal": maximum,
        "notes": "freezer",
    }


def test_add_and_upsert_pantry_item(client, api_user, food_factory, api_session) -> None:
    food = food_factory(name="Chicken")
    created = client.post("/api/v1/pantry/items", json=pantry_payload(food.id))
    updated = client.post("/api/v1/pantry/items", json=pantry_payload(food.id, 1, 3))

    assert created.status_code == 201
    assert updated.status_code == 200
    assert updated.json()["servings_available"] == 5
    assert api_session.query(PantryItem).count() == 1


def test_get_pantry_is_user_scoped(client, api_user, food_factory, api_session) -> None:
    food = food_factory()
    other = User(email="other@example.com", username="other", password_hash="x", name="Other")
    api_session.add_all(
        [
            PantryItem(user=api_user, food=food, servings_available=2, max_servings_per_meal=1),
            PantryItem(user=other, food=food, servings_available=2, max_servings_per_meal=1),
        ]
    )
    api_session.commit()

    response = client.get("/api/v1/pantry")
    assert response.status_code == 200
    assert len(response.json()) == 1


def test_add_pantry_validation(client, api_user, food_factory) -> None:
    food = food_factory()
    assert client.post("/api/v1/pantry/items", json=pantry_payload(uuid.uuid4())).status_code == 404
    assert (
        client.post("/api/v1/pantry/items", json=pantry_payload(food.id, 0, 0)).status_code == 422
    )
    assert (
        client.post("/api/v1/pantry/items", json=pantry_payload(food.id, 1, 2)).status_code == 400
    )


def test_update_depletion_and_ownership(client, api_user, food_factory, api_session) -> None:
    food = food_factory()
    item = PantryItem(user=api_user, food=food, servings_available=2, max_servings_per_meal=1)
    other = User(email="other@example.com", username="other", password_hash="x", name="Other")
    other_item = PantryItem(user=other, food=food, servings_available=2, max_servings_per_meal=1)
    api_session.add_all([item, other_item])
    api_session.commit()

    response = client.patch(f"/api/v1/pantry/items/{item.id}", json={"servings_available": 0})
    assert response.status_code == 200
    assert response.json()["is_available"] is False
    assert response.json()["max_servings_per_meal"] == 0
    assert (
        client.patch(f"/api/v1/pantry/items/{other_item.id}", json={"notes": "x"}).status_code
        == 404
    )


def test_delete_pantry_keeps_food(client, api_user, food_factory, api_session) -> None:
    food = food_factory()
    item = PantryItem(user=api_user, food=food, servings_available=2, max_servings_per_meal=1)
    api_session.add(item)
    api_session.commit()
    item_id = item.id

    assert client.delete(f"/api/v1/pantry/items/{item_id}").status_code == 204
    api_session.expire_all()
    assert api_session.get(PantryItem, item_id) is None
    assert api_session.get(Food, food.id) is not None
