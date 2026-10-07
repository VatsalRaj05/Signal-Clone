/**
 * Authentication store (Zustand).
 *
 * Manages JWT token and current user state.
 * This is one of the few pieces of truly global client state,
 * so Zustand is appropriate here.
 */

import { create } from "zustand";
import type { User } from "@/types";

interface AuthState {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;

  setAuth: (user: User, token: string) => void;
  clearAuth: () => void;
  hydrateFromStorage: () => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  token: null,
  isAuthenticated: false,

  setAuth: (user, token) => {
    if (typeof window !== "undefined") {
      localStorage.setItem("access_token", token);
      localStorage.setItem("auth_user", JSON.stringify(user));
    }
    set({ user, token, isAuthenticated: true });
  },

  clearAuth: () => {
    if (typeof window !== "undefined") {
      localStorage.removeItem("access_token");
      localStorage.removeItem("auth_user");
    }
    set({ user: null, token: null, isAuthenticated: false });
  },

  hydrateFromStorage: () => {
    if (typeof window !== "undefined") {
      const token = localStorage.getItem("access_token");
      if (token) {
        const rawUser = localStorage.getItem("auth_user");
        const user: User | null = rawUser ? JSON.parse(rawUser) : null;
        set({ token, isAuthenticated: true, user });
      }
    }
  },
}));
