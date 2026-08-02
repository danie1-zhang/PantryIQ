import uuid


def test_search_foods_by_name_brand_and_category(client, food_factory) -> None:
    chicken = food_factory(name="Chicken Breast", brand="Farm", category="protein")
    food_factory(name="Brown Rice", brand="Chicken Kitchen", category="carbohydrate")

    response = client.get("/api/v1/foods?query=chicken&category=protein")

    assert response.status_code == 200
    assert [item["id"] for item in response.json()] == [str(chicken.id)]
    assert response.json()[0]["protein_g_per_serving"] == 20


def test_food_detail_and_unknown_food(client, food_factory) -> None:
    food = food_factory(name="Oats")

    assert client.get(f"/api/v1/foods/{food.id}").status_code == 200
    assert client.get(f"/api/v1/foods/{uuid.uuid4()}").status_code == 404


def test_food_pagination_is_validated(client) -> None:
    assert client.get("/api/v1/foods?limit=0").status_code == 422
    assert client.get("/api/v1/foods?limit=101").status_code == 422
