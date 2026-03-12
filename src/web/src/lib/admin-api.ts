/**
 * Admin API client for managing all models.
 */

import { requestJson } from "./api-client";

// ─────────────────────────────────────────────────────────────────
// Types
// ─────────────────────────────────────────────────────────────────

export interface AdminStats {
  total_users: number;
  active_users: number;
  admin_users: number;
  total_exams: number;
  total_questions: number;
  total_attempts: number;
  total_conversations: number;
}

export interface ModelField {
  name: string;
  type: string;
  nullable: boolean;
  primary_key: boolean;
  default?: string;
}

export interface ModelInfo {
  name: string;
  display_name: string;
  description: string;
  fields: ModelField[];
  count: number;
}

export interface PaginatedResponse<T = Record<string, unknown>> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface AdminUser {
  id: string;
  email: string;
  full_name: string;
  avatar_url?: string | null;
  role: string;
  is_active: boolean;
  is_verified: boolean;
  target_exam?: string | null;
  target_score?: number | null;
  timezone: string;
  created_at?: string | null;
  updated_at?: string | null;
  last_login_at?: string | null;
}

export interface CreateUserPayload {
  email: string;
  password: string;
  full_name: string;
  role?: string;
  is_active?: boolean;
  is_verified?: boolean;
}

export interface UpdateUserPayload {
  email?: string;
  full_name?: string;
  role?: string;
  is_active?: boolean;
  is_verified?: boolean;
  target_exam?: string | null;
  target_score?: number | null;
  timezone?: string;
}

// ─────────────────────────────────────────────────────────────────
// Dashboard & Stats
// ─────────────────────────────────────────────────────────────────

export function getAdminStats(): Promise<AdminStats> {
  return requestJson<AdminStats>("/admin/stats");
}

// ─────────────────────────────────────────────────────────────────
// Model Discovery
// ─────────────────────────────────────────────────────────────────

export function listModels(): Promise<ModelInfo[]> {
  return requestJson<ModelInfo[]>("/admin/models");
}

export function getModelInfo(modelName: string): Promise<ModelInfo> {
  return requestJson<ModelInfo>(`/admin/models/${modelName}`);
}

// ─────────────────────────────────────────────────────────────────
// Generic CRUD Operations
// ─────────────────────────────────────────────────────────────────

export interface ListRecordsParams {
  page?: number;
  page_size?: number;
  search?: string;
  order_by?: string;
  order_dir?: "asc" | "desc";
}

export function listRecords(
  modelName: string,
  params: ListRecordsParams = {}
): Promise<PaginatedResponse> {
  const searchParams = new URLSearchParams();
  if (params.page) searchParams.set("page", String(params.page));
  if (params.page_size) searchParams.set("page_size", String(params.page_size));
  if (params.search) searchParams.set("search", params.search);
  if (params.order_by) searchParams.set("order_by", params.order_by);
  if (params.order_dir) searchParams.set("order_dir", params.order_dir);

  const query = searchParams.toString();
  const url = `/admin/models/${modelName}/records${query ? `?${query}` : ""}`;
  return requestJson<PaginatedResponse>(url);
}

export function getRecord(
  modelName: string,
  recordId: string
): Promise<Record<string, unknown>> {
  return requestJson<Record<string, unknown>>(
    `/admin/models/${modelName}/records/${recordId}`
  );
}

export function updateRecord(
  modelName: string,
  recordId: string,
  data: Record<string, unknown>
): Promise<Record<string, unknown>> {
  return requestJson<Record<string, unknown>>(
    `/admin/models/${modelName}/records/${recordId}`,
    {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    }
  );
}

export function deleteRecord(
  modelName: string,
  recordId: string
): Promise<void> {
  return requestJson<void>(`/admin/models/${modelName}/records/${recordId}`, {
    method: "DELETE",
  });
}

// ─────────────────────────────────────────────────────────────────
// User Management
// ─────────────────────────────────────────────────────────────────

export interface ListUsersParams {
  page?: number;
  page_size?: number;
  search?: string;
  role?: string;
  is_active?: boolean;
}

export function listUsers(
  params: ListUsersParams = {}
): Promise<PaginatedResponse<AdminUser>> {
  const searchParams = new URLSearchParams();
  if (params.page) searchParams.set("page", String(params.page));
  if (params.page_size) searchParams.set("page_size", String(params.page_size));
  if (params.search) searchParams.set("search", params.search);
  if (params.role) searchParams.set("role", params.role);
  if (params.is_active !== undefined)
    searchParams.set("is_active", String(params.is_active));

  const query = searchParams.toString();
  const url = `/admin/users${query ? `?${query}` : ""}`;
  return requestJson<PaginatedResponse<AdminUser>>(url);
}

export function createUser(data: CreateUserPayload): Promise<AdminUser> {
  return requestJson<AdminUser>("/admin/users", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
}

export function updateUser(
  userId: string,
  data: UpdateUserPayload
): Promise<AdminUser> {
  return requestJson<AdminUser>(`/admin/users/${userId}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
}

export function deleteUser(userId: string): Promise<void> {
  return requestJson<void>(`/admin/users/${userId}`, {
    method: "DELETE",
  });
}

export function resetUserPassword(
  userId: string,
  password: string
): Promise<{ message: string }> {
  return requestJson<{ message: string }>(`/admin/users/${userId}/reset-password`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ password }),
  });
}
