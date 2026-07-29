import { apiFetch } from "./client";

export interface ChangePasswordPayload {
  current_password: string;
  new_password: string;
}

export function changePassword(payload: ChangePasswordPayload): Promise<void> {
  return apiFetch("/auth/change-password", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}
