export interface Page<T> {
  items: T[];
  page: number;
  page_size: number;
  total: number;
  pages: number;
}

export type JobStatus = "queued" | "processing" | "completed" | "failed";
export type JobOrigin = "manual" | "automatic";
export type JobType = "process_charge" | "process_due_charges";

export interface Job {
  id: string;
  type: JobType;
  status: JobStatus;
  origin: JobOrigin | string;
  charge_id: string | null;
  terminal: boolean;
  duration_ms: number | null;
  payload: Record<string, unknown>;
  result: {
    evaluated: number;
    eligible: number;
    skipped: number;
    simulated: number;
    deduplicated: number;
    notification_failed: number;
  } | null;
  scheduled_for: string;
  attempts: number;
  max_attempts: number;
  started_at: string | null;
  finished_at: string | null;
  error: string | null;
  created_at: string;
  updated_at: string;
}

export interface JobAccepted {
  job_id: string;
  status: JobStatus;
  created: boolean;
}
