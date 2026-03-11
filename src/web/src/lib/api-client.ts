const API_BASE_URL =
  ((import.meta.env.VITE_API_BASE_URL as string | undefined) ?? "/api/v1").replace(/\/$/, "");

const ACCESS_TOKEN_KEY = "talksy.access_token";
const REFRESH_TOKEN_KEY = "talksy.refresh_token";

export interface ValidationIssue {
  loc?: Array<string | number>;
  msg?: string;
  type?: string;
}

export class ApiError extends Error {
  status: number;
  detail?: unknown;
  errors?: ValidationIssue[];

  constructor(message: string, status: number, detail?: unknown, errors?: ValidationIssue[]) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.detail = detail;
    this.errors = errors;
  }
}

let refreshPromise: Promise<boolean> | null = null;

export function getApiUrl(path: string): string {
  if (/^https?:\/\//i.test(path)) {
    return path;
  }

  const normalizedPath = path.startsWith("/") ? path : `/${path}`;
  return `${API_BASE_URL}${normalizedPath}`;
}

export function getStoredAccessToken(): string | null {
  return localStorage.getItem(ACCESS_TOKEN_KEY);
}

export function getStoredRefreshToken(): string | null {
  return localStorage.getItem(REFRESH_TOKEN_KEY);
}

export function setStoredTokens(accessToken: string, refreshToken: string): void {
  localStorage.setItem(ACCESS_TOKEN_KEY, accessToken);
  localStorage.setItem(REFRESH_TOKEN_KEY, refreshToken);
}

export function clearStoredTokens(): void {
  localStorage.removeItem(ACCESS_TOKEN_KEY);
  localStorage.removeItem(REFRESH_TOKEN_KEY);
}

function isPlainObject(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

async function parseError(response: Response): Promise<ApiError> {
  let payload: unknown;

  try {
    payload = await response.json();
  } catch {
    payload = await response.text().catch(() => "");
  }

  if (isPlainObject(payload)) {
    const detail = payload.detail;
    const errors = Array.isArray(payload.errors) ? (payload.errors as ValidationIssue[]) : undefined;
    const message =
      typeof detail === "string" && detail.trim()
        ? detail
        : response.statusText || "Request failed";

    return new ApiError(message, response.status, detail, errors);
  }

  const fallbackMessage =
    typeof payload === "string" && payload.trim()
      ? payload
      : response.statusText || "Request failed";

  return new ApiError(fallbackMessage, response.status, payload);
}

async function refreshAccessToken(): Promise<boolean> {
  const refreshToken = getStoredRefreshToken();
  if (!refreshToken) {
    clearStoredTokens();
    return false;
  }

  if (!refreshPromise) {
    refreshPromise = (async () => {
      try {
        const response = await fetch(getApiUrl("/users/refresh"), {
          method: "POST",
          headers: {
            Authorization: `Bearer ${refreshToken}`,
          },
        });

        if (!response.ok) {
          clearStoredTokens();
          return false;
        }

        const payload = (await response.json()) as {
          access_token: string;
          refresh_token: string;
        };
        setStoredTokens(payload.access_token, payload.refresh_token);
        return true;
      } catch {
        clearStoredTokens();
        return false;
      } finally {
        refreshPromise = null;
      }
    })();
  }

  return refreshPromise;
}

interface RequestOptions extends RequestInit {
  auth?: boolean;
  retryOnAuthFailure?: boolean;
}

export async function apiFetch(path: string, options: RequestOptions = {}): Promise<Response> {
  const {
    auth = true,
    retryOnAuthFailure = true,
    headers,
    body,
    ...rest
  } = options;

  const resolvedHeaders = new Headers(headers);
  const accessToken = auth ? getStoredAccessToken() : null;
  if (accessToken) {
    resolvedHeaders.set("Authorization", `Bearer ${accessToken}`);
  }

  const response = await fetch(getApiUrl(path), {
    ...rest,
    headers: resolvedHeaders,
    body,
  });

  if (response.status === 401 && auth && retryOnAuthFailure) {
    const refreshed = await refreshAccessToken();
    if (refreshed) {
      return apiFetch(path, { ...options, retryOnAuthFailure: false });
    }
  }

  return response;
}

export async function requestJson<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const response = await apiFetch(path, options);
  if (!response.ok) {
    throw await parseError(response);
  }

  return (await response.json()) as T;
}

export async function requestArrayBuffer(path: string, options: RequestOptions = {}): Promise<ArrayBuffer> {
  const response = await apiFetch(path, options);
  if (!response.ok) {
    throw await parseError(response);
  }

  return response.arrayBuffer();
}
