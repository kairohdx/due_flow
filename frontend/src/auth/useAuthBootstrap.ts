import { useEffect } from "react";
import {
  clearAuthState,
  markAuthInitialized,
  setAuthSession,
} from "./authStore";
import { refreshAccessTokenOnce } from "../api/client";
import { getMe } from "./authService";

export function useAuthBootstrap(): void {
  useEffect(() => {
    let cancelled = false;
    async function bootstrap(): Promise<void> {
      try {
        const accessToken = await refreshAccessTokenOnce();
        if (!accessToken) throw new Error("sessão ausente");
        const user = await getMe(accessToken);
        if (!cancelled) setAuthSession(accessToken, user);
      } catch {
        if (!cancelled) clearAuthState();
      } finally {
        if (!cancelled) markAuthInitialized();
      }
    }
    void bootstrap();
    return () => {
      cancelled = true;
    };
  }, []);
}
