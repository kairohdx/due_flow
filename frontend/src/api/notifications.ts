import { apiFetch } from "./client";
import type {
  NotificationAttempt,
  NotificationProvider,
  RecoveryAssessment,
  NotificationSubmissionStatus,
  NotificationType,
  Page,
  JobAccepted,
} from "./types";

export interface NotificationFilters {
  page: number;
  pageSize: number;
  status?: NotificationSubmissionStatus;
  provider?: NotificationProvider;
  type?: NotificationType;
  processedFrom?: string;
  processedTo?: string;
}

function queryString(params: Record<string, string | number | undefined>) {
  const query = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== "") query.set(key, String(value));
  });
  return query.toString();
}

export function getNotifications(
  filters: NotificationFilters,
): Promise<Page<NotificationAttempt>> {
  const query = queryString({
    page: filters.page,
    page_size: filters.pageSize,
    status: filters.status,
    provider: filters.provider,
    notification_type: filters.type,
    processed_from: filters.processedFrom,
    processed_to: filters.processedTo,
  });
  return apiFetch(`/notifications?${query}`);
}

export function getNotification(
  notificationId: string,
): Promise<NotificationAttempt> {
  return apiFetch(`/notifications/${notificationId}`);
}

export function getChargeNotifications(
  chargeId: string,
): Promise<Page<NotificationAttempt>> {
  return apiFetch(`/charges/${chargeId}/notifications?page=1&page_size=5`);
}

export function getNotificationRecovery(
  notificationId: string,
): Promise<RecoveryAssessment> {
  return apiFetch(`/notifications/${notificationId}/recovery`);
}

export function retryNotification(
  notificationId: string,
): Promise<JobAccepted> {
  return apiFetch(`/notifications/${notificationId}/retry`, {
    method: "POST",
  });
}

export function retryNotificationWithTemplate(
  notificationId: string,
): Promise<JobAccepted> {
  return apiFetch(`/notifications/${notificationId}/retry-template`, {
    method: "POST",
  });
}

export function getNotificationAttempts(
  notificationId: string,
): Promise<NotificationAttempt[]> {
  return apiFetch(`/notifications/${notificationId}/attempts`);
}
