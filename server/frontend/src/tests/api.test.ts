import { describe, it, expect, beforeEach, vi } from 'vitest';
import { api, getTokens, setTokens } from '../services/api';

describe('API client and token management', () => {
  beforeEach(() => {
    sessionStorage.clear();
    vi.restoreAllMocks();
  });

  it('stores and retrieves tokens in sessionStorage', () => {
    expect(getTokens()).toBeNull();
    setTokens({ access: 'acc-123', refresh: 'ref-456' });
    expect(getTokens()).toEqual({ access: 'acc-123', refresh: 'ref-456' });
    setTokens(null);
    expect(getTokens()).toBeNull();
  });

  it('attaches Authorization header when access token is present', async () => {
    setTokens({ access: 'valid-access-token', refresh: 'ref-token' });

    const fetchMock = vi.fn().mockResolvedValue({
      status: 200,
      ok: true,
      text: async () => JSON.stringify({ message: 'success' }),
    });
    global.fetch = fetchMock;

    const data = await api('/test-endpoint/');
    expect(data).toEqual({ message: 'success' });
    expect(fetchMock).toHaveBeenCalledWith(
      '/api/test-endpoint/',
      expect.objectContaining({
        headers: expect.objectContaining({
          Authorization: 'Bearer valid-access-token',
        }),
      })
    );
  });

  it('throws ApiError with correct status and message on HTTP failure', async () => {
    global.fetch = vi.fn().mockResolvedValue({
      status: 400,
      ok: false,
      text: async () => JSON.stringify({ detail: 'Invalid credentials' }),
    });

    await expect(api('/bad-endpoint/')).rejects.toThrow('Invalid credentials');
  });

  it('refreshes token on 401 when refresh token is available', async () => {
    setTokens({ access: 'expired-access', refresh: 'valid-refresh' });

    let callCount = 0;
    global.fetch = vi.fn().mockImplementation((url: string) => {
      callCount++;
      if (url === '/api/auth/refresh/') {
        return Promise.resolve({
          ok: true,
          status: 200,
          json: async () => ({ access: 'new-access-token' }),
        });
      }
      if (callCount === 1) {
        return Promise.resolve({
          status: 401,
          ok: false,
          text: async () => JSON.stringify({ detail: 'token_not_valid' }),
        });
      }
      return Promise.resolve({
        status: 200,
        ok: true,
        text: async () => JSON.stringify({ data: 'authorized' }),
      });
    });

    const res = await api('/protected/');
    expect(res).toEqual({ data: 'authorized' });
    expect(getTokens()?.access).toBe('new-access-token');
  });
});
