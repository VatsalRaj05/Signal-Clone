/**
 * Auth service — wraps auth-related API calls.
 *
 * Components should call these functions (via TanStack Query hooks)
 * rather than importing the API client directly.
 */

import { apiClient } from "@/lib/api-client";
import type { LoginResponse, LoginRequest, VerifyOTPRequest, RegisterRequest, User } from "@/types";

export const authService = {
  login: (data: LoginRequest) =>
    apiClient.post<LoginResponse>("/auth/login", data),

  verifyOtp: (data: VerifyOTPRequest) =>
    apiClient.post<LoginResponse>("/auth/verify", data),

  register: (data: RegisterRequest) =>
    apiClient.post<{ message: string; user_id: string; mock_otp: string | null }>("/auth/register", data),

  me: () => apiClient.get<User>("/users/me"),
  
  updateProfile: (data: { display_name?: string; avatar_url?: string }) =>
    apiClient.put<User>("/users/me", data)
};
