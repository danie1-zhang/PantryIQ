let accessToken: string | null = null;
let authenticationLostHandler: (() => void) | null = null;

export function getAccessToken(): string | null {
  return accessToken;
}

export function setAccessToken(token: string | null): void {
  accessToken = token;
}

export function setAuthenticationLostHandler(handler: (() => void) | null): void {
  authenticationLostHandler = handler;
}

export function notifyAuthenticationLost(): void {
  accessToken = null;
  authenticationLostHandler?.();
}
