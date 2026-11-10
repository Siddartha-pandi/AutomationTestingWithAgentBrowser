"use client";

import React, { createContext, useContext, useEffect, useState } from "react";
import { authApi } from "@/api";

export interface UserProfile {
  email: string;
  full_name: string;
  role: string;
}

interface AuthContextType {
  user: UserProfile | null;
  token: string | null;
  isLoading: boolean;
  login: (email: string, pass: string) => Promise<void>;
  register: (email: string, pass: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<UserProfile | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const storedToken = localStorage.getItem("auth_token");
    const storedUser = localStorage.getItem("auth_user");

    if (storedToken && storedUser) {
      try {
        setToken(storedToken);
        setUser(JSON.parse(storedUser));
      } catch {
        localStorage.removeItem("auth_token");
        localStorage.removeItem("auth_user");
        setToken(null);
        setUser(null);
      }
    }
    setIsLoading(false);

    const handleUnauthorized = () => {
      logout();
    };
    window.addEventListener("auth:unauthorized", handleUnauthorized);
    return () => {
      window.removeEventListener("auth:unauthorized", handleUnauthorized);
    };
  }, []);

  async function login(email: string, pass: string) {
    const res = await authApi.login(email, pass);
    localStorage.setItem("auth_token", res.access_token);
    const profile: UserProfile = {
      email: res.user?.email || email,
      full_name: res.user?.full_name || email.split("@")[0],
      role: res.user?.role || "Owner",
    };
    localStorage.setItem("auth_user", JSON.stringify(profile));
    setToken(res.access_token);
    setUser(profile);
  }

  async function register(email: string, pass: string) {
    const res = await authApi.register(email, pass);
    localStorage.setItem("auth_token", res.access_token);
    const profile: UserProfile = {
      email: res.user?.email || email,
      full_name: res.user?.full_name || email.split("@")[0],
      role: res.user?.role || "Owner",
    };
    localStorage.setItem("auth_user", JSON.stringify(profile));
    setToken(res.access_token);
    setUser(profile);
  }

  function logout() {
    localStorage.removeItem("auth_token");
    localStorage.removeItem("auth_user");
    setToken(null);
    setUser(null);
  }

  return (
    <AuthContext.Provider value={{ user, token, isLoading, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}

