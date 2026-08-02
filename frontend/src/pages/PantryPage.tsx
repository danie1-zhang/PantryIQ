import { useState } from "react";
import { errorMessage } from "../api/client";
import { useDeletePantryItem, usePantry } from "../api/pantry";
import { AddFoodForm } from "../components/AddFoodForm";
import { EmptyState, ErrorState, LoadingState } from "../components/AsyncState";
import { EditPantryItemForm } from "../components/EditPantryItemForm";
import { Modal } from "../components/Modal";
import { PantryItemCard } from "../components/PantryItemCard";
import type { PantryItem } from "../types/api";

export function PantryPage() {
  const pantry = usePantry(false);
  const remove = useDeletePantryItem();
  const [adding, setAdding] = useState(false);
  const [editing, setEditing] = useState<PantryItem | null>(null);
  const [feedback, setFeedback] = useState("");
  function deleteItem(item: PantryItem) {
    if (!window.confirm(`Remove ${item.food_name} from your pantry?`)) return;
    remove.mutate(item.id, { onSuccess: () => setFeedback(`${item.food_name} was removed.`) });
  }
  return (
    <>
      <header className="page-header">
        <div>
          <p className="eyebrow">Inventory</p>
          <h1>Your pantry</h1>
          <p>Keep quantities current so recommendations match what you can make.</p>
        </div>
        <button className="button button-primary" onClick={() => setAdding(true)}>
          + Add food
        </button>
      </header>
      {feedback && (
        <div className="success-banner" role="status">
          {feedback}
          <button aria-label="Dismiss" onClick={() => setFeedback("")}>
            ×
          </button>
        </div>
      )}
      {remove.error && (
        <p className="form-error" role="alert">
          {errorMessage(remove.error)}
        </p>
      )}
      {pantry.isLoading ? (
        <LoadingState label="Loading pantry…" />
      ) : pantry.error ? (
        <ErrorState error={pantry.error} retry={() => pantry.refetch()} />
      ) : pantry.data?.length ? (
        <div className="card-grid pantry-grid">
          {pantry.data.map((item) => (
            <PantryItemCard
              key={item.id}
              item={item}
              onEdit={() => setEditing(item)}
              onDelete={() => deleteItem(item)}
              deleting={remove.isPending && remove.variables === item.id}
            />
          ))}
        </div>
      ) : (
        <EmptyState title="Your pantry is empty">
          <p>Search the food catalog and add your first ingredient.</p>
          <button className="button button-primary" onClick={() => setAdding(true)}>
            Add food
          </button>
        </EmptyState>
      )}
      {adding && (
        <Modal title="Add food" onClose={() => setAdding(false)}>
          <AddFoodForm
            onComplete={() => {
              setAdding(false);
              setFeedback("Pantry updated.");
            }}
          />
        </Modal>
      )}
      {editing && (
        <Modal title="Update pantry item" onClose={() => setEditing(null)}>
          <EditPantryItemForm
            item={editing}
            onComplete={() => {
              setEditing(null);
              setFeedback("Changes saved.");
            }}
          />
        </Modal>
      )}
    </>
  );
}
