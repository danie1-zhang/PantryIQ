import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ApiError } from "../api/client";
import { LoginPage } from "./LoginPage";
import { RegisterPage } from "./RegisterPage";

const login = vi.fn();
const register = vi.fn();

vi.mock("../auth/AuthContext", () => ({
  useAuth: () => ({ isAuthenticated: false, login }),
}));
vi.mock("../api/auth", () => ({ register: (...arguments_: unknown[]) => register(...arguments_) }));

describe("authentication pages", () => {
  beforeEach(() => {
    login.mockReset();
    register.mockReset();
  });

  it("submits login credentials and follows the original destination", async () => {
    login.mockResolvedValue(undefined);
    render(
      <MemoryRouter
        initialEntries={[{ pathname: "/login", state: { from: { pathname: "/pantry" } } }]}
      >
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/pantry" element={<div>pantry destination</div>} />
        </Routes>
      </MemoryRouter>,
    );
    fireEvent.change(screen.getByLabelText("Email or username"), { target: { value: "user" } });
    fireEvent.change(screen.getByLabelText("Password"), { target: { value: "long password" } });
    fireEvent.click(screen.getByRole("button", { name: "Log in" }));

    await waitFor(() =>
      expect(login).toHaveBeenCalledWith({ email_or_username: "user", password: "long password" }),
    );
    expect(await screen.findByText("pantry destination")).toBeInTheDocument();
  });

  it("shows a generic login failure", async () => {
    login.mockRejectedValue(new ApiError("Invalid email/username or password", 401));
    render(
      <MemoryRouter>
        <LoginPage />
      </MemoryRouter>,
    );
    fireEvent.change(screen.getByLabelText("Email or username"), { target: { value: "missing" } });
    fireEvent.change(screen.getByLabelText("Password"), { target: { value: "wrong" } });
    fireEvent.click(screen.getByRole("button", { name: "Log in" }));
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Invalid email/username or password",
    );
  });

  it("submits registration and reports conflicts", async () => {
    register.mockRejectedValue(new ApiError("Email or username is already registered", 409));
    render(
      <MemoryRouter>
        <RegisterPage />
      </MemoryRouter>,
    );
    fireEvent.change(screen.getByLabelText("Name"), { target: { value: "Example User" } });
    fireEvent.change(screen.getByLabelText("Email"), { target: { value: "user@example.com" } });
    fireEvent.change(screen.getByLabelText("Username"), { target: { value: "example_user" } });
    fireEvent.change(screen.getByLabelText("Password"), { target: { value: "a secure password" } });
    fireEvent.change(screen.getByLabelText("Confirm password"), {
      target: { value: "a secure password" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Create account" }));

    await waitFor(() =>
      expect(register).toHaveBeenCalledWith({
        email: "user@example.com",
        username: "example_user",
        name: "Example User",
        password: "a secure password",
      }),
    );
    expect(await screen.findByRole("alert")).toHaveTextContent("already registered");
  });
});
