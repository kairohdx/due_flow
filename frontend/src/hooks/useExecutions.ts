import { useQuery } from "@tanstack/react-query";
import {
  getExecution,
  getExecutions,
  type ExecutionFilters,
} from "../api/executions";

const ACTIVE_POLLING_MS = 2_000;
const STABLE_POLLING_MS = 15_000;

export function useExecutions(filters: ExecutionFilters) {
  return useQuery({
    queryKey: ["processing-jobs", filters],
    queryFn: () => getExecutions(filters),
    placeholderData: (previous) => previous,
    refetchInterval: (query) => {
      const active = query.state.data?.items.some(
        (item) => item.status === "queued" || item.status === "processing",
      );
      return active ? ACTIVE_POLLING_MS : STABLE_POLLING_MS;
    },
    refetchIntervalInBackground: false,
  });
}

export function useExecution(executionId: string) {
  return useQuery({
    queryKey: ["processing-job", executionId],
    queryFn: () => getExecution(executionId),
    enabled: Boolean(executionId),
    refetchInterval: (query) => query.state.data?.terminal ? false : ACTIVE_POLLING_MS,
    refetchIntervalInBackground: false,
  });
}
