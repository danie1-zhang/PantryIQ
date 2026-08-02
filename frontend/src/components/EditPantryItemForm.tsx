import { useState, type FormEvent } from "react";
import { useUpdatePantryItem } from "../api/pantry";
import { errorMessage } from "../api/client";
import type { PantryItem } from "../types/api";

export function EditPantryItemForm({
  item,
  onComplete,
}: {
  item: PantryItem;
  onComplete: () => void;
}) {
  const [servings, setServings] = useState(String(item.servings_available));
  const [maximum, setMaximum] = useState(String(item.max_servings_per_meal));
  const [expiration, setExpiration] = useState(item.expiration_date ?? "");
  const [notes, setNotes] = useState(item.notes ?? "");
  const [available, setAvailable] = useState(item.is_available);
  const [validation, setValidation] = useState("");
  const update = useUpdatePantryItem();
  function submit(event: FormEvent) {
    event.preventDefault();
    const quantity = Number(servings);
    const max = Number(maximum);
    if (quantity < 0 || max < 0) return setValidation("Serving values cannot be negative.");
    if (max > quantity) return setValidation("Maximum per meal cannot exceed available servings.");
    setValidation("");
    update.mutate(
      {
        id: item.id,
        input: {
          servings_available: quantity,
          max_servings_per_meal: max,
          expiration_date: expiration || null,
          notes: notes || null,
          is_available: quantity === 0 ? false : available,
        },
      },
      { onSuccess: onComplete },
    );
  }
  return (
    <form className="stack-form" onSubmit={submit} aria-label={`Edit ${item.food_name}`}>
      <h3>Edit {item.food_name}</h3>
      <div className="form-grid">
        <div className="field">
          <label htmlFor="edit-servings">Servings available</label>
          <input
            id="edit-servings"
            type="number"
            min="0"
            step="0.5"
            value={servings}
            onChange={(e) => setServings(e.target.value)}
          />
        </div>
        <div className="field">
          <label htmlFor="edit-maximum">Maximum per meal</label>
          <input
            id="edit-maximum"
            type="number"
            min="0"
            step="0.5"
            value={maximum}
            onChange={(e) => setMaximum(e.target.value)}
          />
        </div>
        <div className="field">
          <label htmlFor="edit-expiration">Expiration date</label>
          <input
            id="edit-expiration"
            type="date"
            value={expiration}
            onChange={(e) => setExpiration(e.target.value)}
          />
        </div>
      </div>
      <div className="field">
        <label htmlFor="edit-notes">Notes</label>
        <textarea
          id="edit-notes"
          maxLength={2000}
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
        />
      </div>
      <label className="checkbox-row">
        <input
          type="checkbox"
          checked={available}
          disabled={Number(servings) === 0}
          onChange={(e) => setAvailable(e.target.checked)}
        />{" "}
        Available for meals
      </label>
      {(validation || update.error) && (
        <p className="form-error" role="alert">
          {validation || errorMessage(update.error)}
        </p>
      )}
      <div className="form-actions">
        <button type="button" className="button button-ghost" onClick={onComplete}>
          Cancel
        </button>
        <button className="button button-primary" disabled={update.isPending}>
          {update.isPending ? "Saving…" : "Save changes"}
        </button>
      </div>
    </form>
  );
}
