import { afterEach, describe, expect, it, vi } from 'vitest'
import { createLiveClient, createMockClient } from './client'
import type { ChatResponse, SopSection } from './types'

describe('createMockClient', () => {
  it('resolves with the scenario matching the request message', async () => {
    const client = createMockClient()
    const response = await client.sendChat({ message: 'How do I receive a delivery?' })
    expect(response.status).toBe('answered')
    expect(response.procedure_result?.document_id).toBe('sop-receiving')
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

  it('posts the request to /api/chat under the given base URL and returns the parsed body', async () => {
    const body: Partial<ChatResponse> = { status: 'answered', answer: 'ok' }
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(body),
    })
    globalThis.fetch = fetchMock as unknown as typeof fetch

    const client = createLiveClient('https://api.example.test')
    const response = await client.sendChat({ message: 'hello' })

    expect(fetchMock).toHaveBeenCalledWith(
      'https://api.example.test/api/chat',
      expect.objectContaining({ method: 'POST' }),
    )
    expect(response.answer).toBe('ok')
  })

  it('throws when the live request is not ok', async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({ ok: false, status: 503 }) as unknown as typeof fetch
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
