import { useEffect, useState, type FormEvent } from "react";
import type { MealConstraints, UserProfile } from "../types/api";

type NumericField = keyof Pick<
  MealConstraints,
  | "calorie_goal"
  | "protein_goal"
  | "carbs_goal"
  | "fat_goal"
  | "sodium_max"
  | "sugar_max"
  | "cost_max"
  | "number_of_candidates"
>;

export function MealConstraintsForm({
  profile,
  submitting,
  onSubmit,
}: {
  profile?: UserProfile;
  submitting: boolean;
  onSubmit: (values: MealConstraints) => void;
}) {
  const [values, setValues] = useState<Record<NumericField, string>>({
    calorie_goal: "",
    protein_goal: "",
    carbs_goal: "",
    fat_goal: "",
    sodium_max: "",
    sugar_max: "",
    cost_max: "",
    number_of_candidates: "10000",
  });
  const [error, setError] = useState("");
  const [method, setMethod] = useState<"cp_sat" | "random">("cp_sat");
  const [timeLimit, setTimeLimit] = useState("2");
  useEffect(() => {
    if (profile)
      setValues((current) => ({
        ...current,
        calorie_goal: String(profile.calorie_goal),
        protein_goal: String(profile.protein_goal),
        carbs_goal: String(profile.carbs_goal),
        fat_goal: String(profile.fat_goal),
        sodium_max: profile.sodium_max?.toString() ?? "",
        sugar_max: profile.sugar_max?.toString() ?? "",
      }));
  }, [profile]);
  function set(field: NumericField, value: string) {
    setValues((current) => ({ ...current, [field]: value }));
  }
  function submit(event: FormEvent) {
    event.preventDefault();
    const required = ["calorie_goal", "protein_goal", "carbs_goal", "fat_goal"] as const;
    if (required.some((field) => !values[field] || Number(values[field]) <= 0))
      return setError("Calories and macro goals must be greater than zero.");
    const optional = ["sodium_max", "sugar_max", "cost_max"] as const;
    if (optional.some((field) => values[field] && Number(values[field]) < 0))
      return setError("Optional maximums cannot be negative.");
    const candidates = Number(values.number_of_candidates);
    if (candidates < 1 || candidates > 100000)
      return setError("Candidate count must be between 1 and 100,000.");
    const seconds = Number(timeLimit);
    if (seconds < 0.1 || seconds > 10)
      return setError("Solver time limit must be between 0.1 and 10 seconds.");
    setError("");
    onSubmit({
      calorie_goal: Number(values.calorie_goal),
      protein_goal: Number(values.protein_goal),
      carbs_goal: Number(values.carbs_goal),
      fat_goal: Number(values.fat_goal),
      sodium_max: values.sodium_max ? Number(values.sodium_max) : null,
      sugar_max: values.sugar_max ? Number(values.sugar_max) : null,
      cost_max: values.cost_max ? Number(values.cost_max) : null,
      number_of_candidates: candidates,
      optimization_method: method,
      time_limit_seconds: seconds,
    });
  }
  const field = (name: NumericField, label: string, optional = false) => (
    <div className="field">
      <label htmlFor={name}>
        {label} {optional && <span>optional</span>}
      </label>
      <input
        id={name}
        type="number"
        min={optional ? "0" : "0.01"}
        step="any"
        value={values[name]}
        onChange={(e) => set(name, e.target.value)}
      />
    </div>
  );
  return (
    <form className="card constraints-form" onSubmit={submit} noValidate>
      <div className="form-grid">
        {field("calorie_goal", "Calories")}
        {field("protein_goal", "Protein (g)")}
        {field("carbs_goal", "Carbohydrates (g)")}
        {field("fat_goal", "Fat (g)")}
        {field("sodium_max", "Sodium maximum (mg)", true)}
        {field("sugar_max", "Sugar maximum (g)", true)}
        {field("cost_max", "Cost maximum ($)", true)}
      </div>
      <details className="advanced-options">
        <summary>Advanced options</summary>
        <div className="form-grid">
          <div className="field">
            <label htmlFor="optimization-method">Optimization method</label>
            <select
              id="optimization-method"
              value={method}
              onChange={(event) => setMethod(event.target.value as "cp_sat" | "random")}
            >
              <option value="cp_sat">CP-SAT (recommended)</option>
              <option value="random">Random baseline</option>
            </select>
          </div>
          <div className="field">
            <label htmlFor="time-limit">Solver time limit (seconds)</label>
            <input
              id="time-limit"
              type="number"
              min="0.1"
              max="10"
              step="0.1"
              value={timeLimit}
              onChange={(event) => setTimeLimit(event.target.value)}
            />
          </div>
          {method === "random" && field("number_of_candidates", "Candidate count")}
        </div>
      </details>
      {error && (
        <p className="form-error" role="alert">
          {error}
        </p>
      )}
      <button className="button button-primary button-large" disabled={submitting}>
        {submitting ? "Solving your meal…" : "Generate meal"}
      </button>
    </form>
  );
}
