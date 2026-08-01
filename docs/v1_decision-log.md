# Pantry Meal Optimizer – V1 Decision Log

## Overview

This document records the major architectural and implementation decisions made during Version 1 (V1) of the Pantry Meal Optimizer.

The goal of V1 is to demonstrate the complete end-to-end workflow of:

Food Catalog → Pantry → Candidate Meal Generation → Nutrition Evaluation → Best Meal Selection

V1 intentionally prioritizes correctness and modularity over scalability or optimal performance.

---

# V1 Scope

### Included

- Food catalog stored in CSV format
- Pantry creation and management
- Nutrition constraint evaluation
- Randomized meal generation
- Meal scoring
- Best meal selection
- Pantry updates after meal acceptance
- Unit tests

### Not Included

- Database
- API
- Frontend
- User authentication
- Learned user preferences
- LLM integration
- Continuous serving optimization
- Global optimization algorithms

---

# Food Storage

## Decision

Use a manually created CSV food catalog.

## Reasoning

The project focuses on optimization rather than data collection.

A CSV allows development of the optimization pipeline before introducing a database.

## Future

Replace with a relational food database and automated nutrition data ingestion.

---

# Pantry Representation

## Decision

Represent each user's pantry as a pandas DataFrame stored inside a Pantry object.

## Reasoning

The pantry is naturally tabular and closely resembles the relational table that will later exist in the database.

---

# Candidate Meal Representation

## Decision

Represent a meal as

```python
{
    "food_id": servings
}
```

Example:

```python
{
    "chicken": 1.5,
    "rice": 2,
    "broccoli": 1
}
```

## Reasoning

This representation is compact, easy to manipulate, and can be passed between modules without additional conversion.

---

# Nutrition Evaluation

## Decision

Evaluate each candidate independently.

Outputs:

- nutrition totals
- constraint satisfaction
- feasibility score
- feasible / infeasible indicator

## Reasoning

Separating meal evaluation from meal generation allows different optimization algorithms to reuse the same scoring system.

---

# Meal Scoring

Calories

- closer to target is better

Protein

- reaching the goal is sufficient
- exceeding the goal is not penalized

Carbohydrates

- closer to target is better

Fat

- closer to target is better

Optional Constraints

- sodium
- sugar
- cost

Lower values are preferred.

---

# Candidate Generation

## Decision

Generate a fixed number of randomized candidate meals.

## Reasoning

Brute force search becomes computationally infeasible as pantry size increases.

Random search provides a simple baseline while allowing the optimization pipeline to be developed.

---

# Meal Structure Rules

Candidate meals should resemble realistic meals.

Current rules include:

- must contain a protein
- must contain either a carbohydrate or produce item
- limited number of protein sources
- limited condiments
- serving limits respected

These rules are intentionally simple and will evolve.

---

# Selecting the Best Meal

The optimizer:

1. generates many candidate meals
2. evaluates each candidate
3. prefers feasible meals
4. otherwise returns the highest-scoring infeasible meal

If no feasible meal exists, a disclaimer is returned.

---

# User Interaction

The User class coordinates the entire application.

Responsibilities include:

- storing user information
- managing the pantry
- collecting meal constraints
- invoking the optimizer
- accepting meals
- updating pantry quantities

Business logic remains inside the Pantry and Optimizer classes.

---

# Testing

V1 includes unit tests for

- Pantry
- Nutrition Constraints
- Optimizer
- User

Testing is intended to support future refactoring.

---

# Known Limitations

Current optimization is randomized.

The optimizer is not guaranteed to find the mathematically optimal meal.

Food data is manually maintained.

Only one meal is optimized at a time.

No preference learning is performed.

No deployment or persistence beyond CSV storage exists.

---

# Planned V2 Improvements

- PostgreSQL database
- automated food ingestion
- improved optimization algorithms
- adjustable serving optimization
- user authentication
- REST API
- frontend
- FastAPI backend
- learned preferences
- LLM powered assistant