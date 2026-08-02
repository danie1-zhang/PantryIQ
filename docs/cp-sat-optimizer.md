# CP-SAT Meal Optimizer

## Why CP-SAT is the default

The original optimizer samples random meals and keeps the best one it sees. That remains useful as a baseline, but its result depends on the sample and is not guaranteed to be best.

The default optimizer now uses Google OR-Tools CP-SAT. It searches the encoded meal space deterministically, enforces pantry and meal-structure rules, and reports whether the returned solution was proven optimal or was only the best solution found before the time limit.

Use `optimization_method: "random"` to run the original implementation.

## Integer scaling

CP-SAT operates on integers. One serving unit represents half a serving:

```text
0 units = 0 servings
1 unit  = 0.5 servings
2 units = 1 serving
```

Nutrition values are rounded to hundredths and cost is rounded to cents. A total expression multiplies each scaled per-serving value by the number of half-serving units. Goals and maximums are multiplied by the same serving scale, so both sides of every constraint use identical units.

Scaling and unscaling helpers live in `src/optimizer/cp_sat_optimizer.py` and have direct unit tests.

## Meal constraints

Every meal must:

- contain at least one food
- stay within available and per-meal servings
- use no more than six foods or eight total servings by default
- include a protein-category food
- include a carbohydrate or produce food
- include a non-condiment food
- use at most two protein foods and two condiments

Categories are normalized in one place. The current catalog categories are supported, including `protein_carb`. No rules depend on individual food names.

## Strict solve

The first model requires:

- protein at or above its goal
- calories, carbohydrates, and fat within 10% of their targets
- sodium, sugar, and cost at or below their supplied maximums

Its objective minimizes normalized calorie, carbohydrate, and fat deviation. Smaller cost, sodium, sugar, and food count are lower-priority tie breakers. Protein above the minimum is not penalized.

## Relaxed solve

If strict nutrition constraints are infeasible, a second model keeps all pantry and meal-structure rules but adds violation variables. Hard-constraint violations receive much larger weights than ordinary target deviations.

The response is marked `is_feasible: false` and reports the missed constraints and amounts. A structurally impossible pantry still returns a client error instead of inventing a meal.

## Solver status

- `OPTIMAL`: CP-SAT proved the best solution for the encoded model.
- `FEASIBLE`: a valid solution was found, but optimality was not proved in time.
- `INFEASIBLE`: the strict model triggers the relaxed solve; an infeasible relaxed model produces a clear error.
- `MODEL_INVALID`: treated as an implementation failure.
- `UNKNOWN`: returned as a controlled timeout/conflict error.

The request time limit is bounded from 0.1 to 10 seconds and covers strict and relaxed solving together. Solver instances are created per request and never modify the database.

## Independent evaluation

After solving, half-serving units are converted back to servings and the existing nutrition evaluator recalculates totals from canonical food data. It produces the public totals, score, and constraint results. A strict solver result that the evaluator considers infeasible fails loudly.

Meal acceptance is unchanged. The browser sends only food IDs, servings, rating, and notes; FastAPI locks and revalidates pantry rows, recalculates totals, deducts inventory, and writes meal history transactionally.

## Limitations

The optimizer is only optimal for the rules and half-serving choices represented by the model. Mathematical optimality does not guarantee taste, culinary compatibility, preparation convenience, or personal preference.

The Generate Another flow sends up to 20 recommendations from the current page session back as exclusions. CP-SAT adds an exact no-good constraint for each food-and-serving combination, and the random baseline skips matching candidates. This prevents an exact repeat while another structurally valid meal exists. The exclusions are not stored, so they reset when the page reloads; persistent variety would require an approved history or preference design.

The current `Food` table has no `is_active` column, so referenced catalog foods are treated as active. No database migration was needed for this optimizer.
