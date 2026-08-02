import type { MealHistoryItem } from "../types/api";

export function MealHistoryCard({ meal, onOpen }: { meal: MealHistoryItem; onOpen: () => void }) {
  return (
    <article className="card history-card">
      <div className="card-heading">
        <div>
          <p className="eyebrow">
            {new Date(meal.eaten_at).toLocaleDateString(undefined, {
              month: "short",
              day: "numeric",
              year: "numeric",
            })}
          </p>
          <h3>
            {new Date(meal.eaten_at).toLocaleTimeString(undefined, {
              hour: "numeric",
              minute: "2-digit",
            })}
          </h3>
        </div>
        {meal.rating && <span className="rating">{"★".repeat(meal.rating)}</span>}
      </div>
      <p>{meal.items.map((item) => `${item.food_name} (${item.servings})`).join(" · ")}</p>
      <div className="macro-row">
        <span>{meal.total_calories} cal</span>
        <span>{meal.total_protein_g}g protein</span>
        <span>{meal.total_carbs_g}g carbs</span>
        <span>{meal.total_fat_g}g fat</span>
      </div>
      {meal.notes && <p className="card-note">{meal.notes}</p>}
      <button className="text-button" onClick={onOpen}>
        View meal details →
      </button>
    </article>
  );
}
