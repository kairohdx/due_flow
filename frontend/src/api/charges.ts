import { apiFetch } from "./client";
import type {
  Charge,
  ChargePayload,
  ChargeStatus,
  JobAccepted,
  Page,
} from "./types";

export interface ChargeFilters {
  page: number;
  pageSize: number;
  search?: string;
  status?: ChargeStatus;
  dueFrom?: string;
  dueTo?: string;
}

function queryString(params: Record<string, string | number | undefined>) {
  const query = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== "") query.set(key, String(value));
  });
  return query.toString();
}

export function getCharges(filters: ChargeFilters): Promise<Page<Charge>> {
  const query = queryString({
    page: filters.page,
    page_size: filters.pageSize,
    search: filters.search,
    status: filters.status,
    due_from: filters.dueFrom,
    due_to: filters.dueTo,
  });
  return apiFetch(`/charges?${query}`);
}

export function getCharge(chargeId: string): Promise<Charge> {
  return apiFetch(`/charges/${chargeId}`);
}

export function createCharge(payload: ChargePayload): Promise<Charge> {
  return apiFetch("/charges", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function updateCharge(
  chargeId: string,
  payload: ChargePayload,
): Promise<Charge> {
  return apiFetch(`/charges/${chargeId}`, {
    method: "PUT",
    body: JSON.stringify(payload),
  });
}

export function markChargePaid(chargeId: string): Promise<Charge> {
  return apiFetch(`/charges/${chargeId}/mark-paid`, { method: "POST" });
}

export function cancelCharge(chargeId: string): Promise<Charge> {
  return apiFetch(`/charges/${chargeId}/cancel`, { method: "POST" });
}

export function processCharge(chargeId: string): Promise<JobAccepted> {
  return apiFetch(`/charges/${chargeId}/process`, {
    method: "POST",
    body: JSON.stringify({}),
  });
}
