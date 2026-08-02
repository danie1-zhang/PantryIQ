from __future__ import annotations

PROTEIN_CATEGORIES = {
    "protein",
    "protein_carb",
    "meat",
    "poultry",
    "fish",
    "seafood",
    "egg",
    "eggs",
    "tofu",
}
CARB_CATEGORIES = {
    "carb",
    "carbohydrate",
    "protein_carb",
    "grain",
    "rice",
    "pasta",
    "bread",
    "potato",
}
PRODUCE_CATEGORIES = {"vegetable", "vegetables", "fruit", "produce"}
CONDIMENT_CATEGORIES = {"condiment", "sauce", "seasoning", "dressing"}

CATEGORY_ALIASES = {
    "carbohydrates": "carbohydrate",
    "veggie": "vegetable",
    "veggies": "vegetable",
    "protein carb": "protein_carb",
    "protein-carb": "protein_carb",
}


def normalize_category(value: str | None) -> str:
    """Normalize catalog category spelling without food-name-specific rules."""

    normalized = (value or "other").strip().lower().replace("/", "_")
    return CATEGORY_ALIASES.get(normalized, normalized)
