import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { profile } from "../test/fixtures";
import { getAccessToken } from "./authStorage";
import { AuthProvider, useAuth } from "./AuthContext";

function Status() {
  const auth = useAuth();
  return (
    <div>
      <span>
        {auth.isInitializing ? "loading" : auth.isAuthenticated ? auth.user?.name : "guest"}
      </span>
      <button onClick={() => void auth.login({ email_or_username: "user", password: "password" })}>
        login
      </button>
      <button onClick={() => void auth.logout()}>logout</button>
    </div>
  );
}

function renderAuth(queryClient = new QueryClient()) {
  const wrapper = ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>{children}</AuthProvider>
    </QueryClientProvider>
  );
  return { ...render(<Status />, { wrapper }), queryClient };
}

describe("AuthProvider", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("shows initialization while restoring a session through refresh", async () => {
    let finishRefresh: ((response: Response) => void) | undefined;
    vi.stubGlobal(
      "fetch",
      vi.fn((url: string) => {
        if (url.endsWith("/auth/refresh")) {
          return new Promise<Response>((resolve) => {
            finishRefresh = resolve;
          });
        }
        return Promise.resolve(
          new Response(JSON.stringify(profile), {
            status: 200,
            headers: { "Content-Type": "application/json" },
          }),
        );
      }),
    );
    renderAuth();
    expect(screen.getByText("loading")).toBeInTheDocument();

    finishRefresh?.(
      new Response(JSON.stringify({ access_token: "restored" }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );
    await waitFor(() => expect(screen.getByText(profile.name)).toBeInTheDocument());
    expect(getAccessToken()).toBe("restored");
  });

  it("clears prior private query data on login and logout", async () => {
    const queryClient = new QueryClient();
    queryClient.setQueryData(["pantry"], [{ private: true }]);
    const fetchMock = vi.fn(async (url: string) => {
      if (url.endsWith("/auth/refresh")) return new Response(null, { status: 401 });
      if (url.endsWith("/auth/login")) {
        return new Response(
          JSON.stringify({
            access_token: "logged-in",
            token_type: "bearer",
            expires_in: 900,
            user: profile,
          }),
          { status: 200, headers: { "Content-Type": "application/json" } },
        );
      }
      return new Response(null, { status: 204 });
    });
    vi.stubGlobal("fetch", fetchMock);
    renderAuth(queryClient);
    await waitFor(() => expect(screen.getByText("guest")).toBeInTheDocument());

    fireEvent.click(screen.getByText("login"));
    await waitFor(() => expect(screen.getByText(profile.name)).toBeInTheDocument());
    expect(queryClient.getQueryData(["pantry"])).toBeUndefined();
    queryClient.setQueryData(["meals"], [{ private: true }]);

    fireEvent.click(screen.getByText("logout"));
    await waitFor(() => expect(screen.getByText("guest")).toBeInTheDocument());
    expect(queryClient.getQueryData(["meals"])).toBeUndefined();
    expect(getAccessToken()).toBeNull();
  });
});
