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

function getToken(): string | null {
  return localStorage.getItem("pantryiq_token");
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

export async function apiRequest<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = getToken();
  const headers = new Headers(options.headers);
  if (options.body) headers.set("Content-Type", "application/json");
  if (token) headers.set("Authorization", `Bearer ${token}`);

  const response = await fetch(`${API_BASE_URL}${path}`, { ...options, headers });
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
