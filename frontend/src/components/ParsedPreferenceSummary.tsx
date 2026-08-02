import type { ParsedMealPreferences, PreferenceParseResponse } from "../types/preferences";

const fields = [
  ["cuisines", "Cuisine"],
  ["allergens", "No allergen"],
  ["dietary_rules", "Dietary"],
  ["avoid_ingredients", "Avoid"],
  ["preferred_ingredients", "Prefer"],
  ["preferred_categories", "Prefer category"],
  ["excluded_categories", "No category"],
  ["soft_dislikes", "Dislike"],
] as const;

export function ParsedPreferenceSummary({
  value,
  onChange,
}: {
  value: PreferenceParseResponse;
  onChange: (preferences: ParsedMealPreferences) => void;
}) {
  function remove(field: (typeof fields)[number][0], tag: string) {
    onChange({
      ...value.preferences,
      [field]: value.preferences[field].filter((item) => item !== tag),
    });
  }
  return (
    <section className="card" aria-label="Parsed preferences">
      <h2>Interpreted preferences</h2>
      {value.preferences.clarification_needed && (
        <div className="state-panel state-error" role="alert">
          {value.preferences.clarification_question}
        </div>
      )}
      <div className="preference-chips">
        {fields.flatMap(([field, label]) =>
          value.preferences[field].map((tag) => (
            <button
              key={`${field}-${tag}`}
              type="button"
              className="preference-chip"
              onClick={() => remove(field, tag)}
              aria-label={`Remove ${label} ${tag}`}
            >
              {label}: {tag} ×
            </button>
          )),
        )}
        {value.preferences.spice_preference && (
          <button
            type="button"
            className="preference-chip"
            onClick={() => onChange({ ...value.preferences, spice_preference: null })}
          >
            Spice: {value.preferences.spice_preference} ×
          </button>
        )}
      </div>
      {value.preferences.cuisines.length > 0 && (
        <div className="field">
          <label htmlFor="cuisine-mode">Cuisine matching</label>
          <select
            id="cuisine-mode"
            value={value.preferences.cuisine_mode}
            onChange={(event) =>
              onChange({
                ...value.preferences,
                cuisine_mode: event.target.value as ParsedMealPreferences["cuisine_mode"],
              })
            }
          >
            <option value="compatible">Compatible</option>
            <option value="strict">Strict</option>
            <option value="preference">Preference only</option>
          </select>
        </div>
      )}
      <ul>
        {value.interpretation_summary.map((line) => (
          <li key={line}>{line}</li>
        ))}
      </ul>
      <p className="muted">Select a chip to remove it before generation.</p>
    </section>
  );
}
