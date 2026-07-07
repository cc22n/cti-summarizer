export interface Summary {
  id: number;
  normalized_alert_id: number | null;
  summary_type: string; // "alert" | "digest"
  content: string;
  model_used: string;
  prompt_tokens: number | null;
  completion_tokens: number | null;
  period_start: string | null;
  period_end: string | null;
  created_at: string;
}

export interface SummaryListResponse {
  items: Summary[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}
