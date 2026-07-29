import { useSyncExternalStore } from "react";
import type { CurrentUser } from "./types";

interface AuthState {
  accessToken: string | null;
  user: CurrentUser | null;
  initialized: boolean;
}

const state: AuthState = {
  accessToken: null,
  user: null,
  initialized: false,
};

let snapshot: AuthState = { ...state };
const listeners = new Set<() => void>();

function emit(): void {
  snapshot = { ...state };
  listeners.forEach((listener) => listener());
}

export function getAuthState(): AuthState {
  return state;
}

export function setAuthSession(
  accessToken: string,
  user?: CurrentUser,
): void {
  state.accessToken = accessToken;
  if (user !== undefined) state.user = user;
  emit();
}

export function setCurrentUser(user: CurrentUser): void {
  state.user = user;
  emit();
}

export function markAuthInitialized(): void {
  state.initialized = true;
  emit();
}

export function clearAuthState(): void {
  state.accessToken = null;
  state.user = null;
  state.initialized = true;
  emit();
}

export function resetAuthStateForTests(): void {
  state.accessToken = null;
  state.user = null;
  state.initialized = false;
  emit();
}

export function subscribeAuthState(listener: () => void): () => void {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

export function useAuthState(): AuthState {
  return useSyncExternalStore(
    subscribeAuthState,
    () => snapshot,
    () => snapshot,
  );
}
