import { Navigate, Outlet, useLocation } from "react-router-dom";
import { useAuth } from "./AuthContext";

export function ProtectedRoute() {
  const { isAuthenticated, isInitializing } = useAuth();
  const location = useLocation();
  if (isInitializing) {
    return <div className="state-panel">Restoring your session…</div>;
  }
  return isAuthenticated ? <Outlet /> : <Navigate to="/login" replace state={{ from: location }} />;
}
