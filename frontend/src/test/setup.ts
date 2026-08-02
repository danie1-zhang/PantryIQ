import "@testing-library/jest-dom/vitest";
import { cleanup } from "@testing-library/react";
import { afterEach, vi } from "vitest";
import { setAccessToken, setAuthenticationLostHandler } from "../auth/authStorage";

afterEach(() => {
  cleanup();
  localStorage.clear();
  setAccessToken(null);
  setAuthenticationLostHandler(null);
  vi.restoreAllMocks();
});
