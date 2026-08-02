import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";
import { ProtectedRoute } from "./ProtectedRoute";

let authState = { isAuthenticated: false, isInitializing: false };
vi.mock("./AuthContext", () => ({ useAuth: () => authState }));

function renderRoute() {
  return render(
    <MemoryRouter initialEntries={["/pantry"]}>
      <Routes>
        <Route path="/login" element={<div>login page</div>} />
        <Route element={<ProtectedRoute />}>
          <Route path="/pantry" element={<div>private pantry</div>} />
        </Route>
      </Routes>
    </MemoryRouter>,
  );
}

describe("ProtectedRoute", () => {
  it("redirects unauthenticated users", () => {
    authState = { isAuthenticated: false, isInitializing: false };
    renderRoute();
    expect(screen.getByText("login page")).toBeInTheDocument();
  });

  it("shows a loading state before session restoration finishes", () => {
    authState = { isAuthenticated: false, isInitializing: true };
    renderRoute();
    expect(screen.getByText("Restoring your session…")).toBeInTheDocument();
  });
});
