import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { food } from "../test/fixtures";
import { AddFoodForm } from "./AddFoodForm";

const mutate = vi.fn();
vi.mock("../api/foods", () => ({
  useFoods: () => ({ data: [food], isFetching: false, error: null }),
}));
vi.mock("../api/pantry", () => ({
  useAddPantryItem: () => ({ mutate, isPending: false, error: null }),
}));

describe("AddFoodForm", () => {
  beforeEach(() => mutate.mockClear());
  it("requires a catalog selection", () => {
    render(<AddFoodForm onComplete={() => undefined} />);
    fireEvent.click(screen.getByRole("button", { name: "Add to pantry" }));
    expect(screen.getByRole("alert")).toHaveTextContent("Choose a food");
  });
  it("submits the selected food and validates maximum servings", () => {
    render(<AddFoodForm onComplete={() => undefined} />);
    fireEvent.click(screen.getByRole("button", { name: /Chicken Breast/ }));
    fireEvent.change(screen.getByLabelText("Servings available"), { target: { value: "3" } });
    fireEvent.change(screen.getByLabelText("Maximum per meal"), { target: { value: "4" } });
    fireEvent.click(screen.getByRole("button", { name: "Add to pantry" }));
    expect(screen.getByRole("alert")).toHaveTextContent("cannot exceed");
    fireEvent.change(screen.getByLabelText("Maximum per meal"), { target: { value: "2" } });
    fireEvent.click(screen.getByRole("button", { name: "Add to pantry" }));
    expect(mutate).toHaveBeenCalledWith(
      expect.objectContaining({
        food_id: "food-1",
        servings_available: 3,
        max_servings_per_meal: 2,
      }),
      expect.any(Object),
    );
  });
});
