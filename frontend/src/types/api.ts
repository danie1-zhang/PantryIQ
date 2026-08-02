export interface Food {
  id: string;
  name: string;
  brand: string;
  category: string;
  serving_size: number;
  serving_unit: string;
  calories_per_serving: number;
  protein_g_per_serving: number;
  carbs_g_per_serving: number;
  fat_g_per_serving: number;
  sugar_g_per_serving: number;
  fiber_g_per_serving: number;
  sodium_mg_per_serving: number;
  cost_per_serving: number | null;
  created_at: string;
  updated_at: string;
}

export interface PantryItem extends Omit<Food, "id" | "name" | "created_at" | "updated_at"> {
  id: string;
  food_id: string;
  food_name: string;
  servings_available: number;
  max_servings_per_meal: number;
  expiration_date: string | null;
  notes: string | null;
  is_available: boolean;
  created_at: string;
  updated_at: string;
}

export interface PantryItemInput {
  food_id: string;
  servings_available: number;
  max_servings_per_meal?: number;
  expiration_date?: string | null;
  notes?: string | null;
}

export interface PantryItemUpdate {
  servings_available?: number;
  max_servings_per_meal?: number;
  expiration_date?: string | null;
  notes?: string | null;
  is_available?: boolean;
}

export interface UserProfile {
  id: string;
  email: string;
  username: string;
  name: string;
  age: number | null;
  height_inches: number | null;
  weight_pounds: number | null;
  gender: string | null;
  calorie_goal: number;
  protein_goal: number;
  carbs_goal: number;
  fat_goal: number;
  sodium_max: number | null;
  sugar_max: number | null;
  created_at: string;
  updated_at: string;
}

export type UserProfileUpdate = Partial<
  Omit<UserProfile, "id" | "email" | "username" | "created_at" | "updated_at">
>;

export interface MealConstraints {
  calorie_goal: number;
  protein_goal: number;
  carbs_goal: number;
  fat_goal: number;
  sodium_max?: number | null;
  sugar_max?: number | null;
  cost_max?: number | null;
  number_of_candidates?: number;
  optimization_method?: "cp_sat" | "random";
  time_limit_seconds?: number;
}

export interface NutritionTotals {
  calories: number;
  protein_g: number;
  carbs_g: number;
  fat_g: number;
  sugar_g: number;
  fiber_g: number;
  sodium_mg: number;
  cost: number | null;
}

export interface MealItem {
  food_id: string;
  food_name: string;
  servings: number;
}

export interface MealRecommendation {
  optimization_method: "cp_sat" | "random";
  solver_status: string;
  is_feasible: boolean;
  feasibility_score: number;
  items: MealItem[];
  totals: NutritionTotals;
  constraint_scores: Record<string, number>;
  constraints_met: Record<string, boolean>;
  constraint_violations: Record<string, number>;
  objective_value: number | null;
  best_objective_bound: number | null;
  solve_time_seconds: number;
  candidates_generated: number;
  valid_candidates_evaluated: number;
  disclaimer: string;
}

export interface LoggedMealItem extends MealItem {
  calories_per_serving: number;
  protein_g_per_serving: number;
  carbs_g_per_serving: number;
  fat_g_per_serving: number;
  sugar_g_per_serving: number;
  fiber_g_per_serving: number;
  sodium_mg_per_serving: number;
}

export interface MealHistoryItem {
  id: string;
  eaten_at: string;
  total_calories: number;
  total_protein_g: number;
  total_carbs_g: number;
  total_fat_g: number;
  total_sugar_g: number;
  total_fiber_g: number;
  total_sodium_mg: number;
  rating: number | null;
  notes: string | null;
  items: LoggedMealItem[];
  created_at: string;
  updated_at: string;
}

export interface LoggedMealDetail {
  id: string;
  eaten_at: string;
  totals: NutritionTotals;
  rating: number | null;
  notes: string | null;
  items: LoggedMealItem[];
  created_at: string;
  updated_at: string;
}

export interface AcceptMealInput {
  items: Array<{ food_id: string; servings: number }>;
  rating?: number | null;
  notes?: string | null;
}
