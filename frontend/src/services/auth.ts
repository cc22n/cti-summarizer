import api from "./api";
import type {
  LoginRequest,
  TokenResponse,
  UserCreate,
  UserResponse,
} from "../types/auth";

export const authApi = {
  login: (body: LoginRequest) =>
    api.post<TokenResponse>("/auth/login", body),

  me: () => api.get<UserResponse>("/auth/me"),

  register: (body: UserCreate) =>
    api.post<UserResponse>("/auth/register", body),

  listUsers: () => api.get<UserResponse[]>("/auth/users"),
};
