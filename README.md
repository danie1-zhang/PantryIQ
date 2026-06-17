# Personalized Nutrition Optimizer

An end-to-end nutrition data platform that turns messy food data into optimized, explainable meal plans.

## North Star

Given my calorie, protein, budget, preferences, and food availability, what should I eat today — and why?

## Planned System

Raw food/menu/user data → cleaned nutrition database → analytics/feature tables → optimizer/recommender → app/API → user logs/ratings → feedback loop → grounded AI assistant.

## Current Version

Version 1: Python nutrition calculator and simple food ranking.

Current features:
- Load foods from CSV
- Calculate meal totals
- Rank foods by protein per calorie
- Rank foods by protein per dollar
- Unit tests for macro calculations

## Tech Stack

Current:
- Python
- pandas
- pytest
- ruff
- black
- uv

Planned:
- SQLite/PostgreSQL
- SQLAlchemy
- FastAPI
- Streamlit
- OR-Tools
- scikit-learn
- Docker
- LLM tool-calling assistant

## Project Structure

```text
data/
  raw/
  processed/
  sample/
src/
  ingestion/
  transforms/
  database/
  validation/
  optimizer/
  recommender/
  api/
  app/
  ai/
tests/