export type Severity = "critical" | "high" | "medium" | "low" | "info";

export interface CategoryBrief {
  id: number;
  name: string;
}

export interface Alert {
  id: number;
  raw_alert_id: number;
  title: string;
  description: string | null;
  severity: Severity;
  cvss_score: string | null; // Decimal serializes as string in JSON
  source_name: string;
  affected_products: Record<string, unknown> | null;
  attack_vectors: Record<string, unknown> | null;
  mitre_techniques: Record<string, unknown> | null;
  iocs: Record<string, unknown> | null;
  published_date: string | null;
  normalized_at: string;
  categories: CategoryBrief[];
  notes: string | null;
  is_acknowledged: boolean;
  acknowledged_at: string | null;
}

export type AlertSortField =
  | "normalized_at"
  | "published_date"
  | "severity"
  | "cvss_score"
  | "source_name"
  | "title";

export interface AlertListResponse {
  items: Alert[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

export interface AlertStatsResponse {
  total_alerts: number;
  by_severity: Record<string, number>;
  by_source: Record<string, number>;
  last_24h: number;
  last_7d: number;
}

export interface AlertFilters {
  page: number;
  page_size: number;
  severity?: string;
  source?: string;
  search?: string;
  category?: string;
  date_from?: string;
  date_to?: string;
  sort_by?: AlertSortField;
  sort_order?: "asc" | "desc";
  is_acknowledged?: boolean;
}

export interface CorrelationGroup {
  group_type: "cve" | "vendor";
  key: string;
  count: number;
  severities: string[];
  sources: string[];
  alert_ids: number[];
}

export interface CorrelationsResponse {
  groups: CorrelationGroup[];
}
