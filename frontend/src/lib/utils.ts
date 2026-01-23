import { type ClassValue, clsx } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function formatDuration(seconds: number | null | undefined): string {
  if (!seconds) return "0:00"
  const mins = Math.floor(seconds / 60)
  const secs = Math.floor(seconds % 60)
  return `${mins}:${secs.toString().padStart(2, "0")}`
}

export function formatDate(date: string | null | undefined): string {
  if (!date) return "N/A"
  return new Date(date).toLocaleDateString("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  })
}

export function getStatusColor(status: string): string {
  const colors: Record<string, string> = {
    pending: "bg-yellow-100 text-yellow-800",
    transcribing: "bg-blue-100 text-blue-800",
    transcribed: "bg-indigo-100 text-indigo-800",
    analyzing: "bg-purple-100 text-purple-800",
    analyzed: "bg-green-100 text-green-800",
    failed: "bg-red-100 text-red-800",
  }
  return colors[status?.toLowerCase()] || "bg-gray-100 text-gray-800"
}

export function getScoreColor(score: number | null | undefined): string {
  if (!score) return "text-gray-500"
  if (score >= 80) return "text-green-600"
  if (score >= 60) return "text-yellow-600"
  return "text-red-600"
}
