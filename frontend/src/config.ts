function positiveNumber(value: string | undefined, fallback: number): number {
  const parsed = Number(value);
  return Number.isFinite(parsed) && parsed > 0 ? parsed : fallback;
}

export const API_BASE_URL = (
  import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000"
).replace(/\/$/, "");

export const REQUEST_TIMEOUT_MS = positiveNumber(
  import.meta.env.VITE_REQUEST_TIMEOUT_MS,
  10_000,
);

export const QUERY_RETRY_COUNT = 1;
