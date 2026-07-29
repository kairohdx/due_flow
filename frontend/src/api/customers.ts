import { apiFetch } from "./client";
import type { Charge, Customer, CustomerPayload, Page } from "./types";

export interface CustomerFilters {
  page: number;
  pageSize: number;
  search?: string;
  active?: boolean;
}

function queryString(params: Record<string, string | number | boolean | undefined>) {
  const query = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== "") query.set(key, String(value));
  });
  return query.toString();
}

export function getCustomers(
  filters: CustomerFilters,
): Promise<Page<Customer>> {
  const query = queryString({
    page: filters.page,
    page_size: filters.pageSize,
    search: filters.search,
    active: filters.active,
  });
  return apiFetch(`/customers?${query}`);
}

export function getCustomer(customerId: string): Promise<Customer> {
  return apiFetch(`/customers/${customerId}`);
}

export function createCustomer(payload: CustomerPayload): Promise<Customer> {
  return apiFetch("/customers", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function updateCustomer(
  customerId: string,
  payload: CustomerPayload,
): Promise<Customer> {
  return apiFetch(`/customers/${customerId}`, {
    method: "PUT",
    body: JSON.stringify(payload),
  });
}

export function getCustomerCharges(
  customerId: string,
  page = 1,
): Promise<Page<Charge>> {
  const query = queryString({
    customer_id: customerId,
    page,
    page_size: 25,
  });
  return apiFetch(`/charges?${query}`);
}
