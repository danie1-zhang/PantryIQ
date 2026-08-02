import { useState } from "react";
import { errorMessage } from "../api/client";
import type { MealRecommendation } from "../types/api";

export function MealRecommendationCard({
  meal,
  accepting,
  acceptError,
  onAccept,
  onRegenerate,
}: {
  meal: MealRecommendation;
  accepting: boolean;
  acceptError?: unknown;
  onAccept: (rating: number | null, notes: string) => void;
  onRegenerate: () => void;
}) {
  const [rating, setRating] = useState("");
  const [notes, setNotes] = useState("");
  const totals = meal.totals;
  return (
    <section className="recommendation card">
      <div className="recommendation-heading">
        <div>
          <p className="eyebrow">Your recommendation</p>
          <h2>{meal.is_feasible ? "A strong pantry match" : "Closest available match"}</h2>
        </div>
        <div className={`score-badge ${meal.is_feasible ? "score-good" : "score-near"}`}>
          <strong>{meal.feasibility_score}</strong>
          <span>score</span>
        </div>
      </div>
      <div className="solver-metadata" aria-label="Optimization details">
        <span>
          Method <strong>{meal.optimization_method === "cp_sat" ? "CP-SAT" : "Random"}</strong>
        </span>
        <span>
          Status <strong>{meal.solver_status}</strong>
        </span>
        <span>
          Solve time <strong>{meal.solve_time_seconds.toFixed(3)}s</strong>
        </span>
      </div>
      <div className="meal-foods">
        {meal.items.map((item) => (
          <div key={item.food_id}>
            <span>{item.food_name}</span>
            <strong>
              {item.servings} serving{item.servings === 1 ? "" : "s"}
            </strong>
          </div>
        ))}
      </div>
      <div className="nutrition-strip">
        <div>
          <strong>{totals.calories}</strong>
          <span>Calories</span>
        </div>
        <div>
          <strong>{totals.protein_g}g</strong>
          <span>Protein</span>
        </div>
        <div>
          <strong>{totals.carbs_g}g</strong>
          <span>Carbs</span>
        </div>
        <div>
          <strong>{totals.fat_g}g</strong>
          <span>Fat</span>
        </div>
        <div>
          <strong>{totals.sodium_mg}mg</strong>
          <span>Sodium</span>
        </div>
        {totals.cost !== null && (
          <div>
            <strong>${totals.cost.toFixed(2)}</strong>
            <span>Cost</span>
          </div>
        )}
      </div>
      <div className="constraint-list">
        {Object.entries(meal.constraints_met).map(([name, met]) => (
          <span className={met ? "constraint-met" : "constraint-missed"} key={name}>
            {met ? "✓" : "×"} {name}
          </span>
        ))}
      </div>
      {Object.keys(meal.constraint_violations).length > 0 && (
        <div className="violation-summary">
          <strong>Constraint misses</strong>
          <ul>
            {Object.entries(meal.constraint_violations).map(([name, amount]) => (
              <li key={name}>
                {name}: {amount}
              </li>
            ))}
          </ul>
        </div>
      )}
      {meal.preference_summary.length > 0 && (
        <div className="violation-summary">
          <strong>Preference interpretation</strong>
          <ul>
            {meal.preference_summary.map((line) => (
              <li key={line}>{line}</li>
            ))}
          </ul>
        </div>
      )}
      {meal.excluded_foods.length > 0 && (
        <div className="violation-summary">
          <strong>Foods excluded by your request</strong>
          <ul>
            {meal.excluded_foods.map((food) => (
              <li key={food.food_id}>
                {food.food_name}: {food.reason}
              </li>
            ))}
          </ul>
        </div>
      )}
      <p className="disclaimer">{meal.disclaimer}</p>
      <div className="accept-fields">
        <div className="field">
          <label htmlFor="meal-rating">
            Rating <span>optional</span>
          </label>
          <select id="meal-rating" value={rating} onChange={(e) => setRating(e.target.value)}>
            <option value="">No rating</option>
            {[1, 2, 3, 4, 5].map((value) => (
              <option key={value} value={value}>
                {value} / 5
              </option>
            ))}
          </select>
        </div>
        <div className="field">
          <label htmlFor="meal-notes">
            Notes <span>optional</span>
          </label>
          <input
            id="meal-notes"
            maxLength={2000}
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            placeholder="How did it turn out?"
          />
        </div>
      </div>
      {Boolean(acceptError) && (
        <p className="form-error" role="alert">
          {errorMessage(acceptError)}
        </p>
      )}
      <div className="form-actions">
        <button className="button button-secondary" onClick={onRegenerate} disabled={accepting}>
          Generate another
        </button>
        <button
          className="button button-primary"
          onClick={() => onAccept(rating ? Number(rating) : null, notes)}
          disabled={accepting}
        >
          {accepting ? "Accepting…" : "Accept meal"}
        </button>
      </div>
    </section>
  );
}
