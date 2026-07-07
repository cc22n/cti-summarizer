import { useQuery } from "@tanstack/react-query";
import { dashboardApi } from "../services/dashboard";

export function useDashboardOverview() {
  return useQuery({
    queryKey: ["dashboard", "overview"],
    queryFn: () => dashboardApi.overview().then((r) => r.data),
    refetchInterval: 60_000,
    staleTime: 30_000,
  });
}

export function useTimeline(days = 30) {
  return useQuery({
    queryKey: ["dashboard", "timeline", days],
    queryFn: () => dashboardApi.timeline(days).then((r) => r.data),
    staleTime: 60_000,
  });
}
