import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleDateString("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

export function formatDateTime(dateStr: string): string {
  return new Date(dateStr).toLocaleString("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function truncate(str: string, maxLen: number): string {
  if (str.length <= maxLen) return str;
  return str.slice(0, maxLen - 3) + "...";
}

export function getStatusColor(status: string): string {
  const colors: Record<string, string> = {
    pending: "text-yellow-400",
    query_expansion: "text-blue-400",
    paper_retrieval: "text-cyan-400",
    formatting: "text-purple-400",
    survey_generation: "text-indigo-400",
    completed: "text-green-400",
    failed: "text-red-400",
  };
  return colors[status] ?? "text-dark-400";
}

export function getStatusLabel(status: string): string {
  const labels: Record<string, string> = {
    pending: "Pending",
    query_expansion: "Expanding Queries",
    paper_retrieval: "Retrieving Papers",
    formatting: "Formatting Citations",
    survey_generation: "Generating Survey",
    completed: "Completed",
    failed: "Failed",
  };
  return labels[status] ?? status;
}
