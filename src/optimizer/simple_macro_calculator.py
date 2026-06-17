from pathlib import Path
import pandas as pd

NUTRIENTS_COLUMNS = ["calories", "protein", "carbs", "fat", "sodium_mg", "cost_usd"]


def load_foods(csv_path: str | Path) -> pd.DataFrame:
    "load food data from a csv file"
    path = Path(csv_path)
    if not path.exists():
        raise FileNotFoundError(f"Food csv not found: {path}")

    foods = pd.read_csv(path)

    required_columns = {
        "food_name",
        "serving_size",
        "serving_unit",
        "calories",
        "protein",
        "carbs",
        "fat",
        "sodium_mg",
        "cost_usd",
        "category",
        "source",
    }

    missing = required_columns - set(foods.columns)
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    return foods


def calculate_totals(selected_foods: pd.DataFrame) -> dict[str, float]:
    totals = selected_foods[NUTRIENTS_COLUMNS].sum()
    return {column: round(float(totals[column]), 2) for column in NUTRIENTS_COLUMNS}


def rank_by_protein_per_calorie(foods: pd.DataFrame) -> pd.DataFrame:
    protein_ranked = foods.copy()
    protein_ranked["protein_per_calorie"] = (
        protein_ranked["protein"] / protein_ranked["calories"]
    )
    return protein_ranked.sort_values("protein_per_calorie", ascending=False)


def rank_by_protein_per_dollar(foods: pd.DataFrame) -> pd.DataFrame:
    protein_ranked = foods.copy()
    protein_ranked["protein_per_dollar"] = (
        protein_ranked["protein"] / protein_ranked["cost_usd"]
    )
    return protein_ranked.sort_values("protein_per_dollar", ascending=False)


if __name__ == "__main__":
    foods_df = load_foods(
        "/Users/kyle/Projects/nutrition-optimizer/data/sample/foods_sample.csv"
    )

    print("foods ranked by protein per calorie")
    print(
        rank_by_protein_per_calorie(foods_df)[
            ["food_name", "protein_per_calorie"]
        ].head()
    )

    print("foods ranked by protein per dollar")
    print(
        rank_by_protein_per_dollar(foods_df)[["food_name", "protein_per_dollar"]].head()
    )

    selected = foods_df[
        foods_df["food_name"].isin(["Greek yogurt", "Chicken breast", "Eggs"])
    ]
    print("\nExample meal totals: ")
    print(calculate_totals(selected))
