import { describe, expect, it } from 'vitest'
import { selectScenario } from './mockScenarios'
import type { ChatRequest } from './types'

function request(message: string, selection?: ChatRequest['selection']): ChatRequest {
  return { message, selection }
}

describe('selectScenario', () => {
  it('matches a delivery-procedure question', () => {
    const { response } = selectScenario(request('How do I receive a delivery?'))
    expect(response.status).toBe('answered')
    expect(response.procedure_result?.sources[0]?.document_id).toBe('sop-receiving')
  })

  it('matches a term-explanation question', () => {
    const { response } = selectScenario(request('What does exception mean?'))
    expect(response.procedure_result?.steps[0].explanation).toContain('exception')
  })

  it('asks for clarification on an ambiguous assembly name', () => {
    const { response } = selectScenario(request('Can we assemble 20 units of Kit A?'))
    expect(response.status).toBe('needs_clarification')
    expect(response.clarification?.choices).toHaveLength(2)
  })

  it('resolves a build-ready result once an assembly is selected', () => {
    const { response } = selectScenario(
      request('Kit A — Standard', { assembly_id: 'ASM-KIT-A-STD' }),
    )
    expect(response.inventory_result?.kind).toBe('build')
    if (response.inventory_result?.kind === 'build') {
      expect(response.inventory_result.ready).toBe(true)
    }
  })

  it('matches a shortage question with a not-ready build result', () => {
    const { response } = selectScenario(request('Is there a shortage for Kit A?'))
    if (response.inventory_result?.kind === 'build') {
      expect(response.inventory_result.ready).toBe(false)
    } else {
      throw new Error('expected a build inventory result')
    }
  })

  it('matches an insufficient-evidence trigger', () => {
    const { response } = selectScenario(request('There is a conflict in the procedures'))
    expect(response.status).toBe('insufficient_evidence')
  })

  it('matches a temporarily-unavailable trigger', () => {
    const { response } = selectScenario(request('The system seems unavailable'))
    expect(response.status).toBe('temporarily_unavailable')
  })

  it('signals a network error for a network-failure trigger', () => {
    const { networkError } = selectScenario(request('simulate a network disconnect'))
    expect(networkError).toBe(true)
  })

  it('signals a longer delay for a slow-response trigger', () => {
    const { delayMs } = selectScenario(request('please respond slowly'))
    const { delayMs: defaultDelayMs } = selectScenario(request('How do I receive a delivery?'))
    expect(delayMs).toBeGreaterThan(defaultDelayMs)
  })

  it('falls back to the delivery-procedure fixture for an unrecognized message', () => {
    const { response } = selectScenario(request('gibberish query with no keywords'))
    expect(response.status).toBe('answered')
    expect(response.procedure_result?.sources[0]?.document_id).toBe('sop-receiving')
  })
})
