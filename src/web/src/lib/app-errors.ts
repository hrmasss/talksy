import { ApiError, type ValidationIssue } from "./api-client";

function formatValidationIssue(issue: ValidationIssue): string | null {
  if (!issue.msg) {
    return null;
  }

  if (issue.loc && issue.loc.length > 0) {
    const field = issue.loc.join(".");
    return `${field}: ${issue.msg}`;
  }

  return issue.msg;
}

export function getUserFacingErrorMessage(error: unknown, fallbackMessage: string): string {
  if (error instanceof ApiError) {
    const validationMessage = error.errors?.map(formatValidationIssue).find(Boolean);
    if (validationMessage) {
      return validationMessage;
    }

    if (typeof error.detail === "string" && error.detail.trim()) {
      return error.detail;
    }

    if (error.message.trim()) {
      return error.message;
    }
  }

  if (error instanceof Error && error.message.trim()) {
    return error.message;
  }

  if (typeof error === "string" && error.trim()) {
    return error;
  }

  return fallbackMessage;
}
