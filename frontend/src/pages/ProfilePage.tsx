import { useEffect, useState, type FormEvent } from "react";
import { errorMessage } from "../api/client";
import { useUpdateUser, useUser } from "../api/users";
import { ErrorState, LoadingState } from "../components/AsyncState";
import type { UserProfileUpdate } from "../types/api";

type NumericField =
  | "age"
  | "height_inches"
  | "weight_pounds"
  | "calorie_goal"
  | "protein_goal"
  | "carbs_goal"
  | "fat_goal"
  | "sodium_max"
  | "sugar_max";
type FormValues = Record<NumericField | "name" | "gender", string>;

export function ProfilePage() {
  const profile = useUser();
  const update = useUpdateUser();
  const [values, setValues] = useState<FormValues>({
    name: "",
    gender: "",
    age: "",
    height_inches: "",
    weight_pounds: "",
    calorie_goal: "",
    protein_goal: "",
    carbs_goal: "",
    fat_goal: "",
    sodium_max: "",
    sugar_max: "",
  });
  const [validation, setValidation] = useState("");

  useEffect(() => {
    if (!profile.data) return;
    setValues({
      name: profile.data.name,
      gender: profile.data.gender ?? "",
      age: profile.data.age?.toString() ?? "",
      height_inches: profile.data.height_inches?.toString() ?? "",
      weight_pounds: profile.data.weight_pounds?.toString() ?? "",
      calorie_goal: String(profile.data.calorie_goal),
      protein_goal: String(profile.data.protein_goal),
      carbs_goal: String(profile.data.carbs_goal),
      fat_goal: String(profile.data.fat_goal),
      sodium_max: profile.data.sodium_max?.toString() ?? "",
      sugar_max: profile.data.sugar_max?.toString() ?? "",
    });
  }, [profile.data]);

  function submit(event: FormEvent) {
    event.preventDefault();
    if (!values.name.trim()) return setValidation("Name cannot be blank.");
    const positive = [
      "age",
      "height_inches",
      "weight_pounds",
      "calorie_goal",
      "protein_goal",
      "carbs_goal",
      "fat_goal",
    ] as const;
    if (positive.some((field) => values[field] && Number(values[field]) <= 0))
      return setValidation("Age, measurements, and nutrition goals must be greater than zero.");
    if (
      ["sodium_max", "sugar_max"].some(
        (field) =>
          values[field as "sodium_max" | "sugar_max"] &&
          Number(values[field as "sodium_max" | "sugar_max"]) < 0,
      )
    )
      return setValidation("Nutrition maximums cannot be negative.");
    setValidation("");
    const payload: UserProfileUpdate = {
      name: values.name.trim(),
      gender: values.gender.trim() || null,
      age: values.age ? Number(values.age) : null,
      height_inches: values.height_inches ? Number(values.height_inches) : null,
      weight_pounds: values.weight_pounds ? Number(values.weight_pounds) : null,
      calorie_goal: Number(values.calorie_goal),
      protein_goal: Number(values.protein_goal),
      carbs_goal: Number(values.carbs_goal),
      fat_goal: Number(values.fat_goal),
      sodium_max: values.sodium_max ? Number(values.sodium_max) : null,
      sugar_max: values.sugar_max ? Number(values.sugar_max) : null,
    };
    update.mutate(payload);
  }

  if (profile.isLoading) return <LoadingState label="Loading your profile…" />;
  if (profile.error) return <ErrorState error={profile.error} retry={() => profile.refetch()} />;
  const set = (field: keyof FormValues, value: string) =>
    setValues((current) => ({ ...current, [field]: value }));
  const numberField = (name: NumericField, label: string, required = false) => (
    <div className="field">
      <label htmlFor={name}>{label}</label>
      <input
        id={name}
        type="number"
        step="any"
        min={name === "sodium_max" || name === "sugar_max" ? "0" : "0.01"}
        required={required}
        value={values[name]}
        onChange={(e) => set(name, e.target.value)}
      />
    </div>
  );

  return (
    <>
      <header className="page-header">
        <div>
          <p className="eyebrow">Your account</p>
          <h1>Profile and nutrition goals</h1>
          <p>These defaults prefill the meal generator. Email and username are read-only.</p>
        </div>
      </header>
      <form className="card profile-form" onSubmit={submit}>
        <section>
          <h2>Account</h2>
          <div className="form-grid">
            <div className="field">
              <label htmlFor="email">Email</label>
              <input id="email" value={profile.data?.email ?? ""} disabled />
            </div>
            <div className="field">
              <label htmlFor="username">Username</label>
              <input id="username" value={profile.data?.username ?? ""} disabled />
            </div>
            <div className="field">
              <label htmlFor="name">Name</label>
              <input
                id="name"
                value={values.name}
                maxLength={255}
                onChange={(e) => set("name", e.target.value)}
              />
            </div>
            <div className="field">
              <label htmlFor="gender">Gender</label>
              <input
                id="gender"
                value={values.gender}
                maxLength={50}
                onChange={(e) => set("gender", e.target.value)}
              />
            </div>
          </div>
        </section>
        <section>
          <h2>Physical information</h2>
          <div className="form-grid">
            {numberField("age", "Age")}
            {numberField("height_inches", "Height (inches)")}
            {numberField("weight_pounds", "Weight (pounds)")}
          </div>
        </section>
        <section>
          <h2>Default nutrition goals</h2>
          <div className="form-grid">
            {numberField("calorie_goal", "Calories", true)}
            {numberField("protein_goal", "Protein (g)", true)}
            {numberField("carbs_goal", "Carbohydrates (g)", true)}
            {numberField("fat_goal", "Fat (g)", true)}
            {numberField("sodium_max", "Sodium maximum (mg)")}
            {numberField("sugar_max", "Sugar maximum (g)")}
          </div>
        </section>
        {validation && (
          <p className="form-error" role="alert">
            {validation}
          </p>
        )}
        {update.error && (
          <p className="form-error" role="alert">
            {errorMessage(update.error)}
          </p>
        )}
        {update.isSuccess && (
          <p className="success-banner" role="status">
            Profile saved.
          </p>
        )}
        <button className="button button-primary" disabled={update.isPending}>
          {update.isPending ? "Saving…" : "Save changes"}
        </button>
      </form>
    </>
  );
}
