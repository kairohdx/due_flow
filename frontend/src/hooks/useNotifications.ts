import { useQuery } from "@tanstack/react-query";
import {
  getNotification,
  getChargeNotifications,
  getNotifications,
  type NotificationFilters,
} from "../api/notifications";

export function useNotifications(filters: NotificationFilters) {
  return useQuery({
    queryKey: ["notifications", filters],
    queryFn: () => getNotifications(filters),
    placeholderData: (previous) => previous,
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
  });
}
