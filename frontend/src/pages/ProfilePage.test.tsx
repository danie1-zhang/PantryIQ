import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { profile } from "../test/fixtures";
import { ProfilePage } from "./ProfilePage";

const mutate = vi.fn();
vi.mock("../api/users", () => ({
  useUser: () => ({ data: profile, isLoading: false, error: null, refetch: vi.fn() }),
  useUpdateUser: () => ({ mutate, isPending: false, isSuccess: false, error: null }),
}));

describe("ProfilePage", () => {
  it("keeps account identifiers read-only and updates supported fields", () => {
    render(<ProfilePage />);
    expect(screen.getByLabelText("Email")).toBeDisabled();
    fireEvent.change(screen.getByLabelText("Name"), { target: { value: "Updated User" } });
    fireEvent.click(screen.getByRole("button", { name: "Save changes" }));
    expect(mutate).toHaveBeenCalledWith(
      expect.objectContaining({ name: "Updated User", calorie_goal: 2200 }),
    );
  });
});
