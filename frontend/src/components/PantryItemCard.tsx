import type { PantryItem } from "../types/api";

export function PantryItemCard({
  item,
  onEdit,
  onDelete,
  deleting,
}: {
  item: PantryItem;
  onEdit: () => void;
  onDelete: () => void;
  deleting: boolean;
}) {
  return (
    <article className="card pantry-card">
      <div className="card-heading">
        <div>
          <p className="eyebrow">{item.category}</p>
          <h3>{item.food_name}</h3>
          <p className="muted">
            {item.brand} · {item.serving_size} {item.serving_unit}
          </p>
        </div>
        <span className={`status-dot ${item.is_available ? "available" : "unavailable"}`}>
          {item.is_available ? "Available" : "Unavailable"}
        </span>
      </div>
      <div className="metric-grid">
        <div>
          <strong>{item.servings_available}</strong>
          <span>servings left</span>
        </div>
        <div>
          <strong>{item.max_servings_per_meal}</strong>
          <span>max per meal</span>
        </div>
        <div>
          <strong>{item.calories_per_serving}</strong>
          <span>cal / serving</span>
        </div>
        <div>
          <strong>{item.protein_g_per_serving}g</strong>
          <span>protein</span>
        </div>
      </div>
      {item.expiration_date && (
        <p className="detail-line">
          <strong>Expires</strong>{" "}
          {new Date(`${item.expiration_date}T00:00:00`).toLocaleDateString()}
        </p>
      )}
      {item.notes && <p className="card-note">{item.notes}</p>}
      <div className="card-actions">
        <button className="button button-secondary" onClick={onEdit}>
          Edit
        </button>
        <button className="button button-danger" onClick={onDelete} disabled={deleting}>
          {deleting ? "Deleting…" : "Delete"}
        </button>
      </div>
    </article>
  );
}
