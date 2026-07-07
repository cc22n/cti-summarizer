import type { TimelinePoint } from "../types/dashboard";

export interface ChartPoint {
  date: string;
  critical: number;
  high: number;
  medium: number;
  low: number;
  info: number;
  total: number;
}

export function transformTimeline(points: TimelinePoint[]): ChartPoint[] {
  return points.map((p) => ({
    date: p.date.slice(5), // "YYYY-MM-DD" -> "MM-DD"
    critical: p.severity_breakdown?.critical ?? 0,
    high: p.severity_breakdown?.high ?? 0,
    medium: p.severity_breakdown?.medium ?? 0,
    low: p.severity_breakdown?.low ?? 0,
    info: p.severity_breakdown?.info ?? 0,
    total: p.count,
  }));
}

export interface PieSlice {
  name: string;
  value: number;
  fill: string;
}

export const SEVERITY_COLORS: Record<string, string> = {
  critical: "#ef4444",
  high: "#f97316",
  medium: "#eab308",
  low: "#22c55e",
  info: "#6b7280",
};

const SEVERITY_ORDER = ["critical", "high", "medium", "low", "info"];

export function transformSeverityPie(
  by_severity: Record<string, number>
): PieSlice[] {
  return SEVERITY_ORDER.filter((s) => (by_severity[s] ?? 0) > 0).map((s) => ({
    name: s,
    value: by_severity[s],
    fill: SEVERITY_COLORS[s],
  }));
}

export interface BarSlice {
  source: string;
  count: number;
}

export function transformSourceBar(
  by_source: Record<string, number>
): BarSlice[] {
  return Object.entries(by_source)
    .map(([source, count]) => ({ source, count }))
    .sort((a, b) => b.count - a.count);
}
