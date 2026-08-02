import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { errorMessage } from "../api/client";
import { useAcceptMeal, useGenerateMeal } from "../api/meals";
import { useUser } from "../api/users";
import { ErrorState, LoadingState } from "../components/AsyncState";
import { MealConstraintsForm } from "../components/MealConstraintsForm";
import { MealRecommendationCard } from "../components/MealRecommendationCard";
import type { MealConstraints, MealExclusion, MealRecommendation } from "../types/api";

export function GenerateMealPage() {
  const profile = useUser();
  const generate = useGenerateMeal();
  const accept = useAcceptMeal();
  const navigate = useNavigate();
  const [lastConstraints, setLastConstraints] = useState<MealConstraints | null>(null);
  const [excludedMeals, setExcludedMeals] = useState<MealExclusion[]>([]);

  function generateMeal(values: MealConstraints) {
    const baseConstraints = { ...values, excluded_meals: undefined };
    setLastConstraints(baseConstraints);
    setExcludedMeals([]);
    accept.reset();
    generate.mutate(baseConstraints, {
      onSuccess: (meal) => setExcludedMeals([toExclusion(meal)]),
    });
  }

  function regenerateMeal() {
    if (!lastConstraints) return;
    accept.reset();
    generate.mutate(
      { ...lastConstraints, excluded_meals: excludedMeals },
      {
        onSuccess: (meal) =>
          setExcludedMeals((current) => [...current, toExclusion(meal)].slice(-20)),
      },
    );
  }

  function acceptMeal(rating: number | null, notes: string) {
    if (!generate.data) return;
    accept.mutate(
      {
        items: generate.data.items.map(({ food_id, servings }) => ({ food_id, servings })),
        rating,
        notes: notes.trim() || null,
      },
      {
        onSuccess: () =>
          navigate("/meals", { state: { message: "Meal accepted and pantry updated." } }),
      },
    );
  }

  if (profile.isLoading) return <LoadingState label="Loading your nutrition goals…" />;
  if (profile.error) return <ErrorState error={profile.error} retry={() => profile.refetch()} />;

  return (
    <>
      <header className="page-header">
        <div>
          <p className="eyebrow">Meal optimizer</p>
          <h1>Build a meal from your pantry</h1>
          <p>Set your targets and we’ll search your available foods for the closest match.</p>
        </div>
      </header>
      <MealConstraintsForm
        profile={profile.data}
        submitting={generate.isPending}
        onSubmit={generateMeal}
      />
      {generate.error && (
        <div className="state-panel state-error" role="alert">
          <strong>We couldn’t generate a meal.</strong>
          <p>{errorMessage(generate.error)}</p>
        </div>
      )}
      {generate.data && (
        <MealRecommendationCard
          meal={generate.data}
          accepting={accept.isPending}
          acceptError={accept.error}
          onAccept={acceptMeal}
          onRegenerate={regenerateMeal}
        />
      )}
    </>
  );
}

function toExclusion(meal: MealRecommendation): MealExclusion {
  return {
    items: meal.items.map(({ food_id, servings }) => ({ food_id, servings })),
  };
}
