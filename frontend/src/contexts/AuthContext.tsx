import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from "react";
import api from "../services/api";
import { authApi } from "../services/auth";
import type { AuthUser } from "../types/auth";

const TOKEN_KEY = "cti_access_token";

interface AuthContextValue {
  user: AuthUser | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (username: string, password: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const applyToken = useCallback((token: string) => {
    api.defaults.headers.common["Authorization"] = `Bearer ${token}`;
  }, []);

  const logout = useCallback(() => {
    localStorage.removeItem(TOKEN_KEY);
    delete api.defaults.headers.common["Authorization"];
    setUser(null);
  }, []);

  // Restore session from localStorage on mount
  useEffect(() => {
    const stored = localStorage.getItem(TOKEN_KEY);
    if (!stored) {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setIsLoading(false);
      return;
    }
    applyToken(stored);
    authApi
      .me()
      .then((r) =>
        setUser({ username: r.data.username, role: r.data.role as AuthUser["role"] })
      )
      .catch(() => logout())
      .finally(() => setIsLoading(false));
  }, [applyToken, logout]);

  const login = useCallback(
    async (username: string, password: string) => {
      const r = await authApi.login({ username, password });
      const { access_token, username: uname, role } = r.data;
      localStorage.setItem(TOKEN_KEY, access_token);
      applyToken(access_token);
      setUser({ username: uname, role: role as AuthUser["role"] });
    },
    [applyToken]
  );

  return (
    <AuthContext.Provider
      value={{ user, isAuthenticated: !!user, isLoading, login, logout }}
    >
      {children}
    </AuthContext.Provider>
  );
}

// eslint-disable-next-line react-refresh/only-export-components
export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside AuthProvider");
  return ctx;
}
