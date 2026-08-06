"use client";

import { create } from "zustand";
import { api, fetchMe } from "@/lib/api";
import type { AuthTokens, User } from "@/lib/types";
import { extractError } from "@/lib/utils";

interface AuthState {
  user: User | null;
  status: "idle" | "loading" | "authenticated" | "unauthenticated";
  error: string | null;
  load: () => Promise<void>;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, fullName: string) => Promise<void>;
  logout: () => Promise<void>;
  logoutAll: () => Promise<void>;
  updateUser: (user: User) => void;
  clearError: () => void;
}

export const useAuthStore = create<AuthState>((set, get) => ({
  user: null,
  status: "idle",
  error: null,

  async load() {
    const existing = sessionStorage.getItem("access_token");
    if (!existing) {
      set({ status: "unauthenticated" });
      return;
    }
    set({ status: "loading" });
    try {
      const user = await fetchMe();
      set({ user, status: "authenticated" });
    } catch {
      set({ user: null, status: "unauthenticated" });
    }
  },

  async login(email, password) {
    set({ error: null });
    try {
      const tokens = await api.post<AuthTokens>("/api/auth/login", { email, password });
      api.setTokens(tokens);
      set({ user: tokens.user, status: "authenticated" });
    } catch (error) {
      set({ error: extractError(error) });
      throw error;
    }
  },

  async register(email, password, fullName) {
    set({ error: null });
    try {
      const tokens = await api.post<AuthTokens>("/api/auth/register", {
        email,
        password,
        full_name: fullName,
      });
      api.setTokens(tokens);
      set({ user: tokens.user, status: "authenticated" });
    } catch (error) {
      set({ error: extractError(error) });
      throw error;
    }
  },

  async logout() {
    try {
      await api.post("/api/auth/logout", {});
    } catch {
      // best effort
    }
    api.clearSession();
    set({ user: null, status: "unauthenticated" });
  },

  async logoutAll() {
    try {
      await api.post("/api/auth/logout-all", {});
    } catch {
      // best effort
    }
    api.clearSession();
    set({ user: null, status: "unauthenticated" });
  },

  updateUser(user: User) {
    set({ user });
  },

  clearError() {
    set({ error: null });
  },
}));

export function useIsAuthenticated(): boolean {
  return useAuthStore((state) => state.status === "authenticated");
}

export function isAdmin(user: User | null): boolean {
  return user?.role === "admin";
}
