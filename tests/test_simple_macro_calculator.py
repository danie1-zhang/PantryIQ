import pandas as pd

from src.optimizer.simple_macro_calculator import calculate_totals


def test_calculate_totals():
    foods = pd.DataFrame(
        [
            {
                "calories": 100,
                "protein": 17,
                "carbs": 6,
                "fat": 0,
                "sodium_mg": 60,
                "cost_usd": 1.25,
            },
            {
                "calories": 165,
                "protein": 31,
                "carbs": 0,
                "fat": 3.6,
                "sodium_mg": 74,
                "cost_usd": 1.80,
            },
        ]
    )

    totals = calculate_totals(foods)

    assert totals["calories"] == 265
    assert totals["protein"] == 48
    assert totals["carbs"] == 6
    assert totals["fat"] == 3.6
    assert totals["sodium_mg"] == 134
    assert totals["cost_usd"] == 3.05
