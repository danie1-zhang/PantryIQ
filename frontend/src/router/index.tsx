import { Navigate, createBrowserRouter } from "react-router-dom";
import { ProtectedRoute } from "../auth/ProtectedRoute";
import { AppLayout } from "../components/AppLayout";
import { DashboardPage } from "../pages/DashboardPage";
import { GenerateMealPage } from "../pages/GenerateMealPage";
import { LoginPage } from "../pages/LoginPage";
import { MealHistoryPage } from "../pages/MealHistoryPage";
import { PantryPage } from "../pages/PantryPage";
import { ProfilePage } from "../pages/ProfilePage";
import { RegisterPage } from "../pages/RegisterPage";

export const router = createBrowserRouter([
  { path: "/login", element: <LoginPage /> },
  { path: "/register", element: <RegisterPage /> },
  {
    element: <ProtectedRoute />,
    children: [
      {
        element: <AppLayout />,
        children: [
          { path: "/dashboard", element: <DashboardPage /> },
          { path: "/pantry", element: <PantryPage /> },
          { path: "/generate-meal", element: <GenerateMealPage /> },
          { path: "/meals", element: <MealHistoryPage /> },
          { path: "/profile", element: <ProfilePage /> },
        ],
      },
    ],
  },
  { path: "*", element: <Navigate to="/dashboard" replace /> },
]);
