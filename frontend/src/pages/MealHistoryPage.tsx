import { useState } from "react";
import { useLocation, useSearchParams } from "react-router-dom";
import { useMealDetail, useMealHistory } from "../api/meals";
import { ErrorState, LoadingState } from "../components/AsyncState";
import { MealHistoryCard } from "../components/MealHistoryCard";
import { Modal } from "../components/Modal";

export function MealHistoryPage() {
  const history = useMealHistory();
  const location = useLocation();
  const [params, setParams] = useSearchParams();
  const [message] = useState((location.state as { message?: string } | null)?.message);
  const selectedId = params.get("meal");
  const detail = useMealDetail(selectedId);

  if (history.isLoading) return <LoadingState label="Loading meal history…" />;
  return (
    <>
      <header className="page-header">
        <div>
          <p className="eyebrow">Meal history</p>
          <h1>Your accepted meals</h1>
          <p>Review what you ate and the nutrition recorded at the time.</p>
        </div>
      </header>
      {message && (
        <p className="success-banner" role="status">
          {message}
        </p>
      )}
      {history.error ? (
        <ErrorState error={history.error} retry={() => history.refetch()} />
      ) : history.data?.length ? (
        <div className="card-grid">
          {history.data.map((meal) => (
            <MealHistoryCard
              key={meal.id}
              meal={meal}
              onOpen={() => setParams({ meal: meal.id })}
            />
          ))}
        </div>
      ) : (
        <div className="state-panel">
          <strong>No accepted meals yet.</strong>
          <p>Generate a meal and accept it to start your history.</p>
        </div>
      )}
      {selectedId && (
        <Modal title="Meal details" onClose={() => setParams({})}>
          {detail.isLoading ? (
            <LoadingState label="Loading meal…" />
          ) : detail.error ? (
            <ErrorState error={detail.error} retry={() => detail.refetch()} />
          ) : (
            detail.data && (
              <div className="meal-detail">
                <p className="detail-date">{new Date(detail.data.eaten_at).toLocaleString()}</p>
                <div className="meal-foods">
                  {detail.data.items.map((item) => (
                    <div key={item.food_id}>
                      <span>{item.food_name}</span>
                      <strong>
                        {item.servings} serving{item.servings === 1 ? "" : "s"}
                      </strong>
                    </div>
                  ))}
                </div>
                <div className="nutrition-strip">
                  <div>
                    <strong>{detail.data.totals.calories}</strong>
                    <span>Calories</span>
                  </div>
                  <div>
                    <strong>{detail.data.totals.protein_g}g</strong>
                    <span>Protein</span>
                  </div>
                  <div>
                    <strong>{detail.data.totals.carbs_g}g</strong>
                    <span>Carbs</span>
                  </div>
                  <div>
                    <strong>{detail.data.totals.fat_g}g</strong>
                    <span>Fat</span>
                  </div>
                </div>
                {detail.data.rating && (
                  <p>
                    <strong>Rating:</strong> {detail.data.rating} / 5
                  </p>
                )}
                {detail.data.notes && (
                  <p>
                    <strong>Notes:</strong> {detail.data.notes}
                  </p>
                )}
              </div>
            )
          )}
        </Modal>
      )}
    </>
  );
}
