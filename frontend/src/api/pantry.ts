import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiRequest } from "./client";
import type { PantryItem, PantryItemInput, PantryItemUpdate } from "../types/api";

export const pantryKeys = { all: ["pantry"] as const };

export function usePantry(availableOnly = true) {
  return useQuery({
    queryKey: [...pantryKeys.all, availableOnly],
    queryFn: () => apiRequest<PantryItem[]>(`/pantry?available_only=${availableOnly}`),
  });
}

function useRefreshPantry() {
  const queryClient = useQueryClient();
  return () => queryClient.invalidateQueries({ queryKey: pantryKeys.all });
}

export function useAddPantryItem() {
  const refresh = useRefreshPantry();
  return useMutation({
    mutationFn: (input: PantryItemInput) =>
      apiRequest<PantryItem>("/pantry/items", { method: "POST", body: JSON.stringify(input) }),
    onSuccess: refresh,
  });
}

export function useUpdatePantryItem() {
  const refresh = useRefreshPantry();
  return useMutation({
    mutationFn: ({ id, input }: { id: string; input: PantryItemUpdate }) =>
      apiRequest<PantryItem>(`/pantry/items/${id}`, {
        method: "PATCH",
        body: JSON.stringify(input),
      }),
    onSuccess: refresh,
  });
}

export function useDeletePantryItem() {
  const refresh = useRefreshPantry();
  return useMutation({
    mutationFn: (id: string) => apiRequest<void>(`/pantry/items/${id}`, { method: "DELETE" }),
    onSuccess: refresh,
  });
}
