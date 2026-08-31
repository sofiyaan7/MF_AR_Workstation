import { format, formatDistanceToNowStrict, isToday, isYesterday, parseISO } from "date-fns";

function toDate(value: string | Date | null | undefined): Date | null {
  if (!value) return null;
  const date = typeof value === "string" ? parseISO(value) : value;
  return Number.isNaN(date.getTime()) ? null : date;
}

/** "25 Aug 2026, 13:21" — the portal's canonical absolute timestamp. */
export function formatDateTime(value: string | Date | null | undefined): string {
  const date = toDate(value);
  return date ? format(date, "d MMM yyyy, HH:mm") : "—";
}

export function formatDate(value: string | Date | null | undefined): string {
  const date = toDate(value);
  return date ? format(date, "d MMM yyyy") : "—";
}

export function formatTime(value: string | Date | null | undefined): string {
  const date = toDate(value);
  return date ? format(date, "HH:mm:ss") : "—";
}

/** "15 minutes ago", "yesterday", "3 days ago". */
export function formatRelative(value: string | Date | null | undefined): string {
  const date = toDate(value);
  if (!date) return "Never";
  const seconds = (Date.now() - date.getTime()) / 1000;
  if (seconds < 60) return "just now";
  if (isToday(date)) return `${formatDistanceToNowStrict(date)} ago`;
  if (isYesterday(date)) return "yesterday";
  return `${formatDistanceToNowStrict(date)} ago`;
}

/** Section heading used by the activity timelines. */
export function dayLabel(value: string | Date): string {
  const date = toDate(value);
  if (!date) return "Unknown";
  if (isToday(date)) return "Today";
  if (isYesterday(date)) return "Yesterday";
  return format(date, "EEEE, d MMMM yyyy");
}

export function formatNumber(value: number | null | undefined): string {
  if (value === null || value === undefined) return "—";
  return new Intl.NumberFormat("en-GB").format(value);
}

/** "PROJECT_OPENED" -> "Project opened" */
export function humaniseEvent(eventType: string): string {
  const words = eventType.toLowerCase().split("_");
  return words.map((w, i) => (i === 0 ? w[0].toUpperCase() + w.slice(1) : w)).join(" ");
}

export function chartDateLabel(value: string): string {
  const date = toDate(value);
  return date ? format(date, "d MMM") : value;
}
