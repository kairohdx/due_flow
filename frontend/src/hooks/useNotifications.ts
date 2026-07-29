import { useQuery } from "@tanstack/react-query";
import {
  getNotification,
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

export function useNotification(notificationId: string) {
  return useQuery({
    queryKey: ["notification", notificationId],
    queryFn: () => getNotification(notificationId),
    enabled: Boolean(notificationId),
  });
}
