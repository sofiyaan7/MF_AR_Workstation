/**
 * Axios instance for the portal API.
 *
 * Authentication uses HttpOnly cookies, so no token is ever held in JavaScript.
 * The only thing read from `document.cookie` is the CSRF token, which the
 * backend requires to be echoed back in a header on every state change.
 */
import axios, { AxiosError, type AxiosRequestConfig } from "axios";

import { readCookie } from "@/lib/utils";

const CSRF_COOKIE = "mfar_csrf";
const CSRF_HEADER = "X-CSRF-Token";

export const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL ?? "/api",
  withCredentials: true,
  headers: { "Content-Type": "application/json" },
});

api.interceptors.request.use((config) => {
  const method = (config.method ?? "get").toUpperCase();
  if (!["GET", "HEAD", "OPTIONS"].includes(method)) {
    const token = readCookie(CSRF_COOKIE);
    if (token) config.headers.set(CSRF_HEADER, token);
  }
  return config;
});

export interface ApiErrorBody {
  error: string;
  message: string;
  details?: string[];
}

export class ApiError extends Error {
  status: number;
  code: string;
  details: string[];

  constructor(status: number, body: ApiErrorBody) {
    super(body.message);
    this.name = "ApiError";
    this.status = status;
    this.code = body.error;
    this.details = body.details ?? [];
  }
}

/** True when the caller must sign in again. */
export function isAuthError(error: unknown): boolean {
  return error instanceof ApiError && error.status === 401;
}

const AUTH_FREE_PATHS = ["/auth/login", "/auth/refresh", "/auth/password-policy", "/auth/forgot-password"];

let refreshInFlight: Promise<void> | null = null;
let onSessionExpired: (() => void) | null = null;

export function setSessionExpiredHandler(handler: () => void) {
  onSessionExpired = handler;
}

async function refreshSession(): Promise<void> {
  // Collapse concurrent 401s into a single refresh request.
  if (!refreshInFlight) {
    refreshInFlight = api
      .post("/auth/refresh")
      .then(() => undefined)
      .finally(() => {
        refreshInFlight = null;
      });
  }
  return refreshInFlight;
}

api.interceptors.response.use(
  (response) => response,
  async (error: AxiosError<ApiErrorBody>) => {
    const config = error.config as (AxiosRequestConfig & { _retried?: boolean }) | undefined;
    const status = error.response?.status ?? 0;
    const url = config?.url ?? "";
    const isAuthFree = AUTH_FREE_PATHS.some((path) => url.startsWith(path));

    // A 401 on a normal call usually means the short-lived access token
    // expired; try one silent refresh before giving up on the session.
    if (status === 401 && config && !config._retried && !isAuthFree) {
      config._retried = true;
      try {
        await refreshSession();
        return await api.request(config);
      } catch {
        onSessionExpired?.();
      }
    }

    const body: ApiErrorBody = error.response?.data ?? {
      error: status === 0 ? "network_error" : "request_failed",
      message:
        status === 0
          ? "Cannot reach the server. Check your connection and try again."
          : "Something went wrong. Please try again.",
      details: [],
    };
    return Promise.reject(new ApiError(status, body));
  },
);

export async function unwrap<T>(promise: Promise<{ data: T }>): Promise<T> {
  return (await promise).data;
}
