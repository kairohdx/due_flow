import { API_BASE_URL, REQUEST_TIMEOUT_MS } from "../config";
import { apiErrorFromResponse } from "../api/errors";
import type {
  AccessTokenResponse,
  CurrentUser,
  LoginPayload,
} from "./types";

async function authFetch<T>(
  path: string,
  init: RequestInit,
  includeCredentials = false,
): Promise<T> {
  const controller = new AbortController();
  const timeoutId = window.setTimeout(
    () => controller.abort(),
    REQUEST_TIMEOUT_MS,
  );
  try {
    const response = await fetch(`${API_BASE_URL}${path}`, {
      ...init,
      credentials: includeCredentials ? "include" : init.credentials,
      signal: controller.signal,
      headers: {
        "Content-Type": "application/json",
        ...init.headers,
      },
    });
    if (!response.ok) throw await apiErrorFromResponse(response);
    if (response.status === 204) return undefined as T;
    return (await response.json()) as T;
  } finally {
    window.clearTimeout(timeoutId);
  }
}

export function login(payload: LoginPayload): Promise<AccessTokenResponse> {
  return authFetch(
    "/auth/login",
    { method: "POST", body: JSON.stringify(payload) },
    true,
  );
}

export function refreshAccessToken(): Promise<AccessTokenResponse> {
  return authFetch("/auth/refresh", { method: "POST", body: "{}" }, true);
}

export function logout(): Promise<void> {
  return authFetch("/auth/logout", { method: "POST", body: "{}" }, true);
}

export function getMe(accessToken: string): Promise<CurrentUser> {
  return authFetch("/auth/me", {
    method: "GET",
    headers: { Authorization: `Bearer ${accessToken}` },
  });
}
