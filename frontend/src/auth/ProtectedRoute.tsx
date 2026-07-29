import type { ReactNode } from "react";
import { Navigate, useLocation } from "react-router-dom";
import { useAuthState } from "./authStore";
import { AppLoading } from "../components/feedback/AppLoading";

export function ProtectedRoute({ children }: { children: ReactNode }) {
  const auth = useAuthState();
  const location = useLocation();
  if (!auth.initialized) return <AppLoading />;
  if (!auth.accessToken) {
    return (
      <Navigate
        to="/login"
        replace
        state={{ from: `${location.pathname}${location.search}${location.hash}` }}
      />
    );
  }
  return children;
}
