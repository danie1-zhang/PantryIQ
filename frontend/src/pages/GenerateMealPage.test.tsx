import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { profile, recommendation } from "../test/fixtures";
import type { MealConstraints } from "../types/api";
import type { PreferenceParseResponse } from "../types/preferences";
import { GenerateMealPage } from "./GenerateMealPage";

const submittedRequests: MealConstraints[] = [];
let generatedMeal: typeof recommendation | undefined;
const parsedResponse: PreferenceParseResponse = {
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
    dietary_rules: [],
    spice_preference: null,
    texture_preferences: [],
    flavor_preferences: [],
    preparation_preferences: [],
    hard_exclusions: [],
    soft_dislikes: [],
    clarification_needed: false,
    clarification_question: null,
  },
  interpretation_summary: ["Greek cuisine is preferred."],
};

vi.mock("../api/users", () => ({
  useUser: () => ({ data: profile, isLoading: false, error: null, refetch: vi.fn() }),
}));

vi.mock("../api/meals", () => ({
  useGenerateMeal: () => ({
    data: generatedMeal,
    error: null,
    isPending: false,
    mutate: (
      request: MealConstraints,
      options?: { onSuccess?: (meal: typeof recommendation) => void },
    ) => {
      submittedRequests.push(request);
      generatedMeal = recommendation;
      options?.onSuccess?.(recommendation);
    },
  }),
  useAcceptMeal: () => ({
    error: null,
    isPending: false,
    mutate: vi.fn(),
    reset: vi.fn(),
  }),
}));

vi.mock("../api/preferences", () => ({
  useParsePreferences: () => ({
    mutate: (_text: string, options?: { onSuccess?: (value: PreferenceParseResponse) => void }) =>
      options?.onSuccess?.(parsedResponse),
    isPending: false,
    error: null,
  }),
}));

describe("GenerateMealPage", () => {
  beforeEach(() => {
    submittedRequests.length = 0;
    generatedMeal = undefined;
  });

  it("excludes earlier recommendations when generating another meal", () => {
    render(
      <MemoryRouter>
        <GenerateMealPage />
      </MemoryRouter>,
    );

    fireEvent.click(screen.getByRole("button", { name: "Generate meal" }));
    fireEvent.click(screen.getByRole("button", { name: "Generate another" }));

    expect(submittedRequests).toHaveLength(2);
    expect(submittedRequests[1].excluded_meals).toEqual([
      {
        items: recommendation.items.map(({ food_id, servings }) => ({ food_id, servings })),
      },
    ]);
  });

  it("includes editable structured preferences in generation", () => {
    render(
      <MemoryRouter>
        <GenerateMealPage />
      </MemoryRouter>,
    );
    fireEvent.change(screen.getByLabelText("Describe what you want"), {
      target: { value: "Greek without peanuts" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Parse preferences" }));
    expect(screen.getByText("Cuisine: greek ×")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Generate meal" }));
    expect(submittedRequests[0].preferences).toEqual(parsedResponse.preferences);
  });
});
