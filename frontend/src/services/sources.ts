import api from "./api";
import type { Source, SourceHealth, IngestionLogListResponse } from "../types/source";

export const sourcesApi = {
  list: () => api.get<Source[]>("/sources"),
  health: (id: number) => api.get<SourceHealth>(`/sources/${id}/health`),
  poll: (id: number) => api.post(`/sources/${id}/poll`),
  toggle: (id: number) => api.patch<Source>(`/sources/${id}/toggle`),
  logs: (id: number, page = 1, pageSize = 10) =>
    api.get<IngestionLogListResponse>(`/sources/${id}/logs`, {
      params: { page, page_size: pageSize },
    }),
};
