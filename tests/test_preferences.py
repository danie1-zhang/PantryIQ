from dataclasses import replace
from decimal import Decimal

import pytest

from src.optimizer.models import OptimizerFood
from src.optimizer.nutrition_constraints import NutritionConstraints
from src.optimizer.service import optimize_meal
from src.schemas.preferences import ParsedMealPreferences
from src.services.exceptions import BusinessRuleError, ExternalServiceError
from src.services.preference_service import filter_and_score_foods, parse_preferences


class FakeProvider:
    def __init__(self, output: str):
        self.output = output

    def parse(self, text: str) -> str:
        return self.output


def food(food_id: str, category: str, **overrides) -> OptimizerFood:
    values = dict(
        food_id=food_id,
        food_name=food_id,
        category=category,
        servings_available=Decimal("2"),
        max_servings_per_meal=Decimal("1"),
        calories_per_serving=Decimal("200"),
        protein_g_per_serving=Decimal("25"),
        carbs_g_per_serving=Decimal("20"),
        fat_g_per_serving=Decimal("10"),
        sugar_g_per_serving=Decimal("0"),
        fiber_g_per_serving=Decimal("1"),
        sodium_mg_per_serving=Decimal("10"),
        cost_per_serving=Decimal("1"),
    )
    values.update(overrides)
    return OptimizerFood(**values)


def test_parser_normalizes_aliases_duplicates_and_preferences() -> None:
    parsed = parse_preferences(
        "ignored",
        FakeProvider(
            '{"cuisines":["Grecian","greek"],"allergens":["groundnuts"],'
            '"dietary_rules":["dairy-free"],"soft_dislikes":["mushroom"],'
            '"spice_preference":"none"}'
        ),
    )
    assert parsed.cuisines == ["greek"]
    assert parsed.allergens == ["peanut"]
    assert parsed.dietary_rules == ["dairy_free"]
    assert parsed.soft_dislikes == ["mushroom"]
    assert parsed.spice_preference == "none"


@pytest.mark.parametrize(
    "output",
    [
        "not json",
        '{"invented_field":true}',
        '{"preferred_food_ids":["00000000-0000-0000-0000-000000000001"]}',
    ],
)
def test_parser_rejects_malformed_invented_or_ungrounded_output(output: str) -> None:
    with pytest.raises(ExternalServiceError):
        parse_preferences("request", FakeProvider(output))


def test_clarification_requires_a_question() -> None:
    with pytest.raises(ExternalServiceError):
        parse_preferences("ambiguous", FakeProvider('{"clarification_needed":true}'))
    parsed = parse_preferences(
        "ambiguous",
        FakeProvider(
            '{"clarification_needed":true,"clarification_question":"Strict or compatible?"}'
        ),
    )
    assert parsed.clarification_needed


def test_filtering_enforces_allergens_diet_cuisine_neutral_and_spice() -> None:
    foods = [
        food(
            "chicken",
            "protein",
            cuisine_tags=("greek",),
            dietary_tags=("dairy_free",),
            ingredient_tags=("chicken",),
        ),
        food(
            "peanut",
            "protein",
            cuisine_tags=("greek",),
            dietary_tags=("dairy_free",),
            allergen_tags=("peanut",),
        ),
        food("rice", "carb", dietary_tags=("dairy_free",), is_cuisine_neutral=True),
        food(
            "hot",
            "vegetable",
            cuisine_tags=("greek",),
            dietary_tags=("dairy_free",),
            spice_level="hot",
        ),
        food("italian", "vegetable", cuisine_tags=("italian",), dietary_tags=("dairy_free",)),
    ]
    preferences = ParsedMealPreferences(
        cuisines=["greek"],
        allergens=["peanut"],
        dietary_rules=["dairy_free"],
        preferred_ingredients=["chicken"],
        spice_preference="mild",
    )
    result = filter_and_score_foods(foods, preferences)
    assert {item.food_id for item in result.eligible_foods} == {"chicken", "rice"}
    assert (
        next(item for item in result.eligible_foods if item.food_id == "chicken").preference_score
        > 0
    )
    assert {item.food_id for item in result.excluded_foods} == {"peanut", "hot", "italian"}


def test_strict_cuisine_excludes_neutral_and_empty_result_is_clear() -> None:
    with pytest.raises(BusinessRuleError, match="No foods"):
        filter_and_score_foods(
            [food("rice", "carb", is_cuisine_neutral=True)],
            ParsedMealPreferences(cuisines=["greek"], cuisine_mode="strict"),
        )


def test_soft_preference_changes_cp_sat_tie_without_overriding_nutrition() -> None:
    chicken = food("chicken", "protein", preference_score=5)
    tofu = replace(chicken, food_id="tofu", food_name="tofu", preference_score=0)
    rice = food(
        "rice",
        "carb",
        calories_per_serving=Decimal("100"),
        protein_g_per_serving=Decimal("5"),
        carbs_g_per_serving=Decimal("30"),
        fat_g_per_serving=Decimal("0"),
    )
    constraints = NutritionConstraints(300, 30, 50, 10)
    result = optimize_meal([chicken, tofu, rice], constraints, time_limit_seconds=1)
    assert "chicken" in result.meal
    assert "tofu" not in result.meal
