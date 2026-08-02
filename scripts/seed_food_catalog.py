"""Import data/food_catalog.csv into the foods table."""

from __future__ import annotations

import argparse
import csv
import re
import sys
from decimal import Decimal
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.database.models import Food  # noqa: E402
from src.database.session import SessionLocal  # noqa: E402

DEFAULT_CATALOG = PROJECT_ROOT / "data" / "food_catalog.csv"
DEFAULT_METADATA = PROJECT_ROOT / "data" / "food_preference_metadata.csv"
SERVING_PATTERN = re.compile(r"^\s*(\d+(?:\.\d+)?)\s+(.+?)\s*$")


def parse_serving(value: str) -> tuple[Decimal, str]:
    match = SERVING_PATTERN.fullmatch(value)
    if not match:
        raise ValueError(f"Invalid serving size {value!r}; expected '<number> <unit>'")
    return Decimal(match.group(1)), match.group(2)


def optional_decimal(value: str | None) -> Decimal | None:
    return Decimal(value) if value and value.strip() else None


def parse_tags(value: str | None) -> list[str]:
    return [tag.strip().lower() for tag in (value or "").split(";") if tag.strip()]


def load_preference_metadata(path: Path = DEFAULT_METADATA) -> dict[str, dict[str, object]]:
    if not path.exists():
        return {}
    with path.open(newline="", encoding="utf-8-sig") as metadata_file:
        return {
            row["food_id"]: {
                "cuisine_tags": parse_tags(row["cuisine_tags"]),
                "dietary_tags": parse_tags(row["dietary_tags"]),
                "allergen_tags": parse_tags(row["allergen_tags"]),
                "ingredient_tags": parse_tags(row["ingredient_tags"]),
                "flavor_tags": parse_tags(row["flavor_tags"]),
                "spice_level": row["spice_level"].strip().lower() or "none",
                "is_cuisine_neutral": row["is_cuisine_neutral"].strip().lower() == "true",
            }
            for row in csv.DictReader(metadata_file)
        }


def seed_food_catalog(
    catalog_path: Path = DEFAULT_CATALOG,
    session_factory: sessionmaker[Session] = SessionLocal,
) -> tuple[int, int]:
    created = updated = 0
    preference_metadata = load_preference_metadata()
    with (
        catalog_path.open(newline="", encoding="utf-8-sig") as catalog_file,
        session_factory.begin() as session,
    ):
        for row in csv.DictReader(catalog_file):
            serving_size, serving_unit = parse_serving(row["serving_size"])
            values = {
                "external_source": row["source"].strip() or None,
                "external_id": row["food_id"].strip(),
                "name": row["food_name"].strip(),
                # The existing catalog has no brand column; retain that fact explicitly.
                "brand": "Generic",
                "category": row["food_category"].strip(),
                "serving_size": serving_size,
                "serving_unit": serving_unit,
                "calories": Decimal(row["calories_per_serving"]),
                "protein": Decimal(row["protein_g_per_serving"]),
                "carbs": Decimal(row["carbs_g_per_serving"]),
                "fat": Decimal(row["fat_g_per_serving"]),
                "sugar": Decimal(row["sugar_g_per_serving"]),
                "fiber": Decimal(row["fiber_g_per_serving"]),
                "sodium": Decimal(row["sodium_mg_per_serving"]),
                "cost_per_serving": optional_decimal(row["cost_per_serving"]),
            }
            values.update(preference_metadata.get(row["food_id"].strip(), {}))
            food = session.scalar(
                select(Food).where(
                    Food.external_source == values["external_source"],
                    Food.external_id == values["external_id"],
                )
            )
            if food is None:
                session.add(Food(**values))
                created += 1
            else:
                for key, value in values.items():
                    setattr(food, key, value)
                updated += 1
    return created, updated


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("catalog", nargs="?", type=Path, default=DEFAULT_CATALOG)
    args = parser.parse_args()
    created, updated = seed_food_catalog(args.catalog)
    print(f"Food catalog seed complete: {created} created, {updated} updated")


if __name__ == "__main__":
    main()
