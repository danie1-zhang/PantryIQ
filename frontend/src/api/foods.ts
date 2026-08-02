import { useQuery } from "@tanstack/react-query";
import { apiRequest } from "./client";
import type { Food } from "../types/api";

export const foodKeys = {
  all: ["foods"] as const,
  search: (query: string) => ["foods", query] as const,
};

export function useFoods(query: string) {
  return useQuery({
    queryKey: foodKeys.search(query),
    queryFn: () => apiRequest<Food[]>(`/foods?query=${encodeURIComponent(query)}&limit=20`),
    enabled: query.trim().length >= 2,
    staleTime: 60_000,
  });
}
