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

export interface AdminDocumentUploadResponse {
  message: string;
  collection_name?: string;
}

export interface AdminDocumentSearchResult {
  content: string;
  metadata?: Record<string, unknown>;
}

export type KnowledgeBaseCategory = "exam" | "daily_study" | "roadmap" | "custom";

export type KnowledgeBaseExamSection =
  | "speaking"
  | "writing"
  | "reading"
  | "listening";

export interface KnowledgeBaseCategoryOption {
  value: KnowledgeBaseCategory;
  label: string;
  requiresExamSection?: boolean;
}

export interface KnowledgeBaseExamSectionOption {
  value: KnowledgeBaseExamSection;
  label: string;
}

export const KNOWLEDGE_BASE_CATEGORY_OPTIONS: KnowledgeBaseCategoryOption[] = [
  { value: "exam", label: "Exam", requiresExamSection: true },
  { value: "daily_study", label: "Daily Study" },
  { value: "roadmap", label: "Roadmap" },
  { value: "custom", label: "Custom Collection" },
];

export const KNOWLEDGE_BASE_EXAM_SECTION_OPTIONS: KnowledgeBaseExamSectionOption[] = [
  { value: "speaking", label: "Speaking" },
  { value: "writing", label: "Writing" },
  { value: "reading", label: "Reading" },
  { value: "listening", label: "Listening" },
];

function slugifyCollectionPart(value: string): string {
  return value.trim().toLowerCase().replace(/[^a-z0-9]+/g, "_").replace(/^_+|_+$/g, "");
}

export function buildKnowledgeBaseCollectionName(params: {
  category: KnowledgeBaseCategory;
  examSection?: KnowledgeBaseExamSection;
  customCollectionName?: string;
}): string {
  const { category, examSection, customCollectionName } = params;

  if (category === "custom") {
    return slugifyCollectionPart(customCollectionName || "") || "knowledge_base";
  }

  if (category === "exam") {
    const section = examSection || "speaking";
    return `kb_exam_${slugifyCollectionPart(section)}`;
  }

  return `kb_${slugifyCollectionPart(category)}`;
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

export function uploadAdminDocument(
  params: {
    collectionName?: string;
    category?: KnowledgeBaseCategory;
    examSection?: KnowledgeBaseExamSection;
    customCollectionName?: string;
  },
  file: File
): Promise<AdminDocumentUploadResponse> {
  const form = new FormData();
  form.append("data", file);

  const queryParams = new URLSearchParams();
  if (params.collectionName) queryParams.set("collection_name", params.collectionName);
  if (params.category) queryParams.set("category", params.category);
  if (params.examSection) queryParams.set("exam_section", params.examSection);
  if (params.customCollectionName)
    queryParams.set("custom_collection_name", params.customCollectionName);

  const query = queryParams.toString();
  return requestJson<AdminDocumentUploadResponse>(`/admin/documents/upload?${query}`, {
    method: "POST",
    body: form,
  });
}

export function searchAdminDocuments(
  params: {
    collectionName?: string;
    category?: KnowledgeBaseCategory;
    examSection?: KnowledgeBaseExamSection;
    customCollectionName?: string;
  },
  query: string,
  limit = 5
): Promise<AdminDocumentSearchResult[]> {
  const searchParams = new URLSearchParams({
    query,
    limit: String(limit),
  });
  if (params.collectionName) searchParams.set("collection_name", params.collectionName);
  if (params.category) searchParams.set("category", params.category);
  if (params.examSection) searchParams.set("exam_section", params.examSection);
  if (params.customCollectionName)
    searchParams.set("custom_collection_name", params.customCollectionName);

  const search = searchParams.toString();

  return requestJson<AdminDocumentSearchResult[]>(`/admin/documents/search?${search}`);
}
