import {
  useQuery,
  useMutation,
  useQueryClient,
} from "@tanstack/react-query";
import { sourcesApi } from "../services/sources";

export function useSourceLogs(id: number, page = 1, pageSize = 10) {
  return useQuery({
    queryKey: ["sources", id, "logs", page, pageSize],
    queryFn: () => sourcesApi.logs(id, page, pageSize).then((r) => r.data),
    staleTime: 30_000,
    enabled: id > 0,
  });
}

export function useSources() {
  return useQuery({
    queryKey: ["sources"],
    queryFn: () => sourcesApi.list().then((r) => r.data),
    staleTime: 30_000,
  });
}

export function useSourceHealth(id: number) {
  return useQuery({
    queryKey: ["sources", id, "health"],
    queryFn: () => sourcesApi.health(id).then((r) => r.data),
    refetchInterval: 30_000,
    enabled: id > 0,
  });
}

export function usePollSource() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => sourcesApi.poll(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["sources"] });
    },
  });
}

export function useToggleSource() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => sourcesApi.toggle(id).then((r) => r.data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["sources"] });
    },
  });
}
