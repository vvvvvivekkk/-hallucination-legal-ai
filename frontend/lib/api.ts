import axios, { type AxiosError, type AxiosInstance, type InternalAxiosRequestConfig } from "axios";
import type { AuthTokens, User } from "./types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export class ApiError extends Error {
  constructor(
    public status: number,
    public code: string,
    message: string,
    public details?: unknown,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

function parseError(error: AxiosError): ApiError {
  const data = error.response?.data as
    | { error?: { code?: string; message?: string; details?: unknown } }
    | undefined;
  return new ApiError(
    error.response?.status ?? 0,
    data?.error?.code ?? "network_error",
    data?.error?.message ?? error.message ?? "Network error",
    data?.error?.details,
  );
}

export function getCsrfToken(): string {
  const match = document.cookie.match(/(?:^|;\s*)csrf_token=([^;]+)/);
  return match ? decodeURIComponent(match[1]) : "";
}

let refreshing: Promise<string> | null = null;

async function refreshAccessToken(): Promise<string> {
  if (refreshing) return refreshing;
  refreshing = (async () => {
    const response = await axios.post(`${API_BASE}/api/auth/refresh`, {}, { withCredentials: true });
    const tokens = response.data as AuthTokens;
    if (typeof window !== "undefined") {
      sessionStorage.setItem("access_token", tokens.access_token);
    }
    return tokens.access_token;
  })();
  try {
    return await refreshing;
  } finally {
    refreshing = null;
  }
}

class ApiClient {
  private client: AxiosInstance;

  constructor() {
    this.client = axios.create({
      baseURL: API_BASE,
      timeout: 120_000,
      withCredentials: true,
      headers: {
        "Content-Type": "application/json",
      },
    });

    this.client.interceptors.request.use((config: InternalAxiosRequestConfig) => {
      if (typeof window !== "undefined") {
        const token = sessionStorage.getItem("access_token");
        if (token) {
          config.headers.set("Authorization", `Bearer ${token}`);
        }
      }
      if (typeof document !== "undefined") {
        const csrf = getCsrfToken();
        if (csrf) {
          config.headers.set("X-CSRF-Token", csrf);
        }
      }
      return config;
    });

    this.client.interceptors.response.use(
      (response) => response,
      async (error: AxiosError) => {
        const config = error.config as (InternalAxiosRequestConfig & { _retried?: boolean }) | undefined;
        const status = error.response?.status;
        const url = error.response?.config?.url ?? "";
        if (
          status === 401 &&
          config &&
          !config._retried &&
          !url.includes("/api/auth/login") &&
          !url.includes("/api/auth/refresh") &&
          !url.includes("/api/auth/register")
        ) {
          config._retried = true;
          try {
            const token = await refreshAccessToken();
            config.headers.set("Authorization", `Bearer ${token}`);
            return this.client(config);
          } catch {
            this.clearSession();
          }
        }
        throw parseError(error);
      },
    );
  }

  get instance(): AxiosInstance {
    return this.client;
  }

  async get<T>(url: string, params?: Record<string, unknown>): Promise<T> {
    const response = await this.client.get<T>(url, { params });
    return response.data;
  }

  async post<T>(url: string, body?: unknown): Promise<T> {
    const response = await this.client.post<T>(url, body);
    return response.data;
  }

  async patch<T>(url: string, body?: unknown): Promise<T> {
    const response = await this.client.patch<T>(url, body);
    return response.data;
  }

  async delete<T>(url: string): Promise<T> {
    const response = await this.client.delete<T>(url);
    return response.data;
  }

  setTokens(tokens: AuthTokens): void {
    if (typeof window !== "undefined") {
      sessionStorage.setItem("access_token", tokens.access_token);
    }
  }

  clearSession(): void {
    if (typeof window !== "undefined") {
      sessionStorage.removeItem("access_token");
      window.dispatchEvent(new CustomEvent("auth:logout"));
    }
  }
}

export const api = new ApiClient();

export interface MeResponse extends User {}

export async function fetchMe(): Promise<User> {
  return api.get<User>("/api/auth/me");
}
