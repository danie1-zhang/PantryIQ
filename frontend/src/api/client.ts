import { getAccessToken, notifyAuthenticationLost, setAccessToken } from "../auth/authStorage";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "/api/v1";

export class ApiError extends Error {
  constructor(
    message: string,
    public readonly status: number,
    public readonly details?: unknown,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

function responseMessage(details: unknown, status: number): string {
  if (!details || typeof details !== "object" || !("detail" in details))
    return `Request failed with status ${status}`;
  const detail = (details as { detail: unknown }).detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    const messages = detail.flatMap((entry) =>
      typeof entry === "object" && entry && "msg" in entry ? [String(entry.msg)] : [],
    );
    if (messages.length) return messages.join(" ");
  }
  return "The request could not be processed. Please check the form and try again.";
}

async function sendRequest(path: string, options: RequestInit): Promise<Response> {
  const token = getAccessToken();
  const headers = new Headers(options.headers);
  if (options.body) headers.set("Content-Type", "application/json");
  if (token) headers.set("Authorization", `Bearer ${token}`);

  return fetch(`${API_BASE_URL}${path}`, { ...options, headers, credentials: "include" });
}

let refreshPromise: Promise<string> | null = null;

export async function refreshAccessToken(): Promise<string> {
  if (!refreshPromise) {
    refreshPromise = (async () => {
      const response = await fetch(`${API_BASE_URL}/auth/refresh`, {
        method: "POST",
        credentials: "include",
      });
      if (!response.ok) {
        notifyAuthenticationLost();
        throw new ApiError("Your session has expired. Please log in again.", response.status);
      }
      const body = (await response.json()) as { access_token: string };
      setAccessToken(body.access_token);
      return body.access_token;
    })().finally(() => {
      refreshPromise = null;
    });
  }
  return refreshPromise;
}

export async function apiRequest<T>(path: string, options: RequestInit = {}): Promise<T> {
  let response = await sendRequest(path, options);
  const canRefresh = response.status === 401 && !path.startsWith("/auth/");
  if (canRefresh) {
    try {
      await refreshAccessToken();
      response = await sendRequest(path, options);
    } catch {
      throw new ApiError("Your session has expired. Please log in again.", 401);
    }
  }

  if (!response.ok) {
    let details: unknown;
    try {
      details = await response.json();
    } catch {
      details = null;
    }
    throw new ApiError(responseMessage(details, response.status), response.status, details);
  }
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

export function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : "Something went wrong. Please try again.";
}
