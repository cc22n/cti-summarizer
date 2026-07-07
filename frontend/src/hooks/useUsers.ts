import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { authApi } from "../services/auth";
import type { UserCreate } from "../types/auth";

export function useUsers() {
  return useQuery({
    queryKey: ["users"],
    queryFn: () => authApi.listUsers().then((r) => r.data),
    staleTime: 30_000,
  });
}

export function useCreateUser() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: UserCreate) => authApi.register(body).then((r) => r.data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["users"] });
    },
  });
}
