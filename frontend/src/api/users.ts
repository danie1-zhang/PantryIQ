import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiRequest } from "./client";
import type { UserProfile, UserProfileUpdate } from "../types/api";

export const userKeys = { me: ["user", "me"] as const };

export function useUser() {
  return useQuery({ queryKey: userKeys.me, queryFn: () => apiRequest<UserProfile>("/users/me") });
}

export function useUpdateUser() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: UserProfileUpdate) =>
      apiRequest<UserProfile>("/users/me", { method: "PATCH", body: JSON.stringify(input) }),
    onSuccess: (user) => queryClient.setQueryData(userKeys.me, user),
  });
}
