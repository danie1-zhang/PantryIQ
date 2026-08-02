import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { profile, recommendation } from "../test/fixtures";
import { MealConstraintsForm } from "./MealConstraintsForm";
import { MealRecommendationCard } from "./MealRecommendationCard";

describe("meal generation UI", () => {
  it("prefills profile goals and submits constraints", () => {
    const submit = vi.fn();
    render(<MealConstraintsForm profile={profile} submitting={false} onSubmit={submit} />);
    expect(screen.getByLabelText("Calories")).toHaveValue(2200);
    fireEvent.click(screen.getByRole("button", { name: "Generate meal" }));
    expect(submit).toHaveBeenCalledWith(
      expect.objectContaining({
        calorie_goal: 2200,
        protein_goal: 150,
        number_of_candidates: 10000,
      }),
    );
  });
  it("displays and accepts a recommendation", () => {
    const accept = vi.fn();
    const regenerate = vi.fn();
    render(
      <MealRecommendationCard
        meal={recommendation}
        accepting={false}
        onAccept={accept}
        onRegenerate={regenerate}
      />,
    );
    expect(screen.getByText("A strong pantry match")).toBeInTheDocument();
    expect(screen.getByText("Chicken Breast")).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText(/Rating/), { target: { value: "5" } });
    fireEvent.change(screen.getByLabelText(/Notes/), { target: { value: "Good meal" } });
    fireEvent.click(screen.getByRole("button", { name: "Accept meal" }));
    fireEvent.click(screen.getByRole("button", { name: "Regenerate" }));
    expect(accept).toHaveBeenCalledWith(5, "Good meal");
    expect(regenerate).toHaveBeenCalledOnce();
  });
});
