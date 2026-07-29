import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  cancelCharge,
  createCharge,
  getCharge,
  getCharges,
  markChargePaid,
  processCharge,
  updateCharge,
  type ChargeFilters,
} from "../api/charges";
import type { ChargePayload } from "../api/types";

export function useCharges(filters: ChargeFilters) {
  return useQuery({
    queryKey: ["charges", filters],
    queryFn: () => getCharges(filters),
    placeholderData: (previous) => previous,
  });
}

export function useCharge(chargeId: string) {
  return useQuery({
    queryKey: ["charge", chargeId],
    queryFn: () => getCharge(chargeId),
    enabled: Boolean(chargeId),
  });
}

function useInvalidateCharge(chargeId?: string) {
  const queryClient = useQueryClient();
  return (charge?: unknown) => {
    if (chargeId && charge) queryClient.setQueryData(["charge", chargeId], charge);
    void queryClient.invalidateQueries({ queryKey: ["charges"] });
    void queryClient.invalidateQueries({ queryKey: ["dashboard"] });
  };
}

export function useCreateCharge() {
  const invalidate = useInvalidateCharge();
  return useMutation({ mutationFn: createCharge, onSuccess: () => invalidate() });
}

export function useUpdateCharge(chargeId: string) {
  const invalidate = useInvalidateCharge(chargeId);
  return useMutation({
    mutationFn: (payload: ChargePayload) => updateCharge(chargeId, payload),
    onSuccess: invalidate,
  });
}

export function useMarkChargePaid(chargeId: string) {
  const invalidate = useInvalidateCharge(chargeId);
  return useMutation({
    mutationFn: () => markChargePaid(chargeId),
    onSuccess: invalidate,
  });
}

export function useCancelCharge(chargeId: string) {
  const invalidate = useInvalidateCharge(chargeId);
  return useMutation({
    mutationFn: () => cancelCharge(chargeId),
    onSuccess: invalidate,
  });
}

export function useProcessCharge(chargeId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => processCharge(chargeId),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["processing-jobs"] });
      void queryClient.invalidateQueries({ queryKey: ["dashboard"] });
    },
  });
}
