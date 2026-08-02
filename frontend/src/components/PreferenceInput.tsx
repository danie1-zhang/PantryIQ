import { useState, type FormEvent } from "react";
import { useParsePreferences } from "../api/preferences";
import { errorMessage } from "../api/client";
import type { PreferenceParseResponse } from "../types/preferences";

export function PreferenceInput({
  onParsed,
}: {
  onParsed: (value: PreferenceParseResponse) => void;
}) {
  const [text, setText] = useState("");
  const parse = useParsePreferences();

  function submit(event: FormEvent) {
    event.preventDefault();
    if (!text.trim()) return;
    parse.mutate(text.trim(), { onSuccess: onParsed });
  }

  return (
    <form className="card constraints-form" onSubmit={submit}>
      <div className="field">
        <label htmlFor="meal-preferences">Describe what you want</label>
        <textarea
          id="meal-preferences"
          value={text}
          maxLength={2000}
          onChange={(event) => setText(event.target.value)}
          placeholder="I want a Greek meal without peanuts, and I prefer chicken and vegetables."
          rows={4}
        />
        <span className="muted">
          Mention cuisines, allergies, dietary restrictions, ingredients, or spice level.
        </span>
      </div>
      {parse.error && (
        <p className="form-error" role="alert">
          {errorMessage(parse.error)}
        </p>
      )}
      <button className="button button-secondary" disabled={parse.isPending || !text.trim()}>
        {parse.isPending ? "Interpreting…" : "Parse preferences"}
      </button>
    </form>
  );
}
