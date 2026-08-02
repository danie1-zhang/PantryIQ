from __future__ import annotations

from dataclasses import dataclass, replace
import json
from pydantic import ValidationError

from src.ai.preference_provider import PreferenceProvider
from src.optimizer.models import OptimizerFood
from src.schemas.preferences import ParsedMealPreferences
from src.services.exceptions import BusinessRuleError, ExternalServiceError

SPICE_RANK = {"none": 0, "mild": 1, "medium": 2, "hot": 3, "any": 99}


@dataclass(frozen=True)
class ExcludedFood:
    food_id: str
    food_name: str
    reason: str


@dataclass(frozen=True)
class PreferenceFilterResult:
    eligible_foods: list[OptimizerFood]
    excluded_foods: list[ExcludedFood]
    warnings: list[str]


def parse_preferences(
    text: str, provider: PreferenceProvider, *, validation_retries: int = 0
) -> ParsedMealPreferences:
    """Validate provider JSON and reject ungrounded database identifiers."""

    last_error: Exception | None = None
    for _ in range(validation_retries + 1):
        try:
            result = ParsedMealPreferences.model_validate_json(provider.parse(text))
            if result.required_food_ids or result.preferred_food_ids or result.excluded_food_ids:
                raise ValueError("ungrounded food identifiers")
            return result
        except (ValidationError, json.JSONDecodeError, ValueError) as exc:
            last_error = exc
    raise ExternalServiceError("The preference parser returned an invalid response") from last_error


def interpretation_summary(preferences: ParsedMealPreferences) -> list[str]:
    summary: list[str] = []
    if preferences.cuisines:
        summary.append(
            f"{', '.join(preferences.cuisines).title()} cuisine uses {preferences.cuisine_mode} matching."
        )
    for allergen in preferences.allergens:
        summary.append(f"Foods tagged with the {allergen} allergen are excluded.")
    for rule in preferences.dietary_rules:
        summary.append(f"Only foods compatible with {rule.replace('_', ' ')} are eligible.")
    for ingredient in preferences.avoid_ingredients:
        summary.append(f"Foods containing {ingredient} are excluded.")
    if preferences.preferred_categories:
        summary.append(f"Preferred categories: {', '.join(preferences.preferred_categories)}.")
    if preferences.preferred_ingredients:
        summary.append(f"Preferred ingredients: {', '.join(preferences.preferred_ingredients)}.")
    if preferences.spice_preference and preferences.spice_preference != "any":
        summary.append(f"Maximum spice level: {preferences.spice_preference}.")
    return summary


def filter_and_score_foods(
    foods: list[OptimizerFood], preferences: ParsedMealPreferences
) -> PreferenceFilterResult:
    eligible: list[OptimizerFood] = []
    excluded: list[ExcludedFood] = []
    requested_cuisines = set(preferences.cuisines)
    required_ids = {str(value) for value in preferences.required_food_ids}
    excluded_ids = {str(value) for value in preferences.excluded_food_ids}
    required_categories = set(preferences.required_categories)

    for food in foods:
        reason = _exclusion_reason(food, preferences, requested_cuisines, excluded_ids)
        if reason:
            excluded.append(ExcludedFood(food.food_id, food.food_name, reason))
            continue
        score = _preference_score(food, preferences, requested_cuisines)
        eligible.append(
            replace(
                food,
                preference_score=score,
                is_required=food.food_id in required_ids,
            )
        )
    if not eligible:
        raise BusinessRuleError(
            "No foods in your pantry satisfy the selected preference restrictions."
        )
    eligible_ids = {food.food_id for food in eligible}
    if required_ids - eligible_ids:
        raise BusinessRuleError("A required food is unavailable or violates a hard restriction.")
    if required_categories and not required_categories.issubset(
        {food.category for food in eligible}
    ):
        raise BusinessRuleError("A required food category is unavailable.")
    return PreferenceFilterResult(eligible, excluded, [])


def _exclusion_reason(food, preferences, cuisines, excluded_ids) -> str | None:
    if food.food_id in excluded_ids:
        return "Explicitly excluded food"
    if food.category in preferences.excluded_categories:
        return f"Excluded category: {food.category}"
    allergens = set(food.allergen_tags) & set(preferences.allergens)
    if allergens:
        return f"Contains excluded allergen: {sorted(allergens)[0]}"
    ingredients = set(food.ingredient_tags)
    avoided = ingredients & set(preferences.avoid_ingredients + preferences.hard_exclusions)
    if avoided:
        return f"Contains excluded ingredient: {sorted(avoided)[0]}"
    missing_rules = set(preferences.dietary_rules) - set(food.dietary_tags)
    if missing_rules:
        return f"Not verified compatible with dietary rule: {sorted(missing_rules)[0]}"
    if (
        cuisines
        and preferences.cuisine_mode == "strict"
        and not cuisines.intersection(food.cuisine_tags)
    ):
        return f"Not tagged for strict cuisine: {sorted(cuisines)[0]}"
    if (
        cuisines
        and preferences.cuisine_mode == "compatible"
        and not food.is_cuisine_neutral
        and not cuisines.intersection(food.cuisine_tags)
    ):
        return f"Not compatible with requested cuisine: {sorted(cuisines)[0]}"
    if preferences.spice_preference and preferences.spice_preference != "any":
        if SPICE_RANK.get(food.spice_level, 99) > SPICE_RANK[preferences.spice_preference]:
            return f"Spice level exceeds {preferences.spice_preference}"
    return None


def _preference_score(food, preferences, cuisines) -> int:
    score = 0
    if cuisines.intersection(food.cuisine_tags):
        score += 3
    if food.category in preferences.preferred_categories:
        score += 2
    if set(food.ingredient_tags).intersection(preferences.preferred_ingredients):
        score += 3
    if set(food.flavor_tags).intersection(preferences.flavor_preferences):
        score += 1
    searchable = set(food.ingredient_tags) | set(food.flavor_tags) | {food.food_name.lower()}
    if searchable.intersection(preferences.soft_dislikes):
        score -= 2
    if food.food_id in {str(value) for value in preferences.preferred_food_ids}:
        score += 4
    return max(-10, min(10, score))
