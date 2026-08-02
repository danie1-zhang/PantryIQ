import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, renderHook, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { useAcceptMeal } from "./meals";

describe("useAcceptMeal", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("invalidates pantry and meal-history data after acceptance", async () => {
    const queryClient = new QueryClient({ defaultOptions: { mutations: { retry: false } } });
    queryClient.setQueryData(["pantry", true], []);
    queryClient.setQueryData(["meals", 20], []);
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(
          JSON.stringify({
            id: "meal-1",
            eaten_at: "2026-01-01T00:00:00Z",
            totals: {},
            rating: null,
            notes: null,
            items: [],
            created_at: "2026-01-01T00:00:00Z",
            updated_at: "2026-01-01T00:00:00Z",
          }),
          { status: 201, headers: { "Content-Type": "application/json" } },
        ),
      ),
    );
    const wrapper = ({ children }: { children: ReactNode }) => (
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    );
    const { result } = renderHook(() => useAcceptMeal(), { wrapper });

    act(() => result.current.mutate({ items: [{ food_id: "food-1", servings: 1 }] }));
    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(queryClient.getQueryState(["pantry", true])?.isInvalidated).toBe(true);
    expect(queryClient.getQueryState(["meals", 20])?.isInvalidated).toBe(true);
  });
});
