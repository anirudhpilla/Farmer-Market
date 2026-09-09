import { createContext, useContext, useEffect, useState } from "react";
import { Navigate, Outlet } from "react-router-dom";

import {
  login as loginRequest,
  logout as logoutRequest,
  hasAdminSession,
  onAuthExpired,
  refreshSession,
  setAccessToken,
} from "./api";
import type { AdminUser } from "./api";

type AuthContextValue = {
  user: AdminUser | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
};

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<AdminUser | null>(null);
  const [loading, setLoading] = useState(hasAdminSession);

  useEffect(() => {
    if (!hasAdminSession()) return;

    let active = true;

    refreshSession()
      .then((result) => {
        if (active) setUser(result.user);
      })
      .catch(() => setAccessToken(null))
      .finally(() => {
        if (active) setLoading(false);
      });

    return () => {
      active = false;
    };
  }, []);

  useEffect(() => onAuthExpired(() => setUser(null)), []);

  async function login(email: string, password: string) {
    const result = await loginRequest(email, password);
    setUser(result.user);
  }

  async function logout() {
    try {
      await logoutRequest();
    } finally {
      setAccessToken(null);
      setUser(null);
    }
  }

  return (
    <AuthContext.Provider value={{ user, loading, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

// Kept beside the small provider to avoid splitting auth across several files.
// eslint-disable-next-line react-refresh/only-export-components
export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth must be used inside AuthProvider");
  return context;
}

export function RequireAdmin() {
  const { user, loading } = useAuth();

  if (loading) return <p className="catalog-message">Restoring admin session…</p>;
  if (!user) return <Navigate to="/admin/login" replace />;
  return <Outlet />;
}
