import { afterEach, describe, expect, it, vi } from "vitest";
import { getAccessToken, setAccessToken, setAuthenticationLostHandler } from "../auth/authStorage";
import { apiRequest } from "./client";

describe("authenticated API client", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("attaches the in-memory access token and includes cookies", async () => {
    setAccessToken("access-token");
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ ok: true }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );
    vi.stubGlobal("fetch", fetchMock);

    await apiRequest("/pantry");

    const options = fetchMock.mock.calls[0][1] as RequestInit;
    expect(new Headers(options.headers).get("Authorization")).toBe("Bearer access-token");
    expect(options.credentials).toBe("include");
  });

  it("coordinates one refresh and retries simultaneous failed requests once", async () => {
    setAccessToken("expired-token");
    let refreshCalls = 0;
    const fetchMock = vi.fn(async (url: string, options?: RequestInit) => {
      if (url.endsWith("/auth/refresh")) {
        refreshCalls += 1;
        return new Response(JSON.stringify({ access_token: "fresh-token" }), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        });
      }
      const authorization = new Headers(options?.headers).get("Authorization");
      return authorization === "Bearer fresh-token"
        ? new Response(JSON.stringify({ ok: true }), {
            status: 200,
            headers: { "Content-Type": "application/json" },
          })
        : new Response(JSON.stringify({ detail: "expired" }), { status: 401 });
    });
    vi.stubGlobal("fetch", fetchMock);

    await Promise.all([apiRequest("/pantry"), apiRequest("/meals")]);

    expect(refreshCalls).toBe(1);
    expect(getAccessToken()).toBe("fresh-token");
  });

  it("clears authentication when refresh fails", async () => {
    setAccessToken("expired-token");
    const lost = vi.fn();
    setAuthenticationLostHandler(lost);
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(null, { status: 401 })));

    await expect(apiRequest("/pantry")).rejects.toMatchObject({ status: 401 });
    expect(getAccessToken()).toBeNull();
    expect(lost).toHaveBeenCalledOnce();
  });
});
