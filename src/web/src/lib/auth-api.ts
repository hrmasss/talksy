import {
  clearStoredTokens,
  requestJson,
  setStoredTokens,
} from "./api-client";

const STORED_USER_KEY = "talksy.user";

export interface User {
  id: string;
  email: string;
  full_name: string;
  avatar_url?: string | null;
  is_active: boolean;
  is_verified: boolean;
  target_exam?: string | null;
  target_score?: number | null;
  timezone: string;
  preferences: Record<string, unknown>;
  created_at?: string | null;
  updated_at?: string | null;
  last_login_at?: string | null;
  target_band_score?: number | null;
  exam_date?: string | null;
  preferred_daily_practice_time?: number | null;
  current_estimated_band?: number | null;
  skill_profile: Record<string, unknown>;
  section_scores: Record<string, number | null>;
  onboarding_completed: boolean;
}

export interface AuthResponse {
  user: User;
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

export interface LoginPayload {
  email: string;
  password: string;
}

export interface SignupPayload {
  email: string;
  password: string;
  full_name: string;
  target_exam?: string;
  target_score?: number;
  timezone?: string;
}

export function getStoredUser(): User | null {
  const raw = localStorage.getItem(STORED_USER_KEY);
  if (!raw) {
    return null;
  }

  try {
    return JSON.parse(raw) as User;
  } catch {
    localStorage.removeItem(STORED_USER_KEY);
    return null;
  }
}

export function setStoredUser(user: User | null): void {
  if (!user) {
    localStorage.removeItem(STORED_USER_KEY);
    return;
  }

  localStorage.setItem(STORED_USER_KEY, JSON.stringify(user));
}

export function persistAuthSession(response: AuthResponse): void {
  setStoredTokens(response.access_token, response.refresh_token);
  setStoredUser(response.user);
}

export function clearAuthSession(): void {
  clearStoredTokens();
  setStoredUser(null);
}

export function loginRequest(payload: LoginPayload): Promise<AuthResponse> {
  return requestJson<AuthResponse>("/users/login", {
    method: "POST",
    auth: false,
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });
}

export function signupRequest(payload: SignupPayload): Promise<AuthResponse> {
  return requestJson<AuthResponse>("/users/register", {
    method: "POST",
    auth: false,
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });
}

export function getCurrentUser(): Promise<User> {
  return requestJson<User>("/users/me");
}
