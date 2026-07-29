import { useQuery } from "@tanstack/react-query";
import {
  getNotification,
  getChargeNotifications,
  getNotifications,
  type NotificationFilters,
} from "../api/notifications";
import { getDashboardSummary } from "../api/dashboard";

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
        attempt?.provider === "meta" &&
        attempt.submission_status === "succeeded" &&
        (attempt.delivery_status === "pending" ||
          attempt.delivery_status === "sent");
      return awaitingMeta ? 5_000 : false;
    },
    refetchIntervalInBackground: false,
  });
}
