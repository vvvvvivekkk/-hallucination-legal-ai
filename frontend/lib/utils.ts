import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatBytes(bytes: number): string {
  if (bytes === 0) return "0 B";
  const k = 1024;
  const sizes = ["B", "KB", "MB", "GB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(1))} ${sizes[i]}`;
}

export function formatDate(value: string | null | undefined): string {
  if (!value) return "";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function timeAgo(value: string | null | undefined): string {
  if (!value) return "";
  const then = new Date(value).getTime();
  if (Number.isNaN(then)) return "";
  const seconds = Math.floor((Date.now() - then) / 1000);
  if (seconds < 60) return "just now";
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  if (days < 30) return `${days}d ago`;
  return formatDate(value);
}

export function truncate(text: string, length = 160): string {
  if (!text) return "";
  return text.length > length ? `${text.slice(0, length)}...` : text;
}

export function extractError(error: unknown): string {
  if (error && typeof error === "object") {
    const anyError = error as Record<string, unknown>;
    const err = anyError.response as Record<string, unknown> | undefined;
    const data = (err?.data ?? anyError.data) as Record<string, unknown> | undefined;
    const errorBody = data?.error as Record<string, unknown> | undefined;
    if (errorBody && typeof errorBody.message === "string") {
      return errorBody.message;
    }
    if (typeof anyError.message === "string") return anyError.message;
  }
  if (typeof error === "string") return error;
  return "Something went wrong. Please try again.";
}

export function getConfidenceColor(score: number): string {
  if (score >= 0.8) return "text-emerald-600 dark:text-emerald-400";
  if (score >= 0.6) return "text-amber-600 dark:text-amber-400";
  return "text-red-600 dark:text-red-400";
}

export function getVerdictColor(verdict: string): string {
  switch (verdict) {
    case "low":
      return "text-emerald-600 dark:text-emerald-400";
    case "medium":
      return "text-amber-600 dark:text-amber-400";
    case "high":
      return "text-red-600 dark:text-red-400";
    default:
      return "text-muted-foreground";
  }
}
