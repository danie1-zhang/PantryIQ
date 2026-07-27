# Pantry Meal Optimizer

A pantry-based nutrition optimization system that recommends the highest-scoring meal a user can make from the foods currently available in their pantry.

---

## Motivation

Meal planning is often treated as a search problem:

> Given the foods currently available and a set of nutrition goals, what is the best meal to eat?

This project explores that problem by combining pantry management, nutrition evaluation, and optimization.

Version 1 focuses on building the optimization pipeline before introducing databases, machine learning, or web infrastructure.

---

## Features

- Food catalog
- Pantry management
- Nutrition constraint evaluation
- Randomized candidate meal generation
- Meal feasibility scoring
- Best meal selection
- Pantry updates after meal acceptance
- Unit tests

---

## Project Structure

```
.
├── data/
│   └── food_catalog.csv
│
├── docs/
│   └── v1_decision_log.md
│
├── src/
│   ├── database/
│   │   ├── pantry.py
│   │   └── user.py
│   │
│   └── optimizer/
│       ├── nutrition_constraints.py
│       └── best_meal.py
│
└── tests/
```

---

## How It Works

```
Food Catalog
      │
      ▼
 Pantry
      │
      ▼
Generate Candidate Meals
      │
      ▼
Evaluate Nutrition Constraints
      │
      ▼
Score Each Candidate
      │
      ▼
Return Highest Scoring Meal
```

---

## Optimization Pipeline

Each candidate meal is represented as

```python
{
    "food_id": servings
}
```

For every generated candidate, the system

1. calculates nutrition totals
2. evaluates constraints
3. computes a feasibility score
4. ranks the candidate

After evaluating many candidates, the optimizer returns the highest-scoring feasible meal.

If no feasible meal exists, the highest-scoring infeasible meal is returned along with a disclaimer.

---

## Current Constraints

Required

- Calories
- Protein
- Carbohydrates
- Fat

Optional

- Sodium
- Sugar
- Cost

---

## Current Architecture

The project currently consists of four primary components.

### Pantry

Stores and manages the user's available foods.

### Nutrition Constraint Evaluator

Scores individual candidate meals.

### Meal Optimizer

Generates candidate meals and returns the best one found.

### User

Coordinates the entire application and user interaction.

---

## Current Limitations

Version 1 intentionally keeps the system simple.

Current limitations include

- manually maintained food catalog
- CSV storage
- randomized search
- no database
- no frontend
- no deployment
- one meal optimization only
- no learned user preferences

---

## Future Work

Planned improvements include

- PostgreSQL storage
- automated food ingestion
- better optimization algorithms
- continuous serving optimization
- REST API
- web frontend
- user accounts
- machine learning preference model
- LLM-powered meal assistant

---

## Purpose

This project is primarily intended as a learning project exploring

- optimization
- software architecture
- data engineering
- machine learning integration
- full-stack application development

The long-term goal is to evolve this project into a production-style nutrition recommendation system.