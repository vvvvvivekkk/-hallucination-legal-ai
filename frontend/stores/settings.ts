"use client";

import { create } from "zustand";
import { api } from "@/lib/api";
import type { User } from "@/lib/types";
import { extractError } from "@/lib/utils";
import { useAuthStore } from "./auth";

interface SettingsState {
  saving: boolean;
  error: string | null;
  success: string | null;
  updateProfile: (payload: { full_name?: string; avatar_url?: string; preferences?: Record<string, unknown> }) => Promise<void>;
  changePassword: (currentPassword: string, newPassword: string) => Promise<void>;
  clearMessages: () => void;
}

export const useSettingsStore = create<SettingsState>((set) => ({
  saving: false,
  error: null,
  success: null,

  async updateProfile(payload) {
    set({ saving: true, error: null, success: null });
    try {
      const user = await api.patch<User>("/api/auth/me", payload);
      useAuthStore.getState().updateUser(user);
      set({ saving: false, success: "Profile updated." });
    } catch (error) {
      set({ saving: false, error: extractError(error) });
    }
  },

  async changePassword(currentPassword, newPassword) {
    set({ saving: true, error: null, success: null });
    try {
      await api.post("/api/auth/change-password", {
        current_password: currentPassword,
        new_password: newPassword,
      });
      set({ saving: false, success: "Password updated." });
    } catch (error) {
      set({ saving: false, error: extractError(error) });
    }
  },

  clearMessages() {
    set({ error: null, success: null });
  },
}));
