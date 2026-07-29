export interface Page<T> {
  items: T[];
  page: number;
  page_size: number;
  total: number;
  pages: number;
}

export type JobStatus = "queued" | "processing" | "completed" | "failed";
export type JobOrigin = "manual" | "automatic";
export type JobType =
  | "process_charge"
  | "process_due_charges"
  | "retry_notification";

export interface JobDecision {
  decision: "notify" | "skip";
  notification_type: string | null;
  template_key: string | null;
  reason: string;
  eligible: boolean;
  recommended_action: string;
  policy_name: string;
  metadata: Record<string, unknown>;
}

export interface JobTraceEntry {
  policy_name: string;
  matched: boolean;
  outcome: string;
  reason: string | null;
  duration_ms: number | null;
}

export interface JobTrace {
  trace_id: string;
  execution_id: string;
  pipeline: string;
  strategy: string;
  status: string;
  duration_ms: number;
  selected_policy: string;
  evaluated: JobTraceEntry[];
  not_evaluated: string[];
}

export interface JobNotification {
  attempt_id: string;
  submission_status: string;
  provider_message_id: string | null;
  idempotency_key: string;
  deduplicated: boolean;
  error: string | null;
}

export interface JobEvaluation {
  charge_id: string;
  decision: JobDecision;
  trace: JobTrace;
  notification: JobNotification | null;
}

export interface JobResult {
  reference_date?: string;
  evaluated: number;
  eligible: number;
  skipped: number;
  simulated: number;
  deduplicated: number;
  notification_failed: number;
  evaluations?: JobEvaluation[];
  retried?: boolean;
  cancelled?: boolean;
  source_attempt_id?: string;
  attempt_id?: string;
  attempt_number?: number;
  submission_status?: string;
  recovery?: Record<string, unknown>;
}

export interface Job {
  id: string;
  type: JobType;
  status: JobStatus;
  origin: JobOrigin | string;
  charge_id: string | null;
  terminal: boolean;
  duration_ms: number | null;
  payload: Record<string, unknown>;
  result: JobResult | null;
  scheduled_for: string;
  attempts: number;
  max_attempts: number;
  locked_at?: string | null;
  locked_by?: string | null;
  started_at: string | null;
  finished_at: string | null;
  error: string | null;
  retain_deduplication_key: boolean;
  created_at: string;
  updated_at: string;
}

export interface JobAccepted {
  job_id: string;
  status: JobStatus;
  created: boolean;
}

export interface Customer {
  id: string;
  name: string;
  phone: string;
  active: boolean;
  created_at: string;
  updated_at: string;
}

export interface CustomerPayload {
  name: string;
  phone: string;
  active: boolean;
}

export type ChargeStatus = "pending" | "paid" | "canceled";

export interface Charge {
  id: string;
  customer_id: string;
  description: string;
  amount: string;
  due_date: string;
  status: ChargeStatus;
  reminder_days_before: number;
  created_at: string;
  updated_at: string;
}

export interface ChargePayload {
  customer_id: string;
  description: string;
  amount: string;
  due_date: string;
  reminder_days_before: number;
}

export type NotificationSubmissionStatus =
  | "pending"
  | "succeeded"
  | "failed"
  | "unknown"
  | "simulated";
export type NotificationDeliveryStatus =
  | "not_started"
  | "pending"
  | "sent"
  | "delivered"
  | "read"
  | "failed";
export type NotificationProvider = "fake" | "meta";
export type NotificationType = "upcoming" | "due_today" | "overdue";
export type MetaErrorAction = "retry" | "fix" | "template" | "review";

export interface MetaErrorInfo {
  code: number | null;
  title: string;
  message: string;
  action: string;
  action_type: MetaErrorAction;
  known: boolean;
  technical_title: string | null;
  technical_details: string | null;
}

export interface NotificationAttempt {
  id: string;
  charge_id: string;
  processing_job_id: string | null;
  root_attempt_id?: string | null;
  retry_of_attempt_id?: string | null;
  retry_requested_by_user_id?: string | null;
  attempt_number?: number;
  notification_type: NotificationType;
  provider: NotificationProvider;
  destination: string;
  message: string;
  message_format?: "text" | "template";
  template_info?: {
    name: string;
    language: string;
    parameters: string[];
  } | null;
  submission_status: NotificationSubmissionStatus;
  provider_message_id: string | null;
  submission_error_code: number | null;
  submission_error_title: string | null;
  submission_error_details: string | null;
  submission_error_info: MetaErrorInfo | null;
  idempotency_key: string;
  policy_name: string;
  decision_reason: string;
  trace: JobTrace | null;
  provider_response: Record<string, unknown> | null;
  delivery_status: NotificationDeliveryStatus;
  delivery_event_at?: string | null;
  delivery_updated_at?: string | null;
  delivery_error_code?: number | null;
  delivery_error_title?: string | null;
  delivery_error_details?: string | null;
  delivery_error_info: MetaErrorInfo | null;
  delivery_response?: Record<string, unknown> | null;
  processed_at: string;
}

export type RecoveryAction =
  | "retry"
  | "template"
  | "fix"
  | "review"
  | "block";

export interface RecoveryAssessment {
  attempt_id: string;
  eligible: boolean;
  action: RecoveryAction;
  reason: string;
  policy_name: string;
  trace: JobTrace;
  template_eligible?: boolean;
}
