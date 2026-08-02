import type { ReactNode } from "react";
import { errorMessage } from "../api/client";

export function LoadingState({ label = "Loading…" }: { label?: string }) {
  return (
    <div className="state-panel" role="status">
      <span className="spinner" />
      {label}
    </div>
  );
}

export function ErrorState({ error, retry }: { error: unknown; retry?: () => void }) {
  return (
    <div className="state-panel error-panel" role="alert">
      <strong>We couldn’t load this.</strong>
      <span>{errorMessage(error)}</span>
      {retry && (
        <button className="button button-secondary" onClick={retry}>
          Try again
        </button>
      )}
    </div>
  );
}

export function EmptyState({ title, children }: { title: string; children: ReactNode }) {
  return (
    <div className="state-panel empty-state">
      <strong>{title}</strong>
      <div>{children}</div>
    </div>
  );
}
