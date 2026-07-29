import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  createCustomer,
  getCustomer,
  getCustomerCharges,
  getCustomers,
  updateCustomer,
  type CustomerFilters,
} from "../api/customers";
import type { CustomerPayload } from "../api/types";

export function useCustomers(filters: CustomerFilters) {
  return useQuery({
    queryKey: ["customers", filters],
    queryFn: () => getCustomers(filters),
    placeholderData: (previous) => previous,
  });
}

export function useCustomer(customerId: string) {
  return useQuery({
    queryKey: ["customer", customerId],
    queryFn: () => getCustomer(customerId),
    enabled: Boolean(customerId),
  });
}

export function useCustomerCharges(customerId: string, page: number) {
  return useQuery({
    queryKey: ["charges", "customer", customerId, page],
    queryFn: () => getCustomerCharges(customerId, page),
    enabled: Boolean(customerId),
    placeholderData: (previous) => previous,
  });
}

export function useCreateCustomer() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: createCustomer,
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["customers"] });
      void queryClient.invalidateQueries({ queryKey: ["dashboard"] });
    },
  });
}

export function useUpdateCustomer(customerId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: CustomerPayload) =>
      updateCustomer(customerId, payload),
    onSuccess: (customer) => {
      queryClient.setQueryData(["customer", customerId], customer);
      void queryClient.invalidateQueries({ queryKey: ["customers"] });
    },
  });
}
