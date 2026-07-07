import api from "./api";
import type {
  Alert,
  AlertFilters,
  AlertListResponse,
  AlertStatsResponse,
  CorrelationsResponse,
} from "../types/alert";

interface SemanticSearchResponse {
  query: string;
  results: Alert[];
  method: "semantic" | "text";
  total: number;
}

export const alertsApi = {
  list: (filters: AlertFilters) =>
    api.get<AlertListResponse>("/alerts", { params: filters }),

  get: (id: number) => api.get<Alert>(`/alerts/${id}`),

  stats: () => api.get<AlertStatsResponse>("/alerts/stats"),

  acknowledge: (id: number) => api.patch<Alert>(`/alerts/${id}/acknowledge`),

  updateNotes: (id: number, notes: string | null) =>
    api.patch<Alert>(`/alerts/${id}/notes`, { notes }),

  semanticSearch: (q: string, limit = 10) =>
    api.get<SemanticSearchResponse>("/alerts/semantic-search", {
      params: { q, limit },
    }),

  correlations: (minCount = 2) =>
    api.get<CorrelationsResponse>("/alerts/correlations", {
      params: { min_count: minCount },
    }),

  exportCsv: async (params?: Record<string, string>) => {
    const query = new URLSearchParams({ format: "csv", ...params }).toString();
    const token = api.defaults.headers.common["Authorization"] as string | undefined;
    const resp = await fetch(`${api.defaults.baseURL}/alerts/export?${query}`, {
      headers: token ? { Authorization: token } : {},
    });
    if (!resp.ok) return;
    const blob = await resp.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "alerts.csv";
    a.click();
    URL.revokeObjectURL(url);
  },

  exportStix: async (params?: Record<string, string>) => {
    const query = new URLSearchParams({ format: "stix", ...params }).toString();
    const token = api.defaults.headers.common["Authorization"] as string | undefined;
    const resp = await fetch(`${api.defaults.baseURL}/alerts/export?${query}`, {
      headers: token ? { Authorization: token } : {},
    });
    if (!resp.ok) return;
    const blob = await resp.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "alerts.stix2.json";
    a.click();
    URL.revokeObjectURL(url);
  },
};
