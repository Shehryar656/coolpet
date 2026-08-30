import React, { createContext, useContext, useEffect, useState, useCallback } from "react";
import { api } from "./api";

const AuthCtx = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  const checkAuth = useCallback(async () => {
    try {
      const r = await api.get("/auth/me");
      setUser(r.data.user);
    } catch {
      const token = localStorage.getItem("coolpet_token");
      if (token) localStorage.removeItem("coolpet_token");
      setUser(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    // If we're returning from Emergent OAuth, defer to AuthCallback to
    // exchange the session_id before running /auth/me. Otherwise the
    // /auth/me call races the cookie set and returns 401 spuriously.
    if (typeof window !== "undefined" && window.location.hash?.includes("session_id=")) {
      setLoading(false);
      return;
    }
    checkAuth();
  }, [checkAuth]);

  const login = async (email, password) => {
    const { data } = await api.post("/auth/login", { email, password });
    localStorage.setItem("coolpet_token", data.token);
    setUser(data.user);
    return data.user;
  };
  const signup = async (name, email, password) => {
    const { data } = await api.post("/auth/signup", { name, email, password });
    localStorage.setItem("coolpet_token", data.token);
    setUser(data.user);
    return data.user;
  };
  const logout = async () => {
    localStorage.removeItem("coolpet_token");
    try { await api.post("/auth/logout"); } catch { /* noop */ }
    setUser(null);
  };
  const applyUser = (u) => setUser(u);

  return (
    <AuthCtx.Provider value={{ user, loading, login, signup, logout, applyUser, checkAuth }}>
      {children}
    </AuthCtx.Provider>
  );
}

export const useAuth = () => useContext(AuthCtx);
