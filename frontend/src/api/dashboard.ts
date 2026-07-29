import { apiFetch } from "./client";
import type { Job, JobAccepted, Page } from "./types";

export interface DashboardSummary {
  generated_at: string;
  window_started_at: string;
  customers_total: number;
  charges_pending: number;
  charges_overdue: number;
  charges_due_today: number;
  charges_due_next_7_days: number;
  charges_evaluated_last_24h: number;
  notifications_processed_last_24h: number;
  notification_failures_last_24h: number;
  jobs_queued: number;
  jobs_processing: number;
  jobs_completed_last_24h: number;
  job_retries_last_24h: number;
  jobs_failed_last_24h: number;
}

export interface AutomationState {
  enabled: boolean;
  interval_seconds: number;
  last_enqueued_at: string | null;
  next_run_at: string | null;
  updated_at: string;
}

export function getDashboardSummary(): Promise<DashboardSummary> {
  return apiFetch("/dashboard/summary");
}

export function getAutomation(): Promise<AutomationState> {
  return apiFetch("/automation");
}

export function enableAutomation(): Promise<AutomationState> {
  return apiFetch("/automation/enable", {
    method: "POST",
    body: "{}",
  });
}

export function configureAutomation(
  intervalSeconds: number,
): Promise<AutomationState> {
  return apiFetch("/automation", {
    method: "PUT",
    body: JSON.stringify({ interval_seconds: intervalSeconds }),
  });
}

export function disableAutomation(): Promise<AutomationState> {
  return apiFetch("/automation/disable", {
    method: "POST",
  });
}

export function enqueueProcessing(): Promise<JobAccepted> {
  return apiFetch("/processing/run", {
    method: "POST",
    body: "{}",
  });
}

export function getRecentJobs(): Promise<Page<Job>> {
  return apiFetch("/processing/jobs?page=1&page_size=5");
}

export function getJob(jobId: string): Promise<Job> {
  return apiFetch(`/processing/jobs/${jobId}`);
}
