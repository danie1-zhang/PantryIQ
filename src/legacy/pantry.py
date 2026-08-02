from __future__ import annotations
from datetime import date
from pathlib import Path
from typing import Any
import pandas as pd


class Pantry:
    """
    Represent a user's available pantry items.

    The pantry stores inventory information such as available servings,
    dates, and notes. Nutrition facts remain in the food catalog and are
    joined onto the pantry when needed.
    """

    PANTRY_COLS = [
        "food_item_id",
        "food_nm",
        "servings",
        "max_servings",
        "is_available",
        "date_added",
        "notes",
    ]

    # Columns expected after normalizing the food catalog.
    CATALOG_COLS = [
        "food_item_id",
        "food_nm",
        "category",
        "serving_size",
        "serving_unit",
        "calories_per_serving",
        "protein_g_per_serving",
        "carbs_g_per_serving",
        "fat_g_per_serving",
        "sugar_g_per_serving",
        "sodium_mg_per_serving",
        "cost_per_serving",
        "source",
    ]

    # Columns exposed by the joined nutrition DataFrame.
    ITEMS_COLS = [
        "food_item_id",
        "food_nm",
        "category",
        "servings",
        "max_servings",
        "serving_size",
        "serving_unit",
        "calories_per_serving",
        "protein_g_per_serving",
        "carbs_g_per_serving",
        "fat_g_per_serving",
        "sugar_g_per_serving",
        "sodium_mg_per_serving",
        "cost_per_serving",
        "is_available",
        "date_added",
        "notes",
    ]

    # Allows the class to accept several reasonable CSV naming conventions.
    CATALOG_COLUMN_ALIASES = {
        "food_id": "food_item_id",
        "food_name": "food_nm",
        "calories": "calories_per_serving",
        "protein_g": "protein_g_per_serving",
        "carbs_g": "carbs_g_per_serving",
        "fat_g": "fat_g_per_serving",
        "sugar_g": "sugar_g_per_serving",
        "sodium_mg": "sodium_mg_per_serving",
        "cost": "cost_per_serving",
    }

    def __init__(
        self,
        food_catalog: pd.DataFrame,
        pantry_items: pd.DataFrame | None = None,
        pantry_path: str | Path | None = None,
    ) -> None:
        """
        Create a pantry using a loaded food catalog.

        Args:
            food_catalog:
                DataFrame containing recognized foods and nutrition facts.
            pantry_items:
                Existing pantry inventory. An empty pantry is created when
                this argument is omitted.
            pantry_path:
                Optional path used by save(). This does not automatically
                write a file.
        """
        self.food_catalog = self._prepare_food_catalog(food_catalog)
        self.pantry_items = self._prepare_pantry_items(pantry_items)
        self.pantry_path = Path(pantry_path) if pantry_path else None

        self.items_nutrition_facts = pd.DataFrame(columns=self.ITEMS_COLS)
        self._refresh_nutrition_facts()

    @staticmethod
    def default_food_catalog_path() -> Path:
        "Return the default food catalog path relative to this file."
        project_root = Path(__file__).resolve().parents[2]
        return project_root / "data" / "food_catalog.csv"

    @classmethod
    def empty(
        cls, food_catalog_path: str | Path | None = None, pantry_path: str | Path | None = None
    ) -> Pantry:
        "Create an empty pantry backed by a food catalog."
        catalog_path = (
            Path(food_catalog_path) if food_catalog_path else cls.default_food_catalog_path()
        )
        food_catalog = cls._read_csv(catalog_path, "food catalog")
        return cls(
            food_catalog=food_catalog,
            pantry_items=None,
            pantry_path=pantry_path,
        )

    @classmethod
    def from_csv(
        cls, pantry_path: str | Path, food_catalog_path: str | Path | None = None
    ) -> Pantry:
        "Load an existing pantry CSV and its food catalog."
        pantry_path = Path(pantry_path)
        catalog_path = (
            Path(food_catalog_path) if food_catalog_path else cls.default_food_catalog_path()
        )
        pantry_items = cls._read_csv(pantry_path, "pantry")
        food_catalog = cls._read_csv(catalog_path, "food catalog")
        return cls(
            food_catalog=food_catalog,
            pantry_items=pantry_items,
            pantry_path=pantry_path,
        )

    @staticmethod
    def _read_csv(path: Path, description: str) -> pd.DataFrame:
        if not path.exists():
            raise FileNotFoundError(f"The {description} CSV was not found at: {path}")
        try:
            return pd.read_csv(path)
        except pd.errors.EmptyDataError as exc:
            raise ValueError(f"The {description} CSV is empty: {path}") from exc
        except pd.errors.ParserError as exc:
            raise ValueError(f"The {description} CSV could not be parsed: {path}") from exc

    def _prepare_food_catalog(self, food_catalog: pd.DataFrame) -> pd.DataFrame:
        "Normalize and validate food catalog columns."
        catalog = food_catalog.copy()
        catalog = catalog.rename(columns=self.CATALOG_COLUMN_ALIASES)

        required_columns = {"food_item_id", "food_nm"}
        missing = required_columns - set(catalog.columns)

        if missing:
            raise ValueError("Food catalog is missing required columns: " f"{sorted(missing)}")

        # Add optional columns that are not yet present.
        for column in self.CATALOG_COLS:
            if column not in catalog.columns:
                catalog[column] = pd.NA

        catalog = catalog[self.CATALOG_COLS].copy()

        if catalog["food_item_id"].isna().any():
            raise ValueError("Food catalog contains a missing food_item_id.")

        if catalog["food_nm"].isna().any():
            raise ValueError("Food catalog contains a missing food_nm.")

        if catalog["food_item_id"].duplicated().any():
            duplicate_ids = catalog.loc[
                catalog["food_item_id"].duplicated(),
                "food_item_id",
            ].tolist()
            raise ValueError(f"Food catalog contains duplicate IDs: {duplicate_ids}")

        numeric_columns = [
            "serving_size",
            "calories_per_serving",
            "protein_g_per_serving",
            "carbs_g_per_serving",
            "fat_g_per_serving",
            "sugar_g_per_serving",
            "sodium_mg_per_serving",
            "cost_per_serving",
        ]

        for column in numeric_columns:
            catalog[column] = pd.to_numeric(catalog[column], errors="coerce")
            if (catalog[column].dropna() < 0).any():
                raise ValueError(f"Food catalog column '{column}' contains negative values.")

        catalog["food_item_id"] = catalog["food_item_id"].astype(str).str.strip()
        catalog["food_nm"] = catalog["food_nm"].astype(str).str.strip()

        return catalog.reset_index(drop=True)

    def _prepare_pantry_items(self, pantry_items: pd.DataFrame | None) -> pd.DataFrame:
        "Create or validate the pantry inventory DataFrame."
        if pantry_items is None:
            return pd.DataFrame(columns=self.PANTRY_COLS)

        pantry = pantry_items.copy()

        missing = set(self.PANTRY_COLS) - set(pantry.columns)
        if missing:
            raise ValueError(f"Pantry data is missing columns: {sorted(missing)}")

        pantry = pantry[self.PANTRY_COLS].copy()

        pantry["servings"] = pd.to_numeric(pantry["servings"], errors="raise")

        pantry["max_servings"] = pd.to_numeric(pantry["max_servings"], errors="raise")

        if (pantry["servings"] < 0).any():
            raise ValueError("Pantry servings cannot be negative.")

        if (pantry["max_servings"] < 0).any():
            raise ValueError("Pantry max_servings cannot be negative.")

        if (pantry["max_servings"] > pantry["servings"]).any():
            raise ValueError("A pantry item's max_servings cannot exceed its available servings.")

        unknown_ids = set(pantry["food_item_id"].astype(str)) - set(
            self.food_catalog["food_item_id"].astype(str)
        )

        if unknown_ids:
            raise ValueError(
                "Pantry contains food IDs not found in the catalog: " f"{sorted(unknown_ids)}"
            )

        pantry["is_available"] = (
            pantry["is_available"]
            .astype(str)
            .str.strip()
            .str.lower()
            .map(
                {
                    "true": True,
                    "false": False,
                    "1": True,
                    "0": False,
                    "yes": True,
                    "no": False,
                }
            )
        )

        if pantry["is_available"].isna().any():
            raise ValueError("is_available must contain true/false values.")

        pantry["date_added"] = pd.to_datetime(
            pantry["date_added"],
            errors="coerce",
        ).dt.date
        pantry["notes"] = pantry["notes"].fillna("")
        return pantry.reset_index(drop=True)

    def add_food(
        self,
        food_query: str,
        servings: float,
        max_servings: float | None = None,
        notes: str = "",
        date_added: date | None = None,
    ) -> None:
        """
        Add a recognized food to the pantry. 'Food_query' may be either a food ID or a food name. If the food already exists in the pantry, its available servings are
        increased instead of creating a duplicate pantry row.
        """
        if servings <= 0:
            raise ValueError("servings must be greater than zero.")

        if max_servings is None:
            max_servings = servings

        if max_servings <= 0:
            raise ValueError("max_servings must be greater than zero.")

        if max_servings > servings:
            raise ValueError("max_servings cannot exceed the available servings being added.")

        catalog_food = self._find_catalog_food(food_query)

        food_item_id = str(catalog_food["food_item_id"])
        food_nm = str(catalog_food["food_nm"])
        added_date = date_added or date.today()

        existing_mask = self.pantry_items["food_item_id"].astype(str) == food_item_id

        if existing_mask.any():
            row_index = self.pantry_items.index[existing_mask][0]
            current_servings = float(self.pantry_items.at[row_index, "servings"])
            current_max = float(self.pantry_items.at[row_index, "max_servings"])
            new_total_servings = current_servings + servings
            new_max_servings = min(new_total_servings, max(current_max, max_servings))

            self.pantry_items.at[row_index, "servings"] = new_total_servings
            self.pantry_items.at[row_index, "max_servings"] = new_max_servings
            self.pantry_items.at[row_index, "is_available"] = True

            if notes.strip():
                old_notes = str(self.pantry_items.at[row_index, "notes"] or "").strip()

                self.pantry_items.at[row_index, "notes"] = (
                    f"{old_notes}; {notes.strip()}" if old_notes else notes.strip()
                )
        else:
            new_row = {
                "food_item_id": food_item_id,
                "food_nm": food_nm,
                "servings": float(servings),
                "max_servings": float(max_servings),
                "is_available": True,
                "date_added": added_date,
                "notes": notes.strip(),
            }

            self.pantry_items.loc[len(self.pantry_items)] = new_row

        self._refresh_nutrition_facts()

    def input_foods(self) -> None:
        """
        Interactively ask the user whether they want to add foods.

        This method is useful for the V1 command-line interface. The actual
        pantry logic remains in add_food(), which makes it easier to test and
        reuse from a future API or frontend.
        """
        while True:
            response = input("Would you like to add a food to the pantry? (y/n): ").strip().lower()

            if response == "n":
                print("Finished adding pantry items.")
                return

            if response != "y":
                print("Please enter 'y' or 'n'.")
                continue

            food_query = input("Enter the food name or food ID: ").strip()

            try:
                catalog_food = self._find_catalog_food(food_query)
            except ValueError as exc:
                print(exc)
                continue

            print(f"Found: {catalog_food['food_nm']} ({catalog_food['food_item_id']})")

            servings = self._prompt_positive_number("How many servings are currently available? ")
            max_servings = self._prompt_positive_number(
                "What is the maximum number of servings allowed in one meal? "
            )

            if max_servings > servings:
                print("Maximum meal servings cannot exceed available servings. Please try again.")
                continue

            notes = input("Optional notes about this item: ").strip()

            try:
                self.add_food(
                    food_query=food_query,
                    servings=servings,
                    max_servings=max_servings,
                    notes=notes,
                )
            except ValueError as exc:
                print(f"Could not add food: {exc}")
                continue
            print(f"Added {servings:g} serving(s) of {catalog_food['food_nm']}.")

    def _find_catalog_food(self, food_query: str) -> pd.Series:
        "Find one catalog food by exact ID or case-insensitive name."
        query = food_query.strip()

        if not query:
            raise ValueError("Food name or ID cannot be empty.")

        id_matches = self.food_catalog[self.food_catalog["food_item_id"].astype(str) == query]

        if len(id_matches) == 1:
            return id_matches.iloc[0]

        name_matches = self.food_catalog[
            self.food_catalog["food_nm"].astype(str).str.casefold() == query.casefold()
        ]

        if len(name_matches) == 1:
            return name_matches.iloc[0]

        if len(name_matches) > 1:
            matching_ids = name_matches["food_item_id"].tolist()
            raise ValueError(
                f"Multiple foods are named '{query}'. Use one of these IDs: {matching_ids}"
            )

        raise ValueError(f"'{query}' was not found in the food catalog.")

    @staticmethod
    def _prompt_positive_number(prompt: str) -> float:
        while True:
            raw_value = input(prompt).strip()

            try:
                value = float(raw_value)
            except ValueError:
                print("Please enter a valid number.")
                continue

            if value <= 0:
                print("Please enter a number greater than zero.")
                continue

            return value

    def _refresh_nutrition_facts(self) -> None:
        """Join pantry inventory with canonical nutrition information."""
        if self.pantry_items.empty:
            self.items_nutrition_facts = pd.DataFrame(columns=self.ITEMS_COLS)
            return

        catalog_without_name = self.food_catalog.drop(
            columns=["food_nm"],
            errors="ignore",
        )
        joined = self.pantry_items.merge(
            catalog_without_name,
            on="food_item_id",
            how="left",
            validate="many_to_one",
        )
        self.items_nutrition_facts = joined[self.ITEMS_COLS].reset_index(drop=True)

    def available_items(self) -> list[str]:
        "Return the names of all currently available pantry items."
        if self.pantry_items.empty:
            return []
        available = self.pantry_items[
            self.pantry_items["is_available"] & (self.pantry_items["servings"] > 0)
        ]
        return available["food_nm"].tolist()

    def available_items_df(self) -> pd.DataFrame:
        "Return available pantry items joined with nutrition facts."
        if self.items_nutrition_facts.empty:
            return self.items_nutrition_facts.copy()

        return self.items_nutrition_facts[
            self.items_nutrition_facts["is_available"]
            & (self.items_nutrition_facts["servings"] > 0)
        ].reset_index(drop=True)

    def items_with_dates(self) -> list[dict[str, Any]]:
        "Return pantry item names and their dates as dictionaries."
        if self.pantry_items.empty:
            return []
        records = self.pantry_items[["food_item_id", "food_nm", "date_added"]].copy()
        return records.to_dict(orient="records")

    def number_of_unique_items(self) -> int:
        "Return the number of unique foods currently in the pantry."
        if self.pantry_items.empty:
            return 0
        return int(self.pantry_items["food_item_id"].nunique())

    def to_csv(self, path: str | Path | None = None) -> Path:
        """
        Save the pantry inventory to a CSV file.

        Nutrition data is not saved here because it can be reconstructed
        from the canonical food catalog.
        """
        output_path = Path(path) if path else self.pantry_path

        if output_path is None:
            raise ValueError(
                "No pantry CSV path was provided. Pass a path to to_csv() or initialize the Pantry with pantry_path."
            )

        output_path.parent.mkdir(parents=True, exist_ok=True)
        self.pantry_items.to_csv(
            output_path,
            index=False,
            date_format="%Y-%m-%d",
        )
        self.pantry_path = output_path
        return output_path

    def save(self) -> Path:
        "Save to the pantry's existing CSV path."
        return self.to_csv()
