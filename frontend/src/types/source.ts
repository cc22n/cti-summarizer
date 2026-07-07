export interface Source {
  id: number;
  name: string;
  source_type: string;
  base_url: string;
  polling_interval_minutes: number;
  is_active: boolean;
  last_polled_at: string | null;
  created_at: string;
}

export interface SourceHealth {
  source_id: number;
  source_name: string;
  is_active: boolean;
  last_polled_at: string | null;
  last_status: string | null;
  last_error_message: string | null;
  alerts_last_24h: number;
  error_count_last_24h: number;
}

export interface IngestionLog {
  id: number;
  status: string;
  alerts_fetched: number;
  alerts_new: number;
  error_message: string | null;
  started_at: string;
  completed_at: string | null;
}

export interface IngestionLogListResponse {
  items: IngestionLog[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}
