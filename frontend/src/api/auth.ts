import { apiRequest } from "./client";
import type { AuthResponse, AuthUser, LoginInput, RegisterInput } from "../types/api";

export function register(input: RegisterInput): Promise<AuthUser> {
  return apiRequest<AuthUser>("/auth/register", {
    method: "POST",
    body: JSON.stringify(input),
  });
}

export function login(input: LoginInput): Promise<AuthResponse> {
  return apiRequest<AuthResponse>("/auth/login", {
    method: "POST",
    body: JSON.stringify(input),
  });
}

export function logout(): Promise<void> {
  return apiRequest<void>("/auth/logout", { method: "POST" });
}
