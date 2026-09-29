import type {
  Action,
  Crop,
  DecisionResponse,
  DecisionSummary,
  FeedbackEntry,
  FeedbackIn,
  ForecastResponse,
  NotifyMessage,
  NotifyResult,
  Panchayat,
  ReviewItem,
  TwinResponse,
} from "./types";

const API_BASE = import.meta.env.VITE_API_BASE ?? "/api";

export interface HealthResponse {
  status: string;
  service: string;
  version: string;
  database: { status: string; dialect: string };
}

/** Requests slower than this fail with a readable error instead of spinning forever. */
const REQUEST_TIMEOUT_MS = 15_000;

/** `status` is the HTTP status, or 0 when the server could not be reached at all. */
export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
  }

  /** True for failures worth retrying (network, timeout, 5xx), as opposed to 4xx. */
  get retryable(): boolean {
    return this.status === 0 || this.status >= 500;
  }
}

export const isAbortError = (e: unknown) => e instanceof DOMException && e.name === "AbortError";

async function get<T>(path: string, signal?: AbortSignal): Promise<T> {
  return request<T>(path, { signal });
}

async function post<T>(path: string, body: unknown): Promise<T> {
  return request<T>(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

async function request<T>(path: string, init: RequestInit): Promise<T> {
  // Combine the caller's signal (component unmount) with a timeout.
  const controller = new AbortController();
  let timedOut = false;
  const timer = window.setTimeout(() => {
    timedOut = true;
    controller.abort();
  }, REQUEST_TIMEOUT_MS);
  const outer = init.signal;
  const onOuterAbort = () => controller.abort();
  if (outer?.aborted) controller.abort();
  outer?.addEventListener("abort", onOuterAbort);

  let res: Response;
  try {
    res = await fetch(`${API_BASE}${path}`, { ...init, signal: controller.signal });
  } catch (e) {
    if (timedOut) throw new ApiError(0, "The server took too long to respond. Please try again.");
    if (isAbortError(e)) throw e; // cancelled by the caller; not an error to show
    throw new ApiError(0, "Can’t reach the server. Check your internet connection and try again.");
  } finally {
    window.clearTimeout(timer);
    outer?.removeEventListener("abort", onOuterAbort);
  }

  if (!res.ok) {
    let message =
      res.status >= 502 && res.status <= 504
        ? // Gateway errors: backend down, redeploying, or a free-tier instance waking up.
          "The server is unavailable right now (it may be starting up). Please try again in a minute."
        : res.status >= 500
          ? `The server had a problem (HTTP ${res.status}). Please try again shortly.`
          : `Request failed (HTTP ${res.status}).`;
    try {
      const body = await res.json();
      if (typeof body.detail === "string") message = body.detail;
      // FastAPI validation errors: [{ loc, msg, ... }]
      else if (Array.isArray(body.detail) && body.detail[0]?.msg) message = body.detail[0].msg;
    } catch {
      // Non-JSON error body (e.g. a proxy error page); keep the generic message.
    }
    throw new ApiError(res.status, message);
  }
  return res.json();
}

const withCrop = (crop?: Crop) => (crop ? `?crop=${crop}` : "");

export const getHealth = (signal?: AbortSignal) => get<HealthResponse>("/health", signal);
export const getDecisionSummaries = (signal?: AbortSignal) => get<DecisionSummary[]>("/decisions", signal);
export const getForecast = (id: string, signal?: AbortSignal) => get<ForecastResponse>(`/forecast/${id}`, signal);
export const getTwin = (id: string, crop?: Crop, signal?: AbortSignal) =>
  get<TwinResponse>(`/twin/${id}${withCrop(crop)}`, signal);
export const getDecision = (id: string, crop?: Crop, signal?: AbortSignal) =>
  get<DecisionResponse>(`/decision/${id}${withCrop(crop)}`, signal);

export const getReviewQueue = (signal?: AbortSignal) => get<ReviewItem[]>("/review-queue", signal);
export const approveReview = (id: string, note?: string) =>
  post<ReviewItem>(`/review-queue/${encodeURIComponent(id)}/approve`, { note: note || null });
export const overrideReview = (id: string, action: Action, note: string) =>
  post<ReviewItem>(`/review-queue/${encodeURIComponent(id)}/override`, { action, note });

export const getNotifyPreview = (id: string, signal?: AbortSignal) => get<NotifyMessage>(`/notify/${id}`, signal);
/** "Sends" the WhatsApp message. The backend only logs it for now. */
export const sendNotify = (id: string) => post<NotifyResult>(`/notify/${id}`, {});

export const getPanchayats = (signal?: AbortSignal) => get<Panchayat[]>("/panchayats", signal);
export const getFeedback = (params: { limit?: number; panchayatId?: string }, signal?: AbortSignal) => {
  const q = new URLSearchParams({ limit: String(params.limit ?? 50) });
  if (params.panchayatId) q.set("panchayat_id", params.panchayatId);
  return get<FeedbackEntry[]>(`/feedback?${q}`, signal);
};
export const submitFeedback = (body: FeedbackIn) => post<FeedbackEntry>("/feedback", body);
