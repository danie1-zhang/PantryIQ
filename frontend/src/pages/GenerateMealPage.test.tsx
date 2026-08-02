import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { profile, recommendation } from "../test/fixtures";
import type { MealConstraints } from "../types/api";
import { GenerateMealPage } from "./GenerateMealPage";

const submittedRequests: MealConstraints[] = [];
let generatedMeal: typeof recommendation | undefined;

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
});
