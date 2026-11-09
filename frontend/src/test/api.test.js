import { describe, expect, it, vi } from 'vitest';
import { api, ApiError } from '../services/api.js';

describe('central API service', () => {
  it('uses the documented customer summary route and returns its schema', async () => {
    const payload = { status: 'missing_inputs', customer_count: null, segment_count: 0 };
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true, json: async () => payload }));
    await expect(api.customerSummary()).resolves.toEqual(payload);
    expect(fetch).toHaveBeenCalledWith(expect.stringMatching(/\/api\/customers\/summary$/), expect.objectContaining({ headers: expect.objectContaining({ Accept: 'application/json' }) }));
  });

  it('surfaces backend validation errors with the response status', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: false, status: 422, json: async () => ({ detail: 'Invalid request' }) }));
    await expect(api.assistantHealth()).rejects.toMatchObject({ name: 'ApiError', status: 422, message: 'Invalid request' });
    expect(ApiError).toBeDefined();
  });
});
