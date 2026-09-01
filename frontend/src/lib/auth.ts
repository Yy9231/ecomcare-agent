import { request } from "./api";

export type Role = "customer" | "agent";

export type AuthSession = {
  access_token: string;
  username: string;
  customer_id: string;
  display_name: string;
  role: Role;
};

// 分角色保存 Token，使客户页和客服工作台可以在两个标签页同时登录。
const storageKey = (role: Role) => `ecomcare.auth.${role}.v1`;

export function loadSession(role: Role): AuthSession | null {
  try {
    const value = localStorage.getItem(storageKey(role));
    if (!value) return null;
    const session = JSON.parse(value) as AuthSession;
    return session.role === role && Boolean(session.access_token) ? session : null;
  } catch {
    return null;
  }
}

export function saveSession(session: AuthSession) {
  localStorage.setItem(storageKey(session.role), JSON.stringify(session));
}

export function clearSession(role: Role) {
  localStorage.removeItem(storageKey(role));
}

export function login(username: string, password: string) {
  return request<AuthSession>("/auth/login", undefined, {
    method: "POST",
    body: JSON.stringify({ username, password }),
  });
}

export function validateSession(token: string) {
  return request<AuthSession>("/auth/me", token);
}
