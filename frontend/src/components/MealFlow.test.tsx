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
        optimization_method: "cp_sat",
        time_limit_seconds: 2,
      }),
    );
  });
  it("validates the solver time limit", () => {
    render(<MealConstraintsForm profile={profile} submitting={false} onSubmit={vi.fn()} />);
    fireEvent.click(screen.getByText("Advanced options"));
    fireEvent.change(screen.getByLabelText("Solver time limit (seconds)"), {
      target: { value: "20" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Generate meal" }));
    expect(screen.getByRole("alert")).toHaveTextContent("between 0.1 and 10");
  });
  it("shows the solving state", () => {
    render(<MealConstraintsForm profile={profile} submitting onSubmit={vi.fn()} />);
    expect(screen.getByRole("button", { name: "Solving your meal…" })).toBeDisabled();
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
    expect(screen.getByText("OPTIMAL")).toBeInTheDocument();
    expect(screen.getByText("CP-SAT")).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText(/Rating/), { target: { value: "5" } });
    fireEvent.change(screen.getByLabelText(/Notes/), { target: { value: "Good meal" } });
    fireEvent.click(screen.getByRole("button", { name: "Accept meal" }));
    fireEvent.click(screen.getByRole("button", { name: "Generate another" }));
    expect(accept).toHaveBeenCalledWith(5, "Good meal");
    expect(regenerate).toHaveBeenCalledOnce();
  });
  it("distinguishes feasible and near-feasible solver results", () => {
    const { rerender } = render(
      <MealRecommendationCard
        meal={{ ...recommendation, solver_status: "FEASIBLE" }}
        accepting={false}
        onAccept={vi.fn()}
        onRegenerate={vi.fn()}
      />,
    );
    expect(screen.getByText("FEASIBLE")).toBeInTheDocument();
    rerender(
      <MealRecommendationCard
        meal={{
          ...recommendation,
          is_feasible: false,
          constraint_violations: { protein: 12.5 },
        }}
        accepting={false}
        onAccept={vi.fn()}
        onRegenerate={vi.fn()}
      />,
    );
    expect(screen.getByText("Closest available match")).toBeInTheDocument();
    expect(screen.getByText("protein: 12.5")).toBeInTheDocument();
  });
  it("shows an acceptance API error", () => {
    render(
      <MealRecommendationCard
        meal={recommendation}
        accepting={false}
        acceptError={new Error("Insufficient pantry servings")}
        onAccept={vi.fn()}
        onRegenerate={vi.fn()}
      />,
    );
    expect(screen.getByRole("alert")).toHaveTextContent("Insufficient pantry servings");
  });
});
