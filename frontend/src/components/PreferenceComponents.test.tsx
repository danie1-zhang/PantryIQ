import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import type { PreferenceParseResponse } from "../types/preferences";
import { ParsedPreferenceSummary } from "./ParsedPreferenceSummary";
import { PreferenceInput } from "./PreferenceInput";

const mutate = vi.fn();
let pending = false;
let parseError: Error | null = null;
vi.mock("../api/preferences", () => ({
  useParsePreferences: () => ({ mutate, isPending: pending, error: parseError }),
}));

const parsed: PreferenceParseResponse = {
  preferences: {
    cuisines: ["greek"],
    cuisine_mode: "compatible",
    required_food_ids: [],
    preferred_food_ids: [],
    excluded_food_ids: [],
    required_categories: [],
    preferred_categories: ["protein"],
    excluded_categories: [],
    preferred_ingredients: ["chicken"],
    avoid_ingredients: [],
    allergens: ["peanut"],
    dietary_rules: ["dairy_free"],
    spice_preference: "none",
    texture_preferences: [],
    flavor_preferences: [],
    preparation_preferences: [],
    hard_exclusions: [],
    soft_dislikes: [],
    clarification_needed: false,
    clarification_question: null,
  },
  interpretation_summary: ["Greek cuisine uses compatible matching."],
};

describe("preference controls", () => {
  it("submits natural language for parsing", () => {
    render(<PreferenceInput onParsed={vi.fn()} />);
    fireEvent.change(screen.getByLabelText("Describe what you want"), {
      target: { value: "Greek without peanuts" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Parse preferences" }));
    expect(mutate).toHaveBeenCalledWith("Greek without peanuts", expect.any(Object));
  });

  it("shows parsing progress and provider errors", () => {
    pending = true;
    const { rerender } = render(<PreferenceInput onParsed={vi.fn()} />);
    expect(screen.getByRole("button", { name: "Interpreting…" })).toBeDisabled();
    pending = false;
    parseError = new Error("Preference parsing provider is unavailable");
    rerender(<PreferenceInput onParsed={vi.fn()} />);
    expect(screen.getByRole("alert")).toHaveTextContent("provider is unavailable");
    parseError = null;
  });

  it("displays and removes structured preferences", () => {
    const change = vi.fn();
    render(<ParsedPreferenceSummary value={parsed} onChange={change} />);
    expect(screen.getByText("No allergen: peanut ×")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Remove No allergen peanut" }));
    expect(change).toHaveBeenCalledWith(expect.objectContaining({ allergens: [] }));
  });

  it("displays clarification instead of hiding ambiguity", () => {
    render(
      <ParsedPreferenceSummary
        value={{
          ...parsed,
          preferences: {
            ...parsed.preferences,
            clarification_needed: true,
            clarification_question: "Strict or compatible?",
          },
        }}
        onChange={vi.fn()}
      />,
    );
    expect(screen.getByRole("alert")).toHaveTextContent("Strict or compatible?");
  });
});
