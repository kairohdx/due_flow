import {
  clearAuthState,
  getAuthState,
  setAuthSession,
} from "../auth/authStore";
import { refreshAccessToken } from "../auth/authService";
import { API_BASE_URL, REQUEST_TIMEOUT_MS } from "../config";
import { apiErrorFromResponse } from "./errors";

let refreshInFlight: Promise<string | null> | null = null;

export async function refreshAccessTokenOnce(): Promise<string | null> {
  if (!refreshInFlight) {
    refreshInFlight = (async () => {
      try {
        const response = await refreshAccessToken();
        setAuthSession(response.access_token);
        return response.access_token;
      } catch {
        clearAuthState();
        return null;
      } finally {
        refreshInFlight = null;
      }
    })();
  }
  return refreshInFlight;
}

async function fetchWithAuth(
  path: string,
  init: RequestInit = {},
  canRefresh = true,
): Promise<Response> {
  const controller = new AbortController();
  const timeoutId = window.setTimeout(
    () => controller.abort(),
    REQUEST_TIMEOUT_MS,
  );
  try {
    const token = getAuthState().accessToken;
    const response = await fetch(`${API_BASE_URL}${path}`, {
      ...init,
      signal: controller.signal,
      headers: {
        "Content-Type": "application/json",
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
        ...init.headers,
      },
    });
    if (response.status === 401 && canRefresh) {
      const refreshedToken = await refreshAccessTokenOnce();
      if (refreshedToken) return fetchWithAuth(path, init, false);
      window.location.assign("/login");
    }
    return response;
  } finally {
    window.clearTimeout(timeoutId);
  }
}

export async function apiFetch<T>(
  path: string,
  init?: RequestInit,
): Promise<T> {
  const response = await fetchWithAuth(path, init);
  if (!response.ok) throw await apiErrorFromResponse(response);
  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

export function resetRefreshForTests(): void {
  refreshInFlight = null;
}
