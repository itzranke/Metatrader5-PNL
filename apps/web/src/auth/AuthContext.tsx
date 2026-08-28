import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import { api, setAccessToken, tryRefresh } from "../lib/api";

export interface User {
  id: number;
  username: string;
  email: string;
  email_verified: boolean;
  role: string;
  locale: string;
  base_currency: string;
  created_at: string;
}

interface AuthContextValue {
  user: User | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (username: string, email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue>(null!);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    (async () => {
      try {
        if (await tryRefresh()) {
          setUser(await api<User>("/auth/me"));
        }
      } catch {
        setUser(null);
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  const login = async (email: string, password: string) => {
    const r = await api<{ access_token: string; user: User }>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    });
    setAccessToken(r.access_token);
    setUser(r.user);
  };

  const register = async (username: string, email: string, password: string) => {
    await api("/auth/register", {
      method: "POST",
      body: JSON.stringify({ username, email, password }),
    });
  };

  const logout = async () => {
    try {
      await api("/auth/logout", { method: "POST" });
    } catch {
      /* token sudah mati — tetap logout lokal */
    } finally {
      setAccessToken(null);
      setUser(null);
    }
  };

  return (
    <AuthContext.Provider value={{ user, loading, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}
