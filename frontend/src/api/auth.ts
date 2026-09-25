import http from "./http";
import type { UserInfo, TokenResult, LoginForm, RegisterForm } from "@/types";

export const authApi = {
  register(data: RegisterForm) {
    return http.post<UserInfo, UserInfo>("/auth/register", data);
  },
  login(data: LoginForm) {
    return http.post<TokenResult, TokenResult>("/auth/login", data);
  },
  me() {
    return http.get<UserInfo, UserInfo>("/auth/me");
  },
  changePassword(old_password: string, new_password: string) {
    return http.post<{ detail: string }, { detail: string }>("/auth/change-password", {
      old_password,
      new_password,
    });
  },
};