export interface DashboardOverview {
  total_alerts: number;
  alerts_today: number;
  alerts_this_week: number;
  critical_count: number;
  high_count: number;
  sources_active: number;
  sources_total: number;
  last_ingestion: string | null;
}

export interface TimelinePoint {
  date: string; // "YYYY-MM-DD" from Python date
  count: number;
  severity_breakdown: Record<string, number> | null;
}

export interface TimelineResponse {
  points: TimelinePoint[];
  period: string;
}
