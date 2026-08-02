export type CuisineMode = "strict" | "compatible" | "preference";
export type SpicePreference = "none" | "mild" | "medium" | "hot" | "any";

export interface ParsedMealPreferences {
  cuisines: string[];
  cuisine_mode: CuisineMode;
  required_food_ids: string[];
  preferred_food_ids: string[];
  excluded_food_ids: string[];
  required_categories: string[];
  preferred_categories: string[];
  excluded_categories: string[];
  preferred_ingredients: string[];
  avoid_ingredients: string[];
  allergens: string[];
  dietary_rules: string[];
  spice_preference: SpicePreference | null;
  texture_preferences: string[];
  flavor_preferences: string[];
  preparation_preferences: string[];
  hard_exclusions: string[];
  soft_dislikes: string[];
  clarification_needed: boolean;
  clarification_question: string | null;
}

export interface PreferenceParseResponse {
  preferences: ParsedMealPreferences;
  interpretation_summary: string[];
}
