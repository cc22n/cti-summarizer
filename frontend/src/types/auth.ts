export interface LoginRequest {
  username: string;
  password: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  username: string;
  role: string;
}

export interface AuthUser {
  username: string;
  role: "admin" | "analyst" | "viewer";
}

export interface UserCreate {
  username: string;
  password: string;
  role: "admin" | "analyst" | "viewer";
}

export interface UserResponse {
  id: number;
  username: string;
  role: string;
  is_active: boolean;
  created_at: string;
}
