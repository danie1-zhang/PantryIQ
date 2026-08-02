import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiRequest } from "./client";
import { pantryKeys } from "./pantry";
import type {
  AcceptMealInput,
  LoggedMealDetail,
  MealConstraints,
  MealHistoryItem,
  MealRecommendation,
} from "../types/api";

export const mealKeys = { all: ["meals"] as const, detail: (id: string) => ["meals", id] as const };

export function useMealHistory(limit = 20) {
  return useQuery({
    queryKey: [...mealKeys.all, limit],
    queryFn: () => apiRequest<MealHistoryItem[]>(`/meals?limit=${limit}`),
  });
}

export function useMealDetail(id: string | null) {
  return useQuery({
    queryKey: mealKeys.detail(id ?? ""),
    queryFn: () => apiRequest<LoggedMealDetail>(`/meals/${id}`),
    enabled: Boolean(id),
  });
}

export function useGenerateMeal() {
  return useMutation({
    mutationFn: (input: MealConstraints) =>
      apiRequest<MealRecommendation>("/meals/generate", {
        method: "POST",
        body: JSON.stringify(input),
      }),
  });
}

export function useAcceptMeal() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: AcceptMealInput) =>
      apiRequest<LoggedMealDetail>("/meals/accept", {
        method: "POST",
        body: JSON.stringify(input),
      }),
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: pantryKeys.all }),
        queryClient.invalidateQueries({ queryKey: mealKeys.all }),
      ]);
    },
  });
}
