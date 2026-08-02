import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { pantryItem } from "../test/fixtures";
import { PantryItemCard } from "./PantryItemCard";

describe("PantryItemCard", () => {
  it("renders pantry nutrition and quantity", () => {
    render(
      <PantryItemCard
        item={pantryItem}
        onEdit={() => undefined}
        onDelete={() => undefined}
        deleting={false}
      />,
    );
    expect(screen.getByRole("heading", { name: "Chicken Breast" })).toBeInTheDocument();
    expect(screen.getByText("4")).toBeInTheDocument();
    expect(screen.getByText("40g")).toBeInTheDocument();
  });
  it("calls edit and delete actions", () => {
    const edit = vi.fn();
    const remove = vi.fn();
    render(<PantryItemCard item={pantryItem} onEdit={edit} onDelete={remove} deleting={false} />);
    fireEvent.click(screen.getByRole("button", { name: "Edit" }));
    fireEvent.click(screen.getByRole("button", { name: "Delete" }));
    expect(edit).toHaveBeenCalledOnce();
    expect(remove).toHaveBeenCalledOnce();
  });
});
