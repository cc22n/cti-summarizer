import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import type { AxiosResponse } from "axios";
import { predictionsApi } from "../services/predictions";
import type { PredictionGenerateResponse } from "../types/prediction";

export function useLatestPredictions() {
  return useQuery({
    queryKey: ["predictions", "latest"],
    queryFn: () => predictionsApi.latest().then((r) => r.data),
    staleTime: 5 * 60_000,
    retry: (failureCount, error) => {
      const status = (error as { response?: { status?: number } })?.response
        ?.status;
      if (status === 404) return false;
      return failureCount < 2;
    },
  });
}

export function useGeneratePredictions() {
  const queryClient = useQueryClient();
  return useMutation<AxiosResponse<PredictionGenerateResponse>, Error>({
    mutationFn: () => predictionsApi.generate(),
    onSuccess: (response) => {
      const taskId = response.data.task_id;
      let pollCount = 0;
      const MAX_POLLS = 40; // 40 * 1.5s = 60s max wait

      const pollStatus = () => {
        pollCount += 1;
        if (pollCount > MAX_POLLS) {
          queryClient.invalidateQueries({ queryKey: ["predictions"] });
          return;
        }
        predictionsApi
          .taskStatus(taskId)
          .then((r) => {
            const { status } = r.data;
            if (status === "SUCCESS" || status === "FAILURE") {
              queryClient.invalidateQueries({ queryKey: ["predictions"] });
            } else {
              setTimeout(pollStatus, 1500);
            }
          })
          .catch(() => {
            // Fallback: invalidate after 5s if polling fails
            setTimeout(() => {
              queryClient.invalidateQueries({ queryKey: ["predictions"] });
            }, 5000);
          });
      };

      setTimeout(pollStatus, 1500);
    },
  });
}
