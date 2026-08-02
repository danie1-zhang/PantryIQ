import { createContext, useContext, useMemo, useState, type ReactNode } from "react";

const AUTH_KEY = "pantryiq_development_login";

interface AuthValue {
  isAuthenticated: boolean;
  login: () => void;
  logout: () => void;
}

const AuthContext = createContext<AuthValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [isAuthenticated, setAuthenticated] = useState(
    () => localStorage.getItem(AUTH_KEY) === "true",
  );
  const value = useMemo<AuthValue>(
    () => ({
      isAuthenticated,
      login: () => {
        localStorage.setItem(AUTH_KEY, "true");
        setAuthenticated(true);
      },
      logout: () => {
        localStorage.removeItem(AUTH_KEY);
        localStorage.removeItem("pantryiq_token");
        setAuthenticated(false);
      },
    }),
    [isAuthenticated],
  );
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

// eslint-disable-next-line react-refresh/only-export-components
export function useAuth(): AuthValue {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth must be used inside AuthProvider");
  return context;
}
