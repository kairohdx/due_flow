import { apiFetch } from "./client";
import type {
  Job,
  JobOrigin,
  JobStatus,
  JobType,
  Page,
} from "./types";

export interface ExecutionFilters {
  page: number;
  pageSize: number;
  status?: JobStatus;
  origin?: JobOrigin;
  type?: JobType;
  createdFrom?: string;
  createdTo?: string;
}

function queryString(params: Record<string, string | number | undefined>) {
  const query = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== "") query.set(key, String(value));
  });
  return query.toString();
}

export function getExecutions(filters: ExecutionFilters): Promise<Page<Job>> {
  const query = queryString({
    page: filters.page,
    page_size: filters.pageSize,
    status: filters.status,
    origin: filters.origin,
    type: filters.type,
    created_from: filters.createdFrom,
    created_to: filters.createdTo,
  });
  return apiFetch(`/processing/jobs?${query}`);
}

export function getExecution(executionId: string): Promise<Job> {
  return apiFetch(`/processing/jobs/${executionId}`);
}
