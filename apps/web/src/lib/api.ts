/**
 * API client — Phase 2.
 * Access token disimpan IN-MEMORY (aman dari XSS localStorage), dikirim via
 * Authorization: Bearer. Refresh token di cookie httpOnly; auto-refresh saat 401.
 */
const API_BASE = import.meta.env.VITE_API_BASE ?? "/api/v1";

let accessToken: string | null = null;

export function setAccessToken(token: string | null) {
  accessToken = token;
}

export function getAccessToken(): string | null {
  return accessToken;
}

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
  }
}

export async function api<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers: Record<string, string> = {
    ...(options.headers as Record<string, string> | undefined),
  };
  if (accessToken) headers["Authorization"] = `Bearer ${accessToken}`;
  const res = await fetch(`${API_BASE}${path}`, { ...options, headers, credentials: "include" });

  if (res.status === 401 && !path.startsWith("/auth/")) {
    if (await tryRefresh()) return api<T>(path, options);
  }

  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail ?? detail;
    } catch {
      /* body bukan JSON */
    }
    throw new ApiError(res.status, detail);
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}

let refreshPromise: Promise<boolean> | null = null;

export function tryRefresh(): Promise<boolean> {
  if (!refreshPromise) {
    refreshPromise = (async () => {
      try {
        const res = await fetch(`${API_BASE}/auth/refresh`, {
          method: "POST",
          credentials: "include",
        });
        if (res.ok) {
          const body = await res.json();
          accessToken = body.access_token;
          return true;
        }
        return false;
      } catch {
        return false;
      } finally {
        setTimeout(() => {
          refreshPromise = null;
        }, 0);
      }
    })();
  }
  return refreshPromise;
}
