import api from "./api";
import type { Summary, SummaryListResponse } from "../types/summary";

export const summariesApi = {
  list: (params: {
    page?: number;
    page_size?: number;
    summary_type?: string;
    normalized_alert_id?: number;
  }) => api.get<SummaryListResponse>("/summaries", { params }),
  get: (id: number) => api.get<Summary>(`/summaries/${id}`),
  latestDigest: () => api.get<Summary>("/summaries/digest/latest"),
  generate: (alert_ids: number[]) =>
    api.post<{ message: string; task_id: string }>("/summaries/generate", {
      alert_ids,
    }),
  generateDigest: (hours = 24) =>
    api.post<{ message: string; task_id: string }>(
      "/summaries/digest/generate",
      { hours }
    ),
};
