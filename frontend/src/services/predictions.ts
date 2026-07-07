import api from "./api";
import type {
  PredictionLatestResponse,
  PredictionGenerateResponse,
  TaskStatusResponse,
} from "../types/prediction";

export const predictionsApi = {
  latest: () => api.get<PredictionLatestResponse>("/predictions/latest"),
  generate: () => api.post<PredictionGenerateResponse>("/predictions/generate"),
  taskStatus: (taskId: string) =>
    api.get<TaskStatusResponse>(`/predictions/tasks/${taskId}`),
};
