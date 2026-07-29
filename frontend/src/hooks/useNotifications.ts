import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  getNotification,
  getChargeNotifications,
  getNotifications,
  getNotificationAttempts,
  getNotificationRecovery,
  retryNotification,
  retryNotificationWithTemplate,
  type NotificationFilters,
} from "../api/notifications";
import { getDashboardSummary, getJob } from "../api/dashboard";

export function useNotificationMetrics() {
  return useQuery({
    queryKey: ["dashboard", "summary"],
    queryFn: getDashboardSummary,
    refetchInterval: 10_000,
    refetchIntervalInBackground: false,
    placeholderData: (previous) => previous,
  });
}

export function useNotifications(filters: NotificationFilters) {
  return useQuery({
    queryKey: ["notifications", filters],
    queryFn: () => getNotifications(filters),
    placeholderData: (previous) => previous,
    refetchInterval: 10_000,
    refetchIntervalInBackground: false,
  });
}

export function useChargeNotifications(chargeId: string) {
  return useQuery({
    queryKey: ["charge-notifications", chargeId],
    queryFn: () => getChargeNotifications(chargeId),
    enabled: Boolean(chargeId),
    refetchInterval: 5_000,
    refetchIntervalInBackground: false,
  });
}

export function useNotification(notificationId: string) {
  return useQuery({
    queryKey: ["notification", notificationId],
    queryFn: () => getNotification(notificationId),
    enabled: Boolean(notificationId),
    refetchInterval: (query) => {
      const attempt = query.state.data;
      const awaitingMeta =
        ((attempt?.provider === "meta" &&
          attempt.submission_status === "succeeded") ||
          (attempt?.provider === "fake" &&
            attempt.submission_status === "simulated")) &&
        (attempt.delivery_status === "pending" ||
          attempt.delivery_status === "sent");
      return awaitingMeta ? 5_000 : false;
    },
    refetchIntervalInBackground: false,
  });
}

export function useNotificationRetry(notificationId: string) {
  const queryClient = useQueryClient();
  const [jobId, setJobId] = useState<string | null>(null);
  const recovery = useQuery({
    queryKey: ["notification-recovery", notificationId],
    queryFn: () => getNotificationRecovery(notificationId),
    enabled: Boolean(notificationId),
  });
  const attempts = useQuery({
    queryKey: ["notification-attempts", notificationId],
    queryFn: () => getNotificationAttempts(notificationId),
    enabled: Boolean(notificationId),
    refetchInterval: 5_000,
    refetchIntervalInBackground: false,
  });
  const retry = useMutation({
    mutationFn: () => retryNotification(notificationId),
    onSuccess: (accepted) => setJobId(accepted.job_id),
  });
  const retryTemplate = useMutation({
    mutationFn: () => retryNotificationWithTemplate(notificationId),
    onSuccess: (accepted) => setJobId(accepted.job_id),
  });
  const job = useQuery({
    queryKey: ["processing-job", jobId],
    queryFn: () => getJob(jobId as string),
    enabled: Boolean(jobId),
    refetchInterval: (query) =>
      query.state.data?.terminal ? false : 2_000,
  });

  useEffect(() => {
    if (!job.data?.terminal) return;
    void queryClient.invalidateQueries({
      queryKey: ["notification", notificationId],
    });
    void queryClient.invalidateQueries({
      queryKey: ["notification-recovery", notificationId],
    });
    void queryClient.invalidateQueries({
      queryKey: ["notification-attempts", notificationId],
    });
    void queryClient.invalidateQueries({ queryKey: ["notifications"] });
    void queryClient.invalidateQueries({ queryKey: ["dashboard"] });
  }, [job.data?.terminal, notificationId, queryClient]);

  return { recovery, attempts, retry, retryTemplate, job };
}
