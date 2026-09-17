import { afterEach, describe, expect, it, vi } from 'vitest'
import { createLiveClient, createMockClient } from './client'
import type { ChatResponse, SopSection, ValidationErrorResponse } from './types'

describe('createMockClient', () => {
  it('resolves with the scenario matching the request message', async () => {
    const client = createMockClient()
    const response = await client.sendChat({ message: 'How do I receive a delivery?' })
    expect(response.status).toBe('answered')
    expect(response.procedure_result?.sources[0]?.document_id).toBe('sop-receiving')
  })

  it('rejects to simulate a network failure when the scenario calls for one', async () => {
    const client = createMockClient()
    await expect(client.sendChat({ message: 'simulate a network disconnect' })).rejects.toThrow()
  })

  it('looks up a known section fixture by document/section/version', async () => {
    const client = createMockClient()
    const section = await client.getSection('sop-receiving', 'sec-2', '3')
    expect(section?.text).toContain('packing slip')
  })

  it('returns null instead of substituting the latest text for an unknown version', async () => {
    const client = createMockClient()
    const section = await client.getSection('sop-receiving', 'sec-2', '99')
    expect(section).toBeNull()
  })
})

describe('createLiveClient', () => {
  const originalFetch = globalThis.fetch

  afterEach(() => {
    globalThis.fetch = originalFetch
  })

  function mockFetchOnce(response: { ok: boolean; status: number; body: unknown }) {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: response.ok,
      status: response.status,
      json: () => Promise.resolve(response.body),
    })
    globalThis.fetch = fetchMock as unknown as typeof fetch
    return fetchMock
  }

  it('posts the request to /api/chat under the given base URL and returns the parsed body', async () => {
    const body: ChatResponse = {
      answer: 'ok',
      answer_citation_ids: [],
      status: 'answered',
      citations: [],
      procedure_result: null,
      inventory_result: null,
      clarification: null,
      error: null,
      trace_id: 't',
      data_mode: 'synthetic',
    }
    const fetchMock = mockFetchOnce({ ok: true, status: 200, body })

    const client = createLiveClient('https://api.example.test')
    const response = await client.sendChat({ message: 'hello' })

    expect(fetchMock).toHaveBeenCalledWith(
      'https://api.example.test/api/chat',
      expect.objectContaining({ method: 'POST' }),
    )
    expect(response.answer).toBe('ok')
  })

  it('parses a 503 response as a real ChatResponse instead of throwing (same envelope per the API)', async () => {
    const body: ChatResponse = {
      answer: 'Part of this request is temporarily unavailable.',
      answer_citation_ids: [],
      status: 'temporarily_unavailable',
      citations: [],
      procedure_result: null,
      inventory_result: null,
      clarification: null,
      error: { code: 'provider_not_configured', message: 'no key', retryable: false },
      trace_id: 't',
      data_mode: 'synthetic',
    }
    mockFetchOnce({ ok: false, status: 503, body })

    const client = createLiveClient('https://api.example.test')
    const response = await client.sendChat({ message: 'hello' })
    expect(response.status).toBe('temporarily_unavailable')
    expect(response.error?.code).toBe('provider_not_configured')
  })

  it('converts a 422 ValidationErrorResponse into a temporarily_unavailable ChatResponse', async () => {
    const body: ValidationErrorResponse = {
      error: { code: 'validation_error', message: 'message too long', retryable: false },
      trace_id: 't',
      data_mode: 'synthetic',
    }
    mockFetchOnce({ ok: false, status: 422, body })

    const client = createLiveClient('https://api.example.test')
    const response = await client.sendChat({ message: 'hello' })
    expect(response.status).toBe('temporarily_unavailable')
    expect(response.error?.code).toBe('validation_error')
  })

  it('throws on a genuine transport failure (fetch itself rejects)', async () => {
    globalThis.fetch = vi.fn().mockRejectedValue(new Error('network down')) as unknown as typeof fetch
    const client = createLiveClient('https://api.example.test')
    await expect(client.sendChat({ message: 'hello' })).rejects.toThrow()
  })

  it('returns null when a live section lookup responds 404', async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({ ok: false, status: 404 }) as unknown as typeof fetch
    const client = createLiveClient('https://api.example.test')
    const section: SopSection | null = await client.getSection('doc', 'sec', '1')
    expect(section).toBeNull()
  })
})
