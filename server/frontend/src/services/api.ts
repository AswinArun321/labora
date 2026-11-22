import { AuthTokens } from '../types';

export const TOKENS_KEY = 'labora.tokens';

export function getTokens(): AuthTokens | null {
  try {
    const raw = sessionStorage.getItem(TOKENS_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

export function setTokens(tokens: AuthTokens | null): void {
  if (tokens) {
    sessionStorage.setItem(TOKENS_KEY, JSON.stringify(tokens));
  } else {
    sessionStorage.removeItem(TOKENS_KEY);
  }
}

export class ApiError extends Error {
  status: number;
  data: any;
  code?: string;

  constructor(status: number, data: any) {
    const message =
      (data && (data.detail?.detail || data.detail)) || `Request failed (${status})`;
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.data = data;
    this.code = data?.code || data?.detail?.code;
  }
}

let isRefreshing = false;
let refreshPromise: Promise<boolean> | null = null;

export async function refreshToken(): Promise<boolean> {
  if (isRefreshing && refreshPromise) {
    return refreshPromise;
  }

  const tokens = getTokens();
  if (!tokens?.refresh) {
    return false;
  }

  isRefreshing = true;
  refreshPromise = (async () => {
    try {
      const res = await fetch('/api/auth/refresh/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refresh: tokens.refresh }),
      });
      if (!res.ok) {
        setTokens(null);
        return false;
      }
      const data = await res.json();
      setTokens({ access: data.access, refresh: data.refresh || tokens.refresh });
      return true;
    } catch {
      setTokens(null);
      return false;
    } finally {
      isRefreshing = false;
      refreshPromise = null;
    }
  })();

  return refreshPromise;
}

export interface ApiOptions {
  method?: string;
  body?: any;
  raw?: boolean;
  form?: FormData;
}

export async function api<T = any>(
  endpoint: string,
  { method = 'GET', body, raw = false, form }: ApiOptions = {},
  allowRetry = true
): Promise<T> {
  const headers: Record<string, string> = {};
  const tokens = getTokens();
  if (tokens?.access) {
    headers['Authorization'] = `Bearer ${tokens.access}`;
  }

  let requestBody: any;
  if (form) {
    requestBody = form;
  } else if (body !== undefined) {
    headers['Content-Type'] = 'application/json';
    requestBody = JSON.stringify(body);
  }

  const url = endpoint.startsWith('/api') ? endpoint : `/api${endpoint}`;
  const res = await fetch(url, {
    method,
    headers,
    body: requestBody,
  });

  if (res.status === 401 && allowRetry && tokens?.refresh) {
    const refreshed = await refreshToken();
    if (refreshed) {
      return api<T>(endpoint, { method, body, raw, form }, false);
    }
    window.dispatchEvent(new Event('labora:logout'));
  }

  if (raw) {
    if (!res.ok) {
      let errData = null;
      try {
        errData = await res.json();
      } catch {
        // ignore
      }
      throw new ApiError(res.status, errData);
    }
    return res as unknown as T;
  }

  const text = await res.text();
  let data: any = null;
  try {
    data = text ? JSON.parse(text) : null;
  } catch {
    data = { detail: text.slice(0, 300) };
  }

  if (!res.ok) {
    throw new ApiError(res.status, data);
  }

  return data as T;
}

export async function downloadFile(endpoint: string, fallbackFilename: string): Promise<void> {
  const res = await api<Response>(endpoint, { raw: true });
  const disposition = res.headers.get('Content-Disposition') || '';
  const match = disposition.match(/filename="([^"]+)"/);
  const filename = match ? match[1] : fallbackFilename;
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 5000);
}
