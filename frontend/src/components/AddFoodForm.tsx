import { useState, type FormEvent } from "react";
import { useFoods } from "../api/foods";
import { useAddPantryItem } from "../api/pantry";
import { errorMessage } from "../api/client";
import type { Food } from "../types/api";

export function AddFoodForm({ onComplete }: { onComplete: () => void }) {
  const [query, setQuery] = useState("");
  const [selected, setSelected] = useState<Food | null>(null);
  const [servings, setServings] = useState("1");
  const [maximum, setMaximum] = useState("1");
  const [expiration, setExpiration] = useState("");
  const [notes, setNotes] = useState("");
  const [validation, setValidation] = useState("");
  const foods = useFoods(query);
  const add = useAddPantryItem();

  function submit(event: FormEvent) {
    event.preventDefault();
    const available = Number(servings);
    const max = Number(maximum);
    if (!selected) return setValidation("Choose a food from the search results.");
    if (available <= 0 || max <= 0) return setValidation("Servings must be greater than zero.");
    if (max > available) return setValidation("Maximum per meal cannot exceed available servings.");
    setValidation("");
    add.mutate(
      {
        food_id: selected.id,
        servings_available: available,
        max_servings_per_meal: max,
        expiration_date: expiration || null,
        notes: notes || null,
      },
      { onSuccess: onComplete },
    );
  }

  return (
    <form className="stack-form" onSubmit={submit} aria-label="Add food to pantry">
      <div className="field">
        <label htmlFor="food-search">Search food catalog</label>
        <input
          id="food-search"
          value={query}
          onChange={(e) => {
            setQuery(e.target.value);
            setSelected(null);
          }}
          placeholder="Try chicken, rice, oats…"
          autoComplete="off"
        />
      </div>
      {foods.isFetching && <p className="muted">Searching…</p>}
      {foods.data && !selected && (
        <div className="search-results">
          {foods.data.length ? (
            foods.data.map((food) => (
              <button
                type="button"
                key={food.id}
                onClick={() => {
                  setSelected(food);
                  setQuery(food.name);
                }}
              >
                <strong>{food.name}</strong>
                <span>
                  {food.brand} · {food.category} · {food.calories_per_serving} cal
                </span>
              </button>
            ))
          ) : (
            <p>No foods found.</p>
          )}
        </div>
      )}
      {selected && (
        <div className="selected-food">
          <span>Selected</span>
          <strong>{selected.name}</strong>
          <small>
            {selected.serving_size} {selected.serving_unit} per serving
          </small>
        </div>
      )}
      <div className="form-grid">
        <div className="field">
          <label htmlFor="add-servings">Servings available</label>
          <input
            id="add-servings"
            type="number"
            min="0.001"
            step="any"
            value={servings}
            onChange={(e) => setServings(e.target.value)}
          />
        </div>
        <div className="field">
          <label htmlFor="add-maximum">Maximum per meal</label>
          <input
            id="add-maximum"
            type="number"
            min="0.001"
            step="any"
            value={maximum}
            onChange={(e) => setMaximum(e.target.value)}
          />
        </div>
        <div className="field">
          <label htmlFor="add-expiration">Expiration date</label>
          <input
            id="add-expiration"
            type="date"
            value={expiration}
            onChange={(e) => setExpiration(e.target.value)}
          />
        </div>
      </div>
      <div className="field">
        <label htmlFor="add-notes">
          Notes <span>optional</span>
        </label>
        <textarea
          id="add-notes"
          maxLength={2000}
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
          placeholder="Storage location or preparation notes"
        />
      </div>
      {(validation || add.error || foods.error) && (
        <p className="form-error" role="alert">
          {validation || errorMessage(add.error || foods.error)}
        </p>
      )}
      <div className="form-actions">
        <button type="button" className="button button-ghost" onClick={onComplete}>
          Cancel
        </button>
        <button className="button button-primary" disabled={add.isPending}>
          {add.isPending ? "Adding…" : "Add to pantry"}
        </button>
      </div>
    </form>
  );
}
