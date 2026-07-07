import api from "./api";
import type { DashboardOverview, TimelineResponse } from "../types/dashboard";

export const dashboardApi = {
  overview: () => api.get<DashboardOverview>("/dashboard/overview"),
  timeline: (days = 30) =>
    api.get<TimelineResponse>("/dashboard/timeline", { params: { days } }),
};
