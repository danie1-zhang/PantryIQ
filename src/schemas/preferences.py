from typing import Annotated, Literal
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    field_validator,
    model_validator,
)

Tag = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]

ALIASES = {
    "grecian": "greek",
    "groundnuts": "peanut",
    "groundnut": "peanut",
    "no dairy": "dairy_free",
    "dairy-free": "dairy_free",
    "non-spicy": "none",
}
KNOWN_ALLERGENS = {
    "peanut",
    "tree_nut",
    "milk",
    "dairy",
    "egg",
    "soy",
    "wheat",
    "gluten",
    "fish",
    "shellfish",
    "sesame",
}
KNOWN_DIETARY_RULES = {
    "dairy_free",
    "gluten_free",
    "vegan",
    "vegetarian",
    "pescatarian",
    "halal",
    "kosher",
}


class ParsedMealPreferences(BaseModel):
    model_config = ConfigDict(extra="forbid")

    cuisines: list[Tag] = Field(default_factory=list, max_length=10)
    cuisine_mode: Literal["strict", "compatible", "preference"] = "compatible"
    required_food_ids: list[UUID] = Field(default_factory=list, max_length=20)
    preferred_food_ids: list[UUID] = Field(default_factory=list, max_length=20)
    excluded_food_ids: list[UUID] = Field(default_factory=list, max_length=50)
    required_categories: list[Tag] = Field(default_factory=list, max_length=20)
    preferred_categories: list[Tag] = Field(default_factory=list, max_length=20)
    excluded_categories: list[Tag] = Field(default_factory=list, max_length=20)
    preferred_ingredients: list[Tag] = Field(default_factory=list, max_length=30)
    avoid_ingredients: list[Tag] = Field(default_factory=list, max_length=30)
    allergens: list[Tag] = Field(default_factory=list, max_length=30)
    dietary_rules: list[Tag] = Field(default_factory=list, max_length=30)
    spice_preference: Literal["none", "mild", "medium", "hot", "any"] | None = None
    texture_preferences: list[Tag] = Field(default_factory=list, max_length=20)
    flavor_preferences: list[Tag] = Field(default_factory=list, max_length=20)
    preparation_preferences: list[Tag] = Field(default_factory=list, max_length=20)
    hard_exclusions: list[Tag] = Field(default_factory=list, max_length=30)
    soft_dislikes: list[Tag] = Field(default_factory=list, max_length=30)
    clarification_needed: bool = False
    clarification_question: str | None = Field(default=None, max_length=300)

    @field_validator(
        "cuisines",
        "required_categories",
        "preferred_categories",
        "excluded_categories",
        "preferred_ingredients",
        "avoid_ingredients",
        "allergens",
        "dietary_rules",
        "texture_preferences",
        "flavor_preferences",
        "preparation_preferences",
        "hard_exclusions",
        "soft_dislikes",
        mode="after",
    )
    @classmethod
    def normalize_tags(cls, values: list[str]) -> list[str]:
        normalized = [ALIASES.get(value.strip().lower(), value.strip().lower()) for value in values]
        return list(dict.fromkeys(normalized))

    @field_validator("required_food_ids", "preferred_food_ids", "excluded_food_ids")
    @classmethod
    def unique_ids(cls, values: list[UUID]) -> list[UUID]:
        return list(dict.fromkeys(values))

    @field_validator("allergens")
    @classmethod
    def known_allergens(cls, values: list[str]) -> list[str]:
        unsupported = set(values) - KNOWN_ALLERGENS
        if unsupported:
            raise ValueError(f"unsupported allergen tags: {sorted(unsupported)}")
        return values

    @field_validator("dietary_rules")
    @classmethod
    def known_dietary_rules(cls, values: list[str]) -> list[str]:
        unsupported = set(values) - KNOWN_DIETARY_RULES
        if unsupported:
            raise ValueError(f"unsupported dietary rule tags: {sorted(unsupported)}")
        return values

    @model_validator(mode="after")
    def validate_clarification(self) -> "ParsedMealPreferences":
        if self.clarification_needed and not self.clarification_question:
            raise ValueError("clarification_question is required when clarification is needed")
        return self


class PreferenceParseRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    text: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=2000)]


class PreferenceParseResponse(BaseModel):
    preferences: ParsedMealPreferences
    interpretation_summary: list[str]


class ExcludedFoodResponse(BaseModel):
    food_id: UUID
    food_name: str
    reason: str
