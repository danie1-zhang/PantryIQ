import { useMutation } from "@tanstack/react-query";
import type { PreferenceParseResponse } from "../types/preferences";
import { apiRequest } from "./client";

export function useParsePreferences() {
  return useMutation({
    mutationFn: (text: string) =>
      apiRequest<PreferenceParseResponse>("/preferences/parse", {
        method: "POST",
        body: JSON.stringify({ text }),
      }),
  });
}
