import { Outlet } from "react-router-dom";
import { Navigation } from "./Navigation";

export function AppLayout() {
  return (
    <div className="app-shell">
      <Navigation />
      <main className="page-shell">
        <Outlet />
      </main>
    </div>
  );
}
