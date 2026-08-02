import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { ErrorState, LoadingState } from "./AsyncState";

describe("request states", () => {
  it("shows loading feedback", () => {
    render(<LoadingState label="Loading pantry…" />);
    expect(screen.getByText("Loading pantry…")).toBeInTheDocument();
  });
  it("shows an API error and retries", () => {
    const retry = vi.fn();
    render(<ErrorState error={new Error("Offline")} retry={retry} />);
    expect(screen.getByRole("alert")).toHaveTextContent("Offline");
    fireEvent.click(screen.getByRole("button", { name: /Try again/ }));
    expect(retry).toHaveBeenCalledOnce();
  });
});
