import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { alertsApi } from "../services/alerts";
import type { AlertFilters } from "../types/alert";
import { useDebouncedValue } from "./useDebouncedValue";

export function useCorrelations(minCount = 2) {
  return useQuery({
    queryKey: ["alerts", "correlations", minCount],
    queryFn: () => alertsApi.correlations(minCount).then((r) => r.data),
    staleTime: 120_000,
  });
}

export function useAlerts(filters: AlertFilters) {
  return useQuery({
    queryKey: ["alerts", filters],
    queryFn: () => alertsApi.list(filters).then((r) => r.data),
    placeholderData: (prev) => prev,
    staleTime: 30_000,
  });
}

export function useAlert(id: number) {
  return useQuery({
    queryKey: ["alert", id],
    queryFn: () => alertsApi.get(id).then((r) => r.data),
    staleTime: 60_000,
    enabled: id > 0,
  });
}

export function useAlertStats() {
  return useQuery({
    queryKey: ["alerts", "stats"],
    queryFn: () => alertsApi.stats().then((r) => r.data),
    refetchInterval: 60_000,
    staleTime: 30_000,
  });
}

export function useAcknowledgeAlert() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => alertsApi.acknowledge(id).then((r) => r.data),
    onSuccess: (data) => {
      queryClient.setQueryData(["alert", data.id], data);
      queryClient.invalidateQueries({ queryKey: ["alerts"] });
    },
  });
}

export function useUpdateNotes() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, notes }: { id: number; notes: string | null }) =>
      alertsApi.updateNotes(id, notes).then((r) => r.data),
    onSuccess: (data) => {
      queryClient.setQueryData(["alert", data.id], data);
    },
  });
}

export function useSemanticSearch(query: string, limit = 10) {
  const debounced = useDebouncedValue(query, 500);
  return useQuery({
    queryKey: ["alerts", "semantic", debounced, limit],
    queryFn: () => alertsApi.semanticSearch(debounced, limit).then((r) => r.data),
    enabled: debounced.length >= 3,
    staleTime: 60_000,
    retry: false,
  });
}
