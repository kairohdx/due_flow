import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  disableAutomation,
  enableAutomation,
  enqueueProcessing,
  getAutomation,
  getDashboardSummary,
  getJob,
} from "../api/dashboard";

const DASHBOARD_POLLING_MS = 10_000;
const ACTIVE_JOB_POLLING_MS = 2_000;

export function useDashboard() {
  const queryClient = useQueryClient();
  const [trackedJobId, setTrackedJobId] = useState<string | null>(null);

  const summary = useQuery({
    queryKey: ["dashboard", "summary"],
    queryFn: getDashboardSummary,
    refetchInterval: DASHBOARD_POLLING_MS,
    refetchIntervalInBackground: false,
    placeholderData: (previous) => previous,
  });

  const automation = useQuery({
    queryKey: ["automation"],
    queryFn: getAutomation,
    refetchInterval: DASHBOARD_POLLING_MS,
    refetchIntervalInBackground: false,
    placeholderData: (previous) => previous,
  });

  const trackedJob = useQuery({
    queryKey: ["processing-job", trackedJobId],
    queryFn: () => getJob(trackedJobId as string),
    enabled: Boolean(trackedJobId),
    refetchInterval: (query) => {
      const job = query.state.data;
      return job?.terminal ? false : ACTIVE_JOB_POLLING_MS;
    },
    refetchIntervalInBackground: false,
  });

  useEffect(() => {
    if (!trackedJob.data?.terminal) return;
    void queryClient.invalidateQueries({ queryKey: ["dashboard"] });
    void queryClient.invalidateQueries({ queryKey: ["processing-jobs"] });
  }, [queryClient, trackedJob.data?.terminal]);

  const enable = useMutation({
    mutationFn: enableAutomation,
    onSuccess: (state) => {
      queryClient.setQueryData(["automation"], state);
      void queryClient.invalidateQueries({ queryKey: ["processing-jobs"] });
    },
  });

  const disable = useMutation({
    mutationFn: disableAutomation,
    onSuccess: (state) => queryClient.setQueryData(["automation"], state),
  });

  const processNow = useMutation({
    mutationFn: enqueueProcessing,
    onSuccess: (accepted) => {
      setTrackedJobId(accepted.job_id);
      void queryClient.invalidateQueries({ queryKey: ["dashboard"] });
      void queryClient.invalidateQueries({ queryKey: ["processing-jobs"] });
    },
  });

  function refreshAll() {
    void queryClient.invalidateQueries({ queryKey: ["dashboard"] });
    void queryClient.invalidateQueries({ queryKey: ["automation"] });
    void queryClient.invalidateQueries({ queryKey: ["processing-jobs"] });
  }

  return {
    summary,
    automation,
    trackedJob,
    enable,
    disable,
    processNow,
    trackedJobId,
    refreshAll,
  };
}
