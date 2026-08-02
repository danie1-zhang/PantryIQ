from decimal import Decimal

from src.api.routes.preferences import get_preference_provider
from src.app.main import app
from src.database.models import PantryItem


class GreekProvider:
    def parse(self, text: str) -> str:
        return (
            '{"cuisines":["greek"],"allergens":["peanut"],'
            '"dietary_rules":["dairy_free"],"preferred_categories":["protein"]}'
        )


class BrokenProvider:
    def parse(self, text: str) -> str:
        return "not json"


def test_authenticated_parse_returns_validated_summary(client) -> None:
    app.dependency_overrides[get_preference_provider] = lambda: GreekProvider()
    try:
        response = client.post(
            "/api/v1/preferences/parse",
            json={"text": "I want a Greek high-protein meal without peanuts or dairy."},
        )
    finally:
        app.dependency_overrides.pop(get_preference_provider, None)
    assert response.status_code == 200
    assert response.json()["preferences"]["allergens"] == ["peanut"]
    assert any("Greek" in line for line in response.json()["interpretation_summary"])


def test_parse_validates_auth_text_length_and_extra_user_id(client) -> None:
    assert (
        client.post(
            "/api/v1/preferences/parse", json={"text": "hello"}, headers={"Authorization": ""}
        ).status_code
        == 401
    )
    assert client.post("/api/v1/preferences/parse", json={"text": "   "}).status_code == 422
    assert client.post("/api/v1/preferences/parse", json={"text": "x" * 2001}).status_code == 422
    assert (
        client.post("/api/v1/preferences/parse", json={"text": "Greek", "user_id": "x"}).status_code
        == 422
    )


def test_provider_failure_is_controlled(client) -> None:
    app.dependency_overrides[get_preference_provider] = lambda: BrokenProvider()
    try:
        response = client.post("/api/v1/preferences/parse", json={"text": "Greek"})
    finally:
        app.dependency_overrides.pop(get_preference_provider, None)
    assert response.status_code == 503


def test_greek_peanut_example_runs_end_to_end(client, api_user, api_session, food_factory) -> None:
    chicken = food_factory(
        name="Greek Chicken",
        category="protein",
        cuisine_tags=["greek"],
        dietary_tags=["dairy_free"],
        ingredient_tags=["chicken"],
    )
    rice = food_factory(
        name="Rice",
        category="carb",
        dietary_tags=["dairy_free"],
        is_cuisine_neutral=True,
    )
    peanut = food_factory(
        name="Peanut Sauce",
        category="condiment",
        cuisine_tags=["greek"],
        dietary_tags=["dairy_free"],
        allergen_tags=["peanut"],
    )
    api_session.add_all(
        [
            PantryItem(
                user=api_user,
                food=item,
                servings_available=Decimal("1"),
                max_servings_per_meal=Decimal("1"),
            )
            for item in (chicken, rice, peanut)
        ]
    )
    api_session.commit()
    app.dependency_overrides[get_preference_provider] = lambda: GreekProvider()
    try:
        parsed = client.post(
            "/api/v1/preferences/parse",
            json={"text": "Greek high-protein without peanuts or dairy"},
        ).json()
    finally:
        app.dependency_overrides.pop(get_preference_provider, None)

    generated = client.post(
        "/api/v1/meals/generate",
        json={
            "calorie_goal": 200,
            "protein_goal": 40,
            "carbs_goal": 20,
            "fat_goal": 10,
            "preferences": parsed["preferences"],
            "time_limit_seconds": 1,
        },
    )
    assert generated.status_code == 200
    assert {item["food_id"] for item in generated.json()["items"]} == {
        str(chicken.id),
        str(rice.id),
    }
    assert generated.json()["excluded_foods"] == [
        {
            "food_id": str(peanut.id),
            "food_name": "Peanut Sauce",
            "reason": "Contains excluded allergen: peanut",
        }
    ]
