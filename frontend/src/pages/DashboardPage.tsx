import { Link, useNavigate } from "react-router-dom";
import { useMealHistory } from "../api/meals";
import { usePantry } from "../api/pantry";
import { useUser } from "../api/users";
import { ErrorState, LoadingState } from "../components/AsyncState";
import { MealHistoryCard } from "../components/MealHistoryCard";

export function DashboardPage() {
  const navigate = useNavigate();
  const user = useUser();
  const pantry = usePantry();
  const meals = useMealHistory(3);
  if (user.isLoading || pantry.isLoading || meals.isLoading)
    return <LoadingState label="Preparing your dashboard…" />;
  if (user.error) return <ErrorState error={user.error} retry={() => user.refetch()} />;
  return (
    <>
      <header className="page-header dashboard-header">
        <div>
          <p className="eyebrow">Today’s pantry</p>
          <h1>Welcome back, {user.data?.name.split(" ")[0]}.</h1>
          <p>See what you have and turn it into your next meal.</p>
        </div>
        <Link className="button button-primary" to="/generate-meal">
          Generate a meal
        </Link>
      </header>
      <section className="summary-grid">
        <article className="summary-card accent">
          <span>Available foods</span>
          <strong>{pantry.data?.length ?? 0}</strong>
          <small>ready for meal generation</small>
        </article>
        <article className="summary-card">
          <span>Total servings</span>
          <strong>
            {pantry.data?.reduce((sum, item) => sum + item.servings_available, 0).toFixed(1) ?? "0"}
          </strong>
          <small>across your pantry</small>
        </article>
        <article className="summary-card">
          <span>Recent meals</span>
          <strong>{meals.data?.length ?? 0}</strong>
          <small>among your latest three</small>
        </article>
      </section>
      <section className="quick-actions">
        <Link to="/pantry" className="action-card">
          <span className="action-icon">+</span>
          <div>
            <strong>Add pantry food</strong>
            <small>Search the food catalog</small>
          </div>
        </Link>
        <Link to="/generate-meal" className="action-card">
          <span className="action-icon">↗</span>
          <div>
            <strong>Build my next meal</strong>
            <small>Use your nutrition goals</small>
          </div>
        </Link>
      </section>
      <section className="section-block">
        <div className="section-heading">
          <div>
            <p className="eyebrow">Meal history</p>
            <h2>Recently accepted</h2>
          </div>
          <Link className="text-button" to="/meals">
            View all →
          </Link>
        </div>
        {meals.error ? (
          <ErrorState error={meals.error} retry={() => meals.refetch()} />
        ) : meals.data?.length ? (
          <div className="card-grid">
            {meals.data.map((meal) => (
              <MealHistoryCard
                key={meal.id}
                meal={meal}
                onOpen={() => navigate(`/meals?meal=${meal.id}`)}
              />
            ))}
          </div>
        ) : (
          <div className="state-panel">No meals logged yet. Generate one when you’re ready.</div>
        )}
      </section>
    </>
  );
}
