import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { summariesApi } from "../services/summaries";

export function useSummaries(params: {
  page?: number;
  page_size?: number;
  summary_type?: string;
  normalized_alert_id?: number;
}) {
  return useQuery({
    queryKey: ["summaries", params],
    queryFn: () => summariesApi.list(params).then((r) => r.data),
    placeholderData: (prev) => prev,
    staleTime: 30_000,
  });
}

export function useSummary(id: number) {
  return useQuery({
    queryKey: ["summary", id],
    queryFn: () => summariesApi.get(id).then((r) => r.data),
    staleTime: 60_000,
    enabled: id > 0,
  });
}

export function useLatestDigest() {
  return useQuery({
    queryKey: ["summaries", "digest", "latest"],
    queryFn: () => summariesApi.latestDigest().then((r) => r.data),
    staleTime: 60_000,
    retry: (failureCount, error) => {
      // Don't retry on 404 (no digest yet)
      const status = (error as { response?: { status?: number } })?.response
        ?.status;
      if (status === 404) return false;
      return failureCount < 2;
    },
  });
}

export function useGenerateDigest() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (hours: number) => summariesApi.generateDigest(hours),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["summaries"] });
    },
  });
}

export function useGenerateSummaries() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (alert_ids: number[]) => summariesApi.generate(alert_ids),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["summaries"] });
    },
  });
}
