export interface PredictionPoint {
  date: string; // "YYYY-MM-DD"
  predicted: number;
  lower: number;
  upper: number;
  is_anomaly: boolean;
}

export interface PredictionLatestResponse {
  run_id: string;
  generated_at: string; // ISO datetime
  training_days: number;
  model_type: string;
  series: Record<string, PredictionPoint[]>;
}

export interface PredictionGenerateResponse {
  task_id: string;
  status: string;
}

export interface TaskStatusResponse {
  task_id: string;
  status: string; // PENDING | STARTED | SUCCESS | FAILURE | RETRY
  result: Record<string, unknown> | null;
}
