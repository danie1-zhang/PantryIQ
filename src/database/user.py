from __future__ import annotations
import re
from pathlib import Path
from database.pantry import Pantry
from optimizer.best_meal import MealOptimizer, OptimizerResult
from optimizer.nutrition_constraints import NutritionConstraints


class User:
    "Represent a user and coordinate their pantry and meal optimizer."

    def __init__(self, name: str, age: int, height_inches: float, weight_pounds: float, pantry: Pantry) -> None:
        if not name.strip():
            raise ValueError("User name cannot be empty.")

        if age <= 0:
            raise ValueError("Age must be greater than zero.")

        if height_inches <= 0:
            raise ValueError("Height must be greater than zero.")

        if weight_pounds <= 0:
            raise ValueError("Weight must be greater than zero.")

        self.name = name.strip()
        self.age = age
        self.height_inches = height_inches
        self.weight_pounds = weight_pounds
        self.pantry = pantry


    @classmethod
    def create_new(cls, *,name: str, age: int, height_inches: float, weight_pounds: float, food_catalog_path: str | Path, pantry_path: str | Path | None = None) -> User:
        "Create a new user with an empty pantry."
        if pantry_path is None:
            pantry_path = cls._default_pantry_path(name)
        pantry = Pantry.empty(food_catalog_path=food_catalog_path, pantry_path=pantry_path)
        return cls(name=name, age=age, height_inches=height_inches, weight_pounds=weight_pounds, pantry=pantry)


    @classmethod
    def from_existing_pantry(cls, *, name: str, age: int, height_inches: float, weight_pounds: float, pantry_path: str | Path, food_catalog_path: str | Path,) -> User:
        "Create a user by loading an existing pantry CSV."
        pantry = Pantry.from_csv(
            pantry_path=pantry_path,
            food_catalog_path=food_catalog_path,
        )
        return cls(name=name, age=age, height_inches=height_inches, weight_pounds=weight_pounds, pantry=pantry,)


    @classmethod
    def create_interactively(cls, food_catalog_path: str | Path,) -> User:
        "Prompt for basic information and create a new user."
        print("\nCreate your nutrition profile")
        name = cls._prompt_nonempty_string("Name: ")
        age = cls._prompt_positive_int("Age: ")
        height_inches = cls._prompt_positive_float("Height in inches: ")
        weight_pounds = cls._prompt_positive_float("Weight in pounds: ")
        return cls.create_new(name=name, age=age, height_inches=height_inches, weight_pounds=weight_pounds, food_catalog_path=food_catalog_path,)


    def run(self) -> None:
        "Run the V1 command-line user menu."
        print(f"\nWelcome, {self.name}.")

        while True:
            self._display_actions()
            choice = input("Select an action: ").strip()
            if choice == "1":
                self.add_foods()
            elif choice == "2":
                self.view_available_items()
            elif choice == "3":
                self.generate_best_meal()
            elif choice == "4":
                self.view_profile()
            elif choice == "5":
                self.save_pantry()
            elif choice == "6":
                self.save_pantry()
                print("Pantry saved. Goodbye.")
                return
            else:
                print("Please select a number from 1 through 6.")


    def add_foods(self) -> None:
        "Use the Pantry input workflow to add one or more foods."
        self.pantry.input_foods()
        if self._prompt_yes_no("Save pantry changes now? (y/n): "):
            self.save_pantry()


    def view_available_items(self) -> None:
        "Display available pantry items and quantities."
        available = self.pantry.available_items_df()
        if available.empty:
            print("\nYour pantry is currently empty.")
            return

        display_columns = [
            "food_nm",
            "servings",
            "max_servings",
            "category",
            "calories_per_serving",
            "protein_g_per_serving"
        ]

        optional_columns = [
            "carbs_g_per_serving",
            "fat_g_per_serving",
            "sugar_g_per_serving",
            "sodium_mg_per_serving",
            "cost_per_serving"
        ]

        display_columns.extend(column for column in optional_columns if column in available.columns)
        print("\nAvailable pantry items:")
        print(available[display_columns].to_string(index=False))
        print(f"\nUnique available items: {self.pantry.number_of_unique_items()}")

    def generate_best_meal(self) -> OptimizerResult | None:
        "Prompt for constraints and generate the best meal found."
        available_foods = self.pantry.available_items_df()
        if available_foods.empty:
            print("\nYour pantry has no available foods. Add food before generating a meal.")
            return None

        constraints = self._prompt_meal_constraints()
        number_of_candidates = self._prompt_positive_int("How many candidate meals should be generated? [Recommended: 10000]: ", default=10_000)
        optimizer = MealOptimizer(pantry_foods=available_foods, constraints=constraints, random_seed=42)

        try:
            result = optimizer.find_best_meal(number_of_candidates=number_of_candidates)
        except (ValueError, RuntimeError) as exc:
            print(f"\nCould not generate a meal: {exc}")
            return None

        self._display_meal_result(result)
        if self._prompt_yes_no("\nWould you like to accept and consume this meal? (y/n): "):
            self.accept_meal(result.meal)
        else:
            print("Meal was not accepted. Pantry quantities were unchanged.")
        return result


    def accept_meal(self, meal: dict[str, float],) -> None:
        "Deduct an accepted meal's servings from the pantry."
        if not meal:
            raise ValueError("Cannot accept an empty meal.")

        pantry_items = self.pantry.pantry_items

        # Validate every item before changing any quantities.
        for food_item_id, servings_used in meal.items():
            matching_rows = pantry_items[pantry_items["food_item_id"].astype(str) == str(food_item_id)]
            if matching_rows.empty:
                raise ValueError(f"Food '{food_item_id}' is no longer in the pantry.")

            row_index = matching_rows.index[0]
            available_servings = float(pantry_items.at[row_index, "servings"])

            if servings_used <= 0:
                raise ValueError(f"Meal contains an invalid serving amount for {food_item_id}'.")

            if servings_used > available_servings:
                raise ValueError(f"Meal requires {servings_used:g} servings of {food_item_id}', but only {available_servings:g} are available.")

        # All items are valid, so it is now safe to mutate the pantry.
        for food_item_id, servings_used in meal.items():
            matching_mask = (pantry_items["food_item_id"].astype(str) == str(food_item_id))
            row_index = pantry_items.index[matching_mask][0]
            current_servings = float(pantry_items.at[row_index, "servings"])
            remaining_servings = round(current_servings - servings_used, 2)
            pantry_items.at[row_index, "servings"] = remaining_servings
            current_max = float(pantry_items.at[row_index, "max_servings"])
            pantry_items.at[row_index, "max_servings"] = min(current_max, remaining_servings)
            pantry_items.at[row_index, "is_available"] = remaining_servings > 0

        # Rebuild the pantry + nutrition joined DataFrame.
        self.pantry._refresh_nutrition_facts()
        self.save_pantry()

        print("\nMeal accepted.")
        print("Consumed servings were deducted from your pantry.")


    def save_pantry(self) -> None:
        "Save the user's pantry to its configured CSV path."
        try:
            saved_path = self.pantry.save()
        except ValueError as exc:
            print(f"Could not save pantry: {exc}")
            return
        print(f"Pantry saved to: {saved_path}")


    def view_profile(self) -> None:
        "Display basic personal information."
        feet = int(self.height_inches // 12)
        inches = self.height_inches % 12
        print("\nUser profile")
        print(f"Name: {self.name}")
        print(f"Age: {self.age}")
        print(f"Height: {feet}'{inches:g}\"")
        print(f"Weight: {self.weight_pounds:g} pounds")
        print(f"Unique pantry items: {self.pantry.number_of_unique_items()}")


    def _prompt_meal_constraints(self) -> NutritionConstraints:
        "Collect required and optional meal constraints."
        print("\nEnter your desired nutrition targets for this meal.")
        calorie_goal = self._prompt_positive_float("Calorie goal: ")
        protein_goal = self._prompt_positive_float("Protein goal in grams: ")
        carbs_goal = self._prompt_positive_float("Carbohydrate goal in grams: ")
        fat_goal = self._prompt_positive_float("Fat goal in grams: ")
        sodium_max = self._prompt_optional_constraint(name="sodium", unit="milligrams")
        sugar_max = self._prompt_optional_constraint(name="sugar", unit="grams")
        cost_max = self._prompt_optional_constraint(name="cost", unit="dollars")

        return NutritionConstraints(
            calorie_goal=calorie_goal,
            protein_goal=protein_goal,
            carbs_goal=carbs_goal,
            fat_goal=fat_goal,
            sodium_max=sodium_max,
            sugar_max=sugar_max,
            cost_max=cost_max,
        )


    @classmethod
    def _prompt_optional_constraint(cls, name: str, unit: str,) -> float | None:
        use_constraint = cls._prompt_yes_no(f"Would you like to set a maximum {name} constraint? (y/n): ")
        if not use_constraint:
            return None
        return cls._prompt_nonnegative_float(f"Maximum {name} in {unit}: ")
        

    def _display_meal_result(self, result: OptimizerResult,) -> None:
        "Display the selected meal and its evaluation."
        evaluation = result.evaluation
        status = ("FEASIBLE MEAL FOUND" if evaluation.is_feasible else "NO FULLY FEASIBLE MEAL FOUND")
        food_name_lookup = self._food_name_lookup()

        print(f"\n{status}")
        print("\nSelected meal:")

        for food_item_id, servings in result.meal.items():
            food_name = food_name_lookup.get(str(food_item_id), str(food_item_id),)
            print(f"- {food_name}: {servings:g} serving(s)")

        totals = evaluation.totals
        print("\nNutrition totals:")
        print(f"- Calories: {totals['calories']:g}")
        print(f"- Protein: {totals['protein_g']:g} g")
        print(f"- Carbohydrates: {totals['carbs_g']:g} g")
        print(f"- Fat: {totals['fat_g']:g} g")
        print(f"- Sugar: {totals['sugar_g']:g} g")
        print(f"- Sodium: {totals['sodium_mg']:g} mg")
        print(f"- Cost: ${totals['cost']:.2f}")
        print(f"\nFeasibility score: {evaluation.feasibility_score:.2f}/100")
        print("\nConstraints:")
        for name, was_met in evaluation.constraints_met.items():
            marker = "met" if was_met else "not met"
            print(f"- {name.title()}: {marker}")

        print(f"\nGenerated {result.candidates_generated:,} candidates; evaluated {result.valid_candidates_evaluated:,} structurally valid candidates.")
        if not evaluation.is_feasible:
            print("\nDisclaimer: No fully feasible meal was found. This is the highest-scoring near-feasible candidate found by the V1 randomized optimizer.")
        else:
            print("\nDisclaimer: This is the best meal found by the V1 randomized search, not a guaranteed global optimum.")


    def _food_name_lookup(self) -> dict[str, str]:
        available = self.pantry.available_items_df()
        return dict(
            zip(available["food_item_id"].astype(str), available["food_nm"].astype(str),))


    @staticmethod
    def _display_actions() -> None:
        print("\nAvailable actions")
        print("1. Add food")
        print("2. View available pantry items")
        print("3. Generate best meal")
        print("4. View user profile")
        print("5. Save pantry")
        print("6. Save and exit")


    @staticmethod
    def _default_pantry_path(name: str) -> Path:
        """Create a safe default pantry filename from the user's name."""
        safe_name = re.sub(pattern=r"[^a-zA-Z0-9_-]+", repl="_", string=name.strip().lower()).strip("_")
        if not safe_name:
            safe_name = "user"
        project_root = Path(__file__).resolve().parents[2]
        return (project_root/"data"/"pantries"/ f"{safe_name}_pantry.csv")
        

    @staticmethod
    def _prompt_nonempty_string(prompt: str) -> str:
        while True:
            value = input(prompt).strip()
            if value:
                return value
            print("This value cannot be empty.")


    @staticmethod
    def _prompt_positive_float(prompt: str) -> float:
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


    @staticmethod
    def _prompt_nonnegative_float(prompt: str) -> float:
        while True:
            raw_value = input(prompt).strip()
            try:
                value = float(raw_value)
            except ValueError:
                print("Please enter a valid number.")
                continue
            if value < 0:
                print("Please enter zero or a positive number.")
                continue
            return value


    @staticmethod
    def _prompt_positive_int(prompt: str, default: int | None = None,) -> int:
        while True:
            raw_value = input(prompt).strip()
            if not raw_value and default is not None:
                return default
            try:
                value = int(raw_value)
            except ValueError:
                print("Please enter a whole number.")
                continue
            if value <= 0:
                print("Please enter a number greater than zero.")
                continue
            return value


    @staticmethod
    def _prompt_yes_no(prompt: str) -> bool:
        while True:
            response = input(prompt).strip().lower()
            if response == "y":
                return True
            if response == "n":
                return False
            print("Please enter 'y' or 'n'.")
