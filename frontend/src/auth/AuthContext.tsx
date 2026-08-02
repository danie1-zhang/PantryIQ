import { useQueryClient } from "@tanstack/react-query";
import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { login as loginRequest, logout as logoutRequest } from "../api/auth";
import { apiRequest, refreshAccessToken } from "../api/client";
import type { AuthUser, LoginInput } from "../types/api";
import { setAccessToken, setAuthenticationLostHandler } from "./authStorage";

interface AuthValue {
  isAuthenticated: boolean;
  isInitializing: boolean;
  user: AuthUser | null;
  login: (credentials: LoginInput) => Promise<void>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient();
  const [user, setUser] = useState<AuthUser | null>(null);
  const [isInitializing, setInitializing] = useState(true);

  useEffect(() => {
    setAuthenticationLostHandler(() => {
      setUser(null);
      queryClient.clear();
    });
    void (async () => {
      try {
        await refreshAccessToken();
        setUser(await apiRequest<AuthUser>("/users/me"));
      } catch {
        setAccessToken(null);
        setUser(null);
      } finally {
        setInitializing(false);
      }
    })();
    return () => setAuthenticationLostHandler(null);
  }, [queryClient]);

  const value = useMemo<AuthValue>(
    () => ({
      isAuthenticated: user !== null,
      isInitializing,
      user,
      login: async (credentials) => {
        const response = await loginRequest(credentials);
        await queryClient.cancelQueries();
        queryClient.clear();
        setAccessToken(response.access_token);
        setUser(response.user);
      },
      logout: async () => {
        try {
          await logoutRequest();
        } finally {
          setAccessToken(null);
          setUser(null);
          await queryClient.cancelQueries();
          queryClient.clear();
        }
      },
    }),
    [isInitializing, queryClient, user],
  );
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

// eslint-disable-next-line react-refresh/only-export-components
export function useAuth(): AuthValue {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth must be used inside AuthProvider");
  return context;
}
