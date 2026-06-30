"use client";

import { createContext, useCallback, useContext, useEffect, useState } from "react";
import { api, tokenStore } from "./api";
import type { User } from "./types";

interface AuthState {
  user: User | null;
  loading: boolean;
  login: (identifier: string, password: string) => Promise<void>;
  register: (b: { email: string; phone: string; full_name: string; password: string }) => Promise<void>;
  logout: () => void;
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  const refreshUser = useCallback(async () => {
    if (!tokenStore.access) { setUser(null); return; }
    try { setUser(await api.me()); } catch { tokenStore.clear(); setUser(null); }
  }, []);

  useEffect(() => { void refreshUser().finally(() => setLoading(false)); }, [refreshUser]);

  const login = useCallback(async (identifier: string, password: string) => {
    tokenStore.set(await api.login(identifier, password));
    setUser(await api.me());
  }, []);

  const register = useCallback(
    async (b: { email: string; phone: string; full_name: string; password: string }) => {
      await api.registerRider(b);
      tokenStore.set(await api.login(b.email, b.password));
      setUser(await api.me());
    },
    [],
  );

  const logout = useCallback(() => { tokenStore.clear(); setUser(null); }, []);

  return (
    <AuthContext.Provider value={{ user, loading, login, register, logout, refreshUser }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
