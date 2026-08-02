import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { pantryItem } from "../test/fixtures";
import { EditPantryItemForm } from "./EditPantryItemForm";

const mutate = vi.fn();
vi.mock("../api/pantry", () => ({
  useUpdatePantryItem: () => ({ mutate, isPending: false, error: null }),
}));

describe("EditPantryItemForm", () => {
  it("submits pantry changes", () => {
    render(<EditPantryItemForm item={pantryItem} onComplete={() => undefined} />);
    fireEvent.change(screen.getByLabelText("Servings available"), { target: { value: "5" } });
    fireEvent.change(screen.getByLabelText("Notes"), { target: { value: "Front shelf" } });
    fireEvent.click(screen.getByRole("button", { name: "Save changes" }));
    expect(mutate).toHaveBeenCalledWith(
      expect.objectContaining({
        id: "pantry-1",
        input: expect.objectContaining({ servings_available: 5, notes: "Front shelf" }),
      }),
      expect.any(Object),
    );
  });

  it("rejects a maximum above the available amount", () => {
    render(<EditPantryItemForm item={pantryItem} onComplete={() => undefined} />);
    fireEvent.change(screen.getByLabelText("Maximum per meal"), { target: { value: "5" } });
    fireEvent.click(screen.getByRole("button", { name: "Save changes" }));
    expect(screen.getByRole("alert")).toHaveTextContent("cannot exceed");
  });
});
