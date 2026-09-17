import { selectScenario } from './mockScenarios'
import type { ChatRequest, ChatResponse, SopSection, ValidationErrorResponse } from './types'

const sectionFixtures = import.meta.glob<{ default: SopSection }>(
  '../../tests/fixtures/sections/*.json',
  { eager: true },
)

function sectionFixtureKey(documentId: string, sectionId: string, version: string): string {
  return `${documentId}__${sectionId}__v${version}`
}

const sectionsByKey = new Map<string, SopSection>()
for (const path in sectionFixtures) {
  const section = sectionFixtures[path].default
  sectionsByKey.set(sectionFixtureKey(section.document_id, section.section_id, section.version), section)
}

export interface ApiClient {
  sendChat(request: ChatRequest): Promise<ChatResponse>
  getSection(documentId: string, sectionId: string, version: string): Promise<SopSection | null>
}

function wait(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

export function createMockClient(): ApiClient {
  return {
    async sendChat(request) {
      const { response, delayMs, networkError } = selectScenario(request)
      await wait(delayMs)
      if (networkError) {
        throw new Error('Network request failed')
      }
      return response
    },
    async getSection(documentId, sectionId, version) {
      await wait(150)
      return sectionsByKey.get(sectionFixtureKey(documentId, sectionId, version)) ?? null
    },
  }
}

export function createLiveClient(baseUrl: string): ApiClient {
  return {
    async sendChat(request) {
      const res = await fetch(`${baseUrl}/api/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(request),
      })
      // Per the real API, 200/500/503/504 all use the ChatResponse envelope
      // (see docs/CONTRACTS.md: "Exception handlers use the same response
      // envelope where possible"). Only 422 (our own request was invalid)
      // uses a distinct ValidationErrorResponse without answer/status.
      if (res.status === 422) {
        const body = (await res.json()) as ValidationErrorResponse
        return {
          answer: '',
          answer_citation_ids: [],
          status: 'temporarily_unavailable',
          citations: [],
          procedure_result: null,
          inventory_result: null,
          clarification: null,
          error: body.error,
          trace_id: body.trace_id,
          data_mode: body.data_mode,
        }
      }
      return (await res.json()) as ChatResponse
    },
    async getSection(documentId, sectionId, version) {
      const url = `${baseUrl}/api/sops/${documentId}/sections/${sectionId}?version=${version}`
      const res = await fetch(url)
      if (res.status === 404) {
        return null
      }
      if (!res.ok) {
        throw new Error(`Section request failed with status ${res.status}`)
      }
      return (await res.json()) as SopSection
    },
  }
}

export function getApiClient(): ApiClient {
  const mode = import.meta.env.VITE_API_MODE ?? 'mock'
  if (mode === 'live') {
    const baseUrl = import.meta.env.VITE_API_BASE_URL
    if (!baseUrl) {
      throw new Error('VITE_API_BASE_URL is required when VITE_API_MODE=live')
    }
    return createLiveClient(baseUrl)
  }
  return createMockClient()
}
