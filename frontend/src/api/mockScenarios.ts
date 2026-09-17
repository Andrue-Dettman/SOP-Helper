import deliveryProcedure from '../../tests/fixtures/chat/delivery-procedure.json'
import termExplanation from '../../tests/fixtures/chat/term-explanation.json'
import ambiguousAssembly from '../../tests/fixtures/chat/ambiguous-assembly.json'
import buildReady from '../../tests/fixtures/chat/build-ready.json'
import buildNotReady from '../../tests/fixtures/chat/build-not-ready.json'
import stockFound from '../../tests/fixtures/chat/stock-found.json'
import insufficientEvidence from '../../tests/fixtures/chat/insufficient-evidence.json'
import temporarilyUnavailable from '../../tests/fixtures/chat/temporarily-unavailable.json'
import type { ChatRequest, ChatResponse } from './types'

export interface MockScenario {
  response: ChatResponse
  delayMs: number
  networkError: boolean
}

const DEFAULT_DELAY_MS = 400
const SLOW_DELAY_MS = 4000

function scenario(
  response: unknown,
  overrides: Partial<Omit<MockScenario, 'response'>> = {},
): MockScenario {
  return {
    response: response as ChatResponse,
    delayMs: DEFAULT_DELAY_MS,
    networkError: false,
    ...overrides,
  }
}

/**
 * Picks a canned response for fixture-driven development, keyed off the
 * request text (and, once an assembly has been disambiguated, the typed
 * selection). Deliberately simple substring rules so a person driving the
 * UI manually — or a Playwright test — can predict which fixture fires.
 */
export function selectScenario(request: ChatRequest): MockScenario {
  const message = request.message.toLowerCase()

  if (request.selection?.assembly_id === 'ASM-KIT-A-STD' || request.selection?.assembly_id === 'ASM-KIT-A-HD') {
    return scenario(buildReady)
  }

  if (message.includes('disconnect') || message.includes('network')) {
    return scenario(temporarilyUnavailable, { networkError: true })
  }
  if (message.includes('unavailable') || message.includes('offline')) {
    return scenario(temporarilyUnavailable)
  }
  if (message.includes('conflict') || message.includes('insufficient')) {
    return scenario(insufficientEvidence)
  }
  if (message.includes('slow') || message.includes('delay')) {
    return scenario(deliveryProcedure, { delayMs: SLOW_DELAY_MS })
  }
  if (message.includes('mean') || message.includes('exception')) {
    return scenario(termExplanation)
  }
  if (message.includes('shortage') || message.includes('not ready')) {
    return scenario(buildNotReady)
  }
  if (message.includes('deliver') || message.includes('receive')) {
    return scenario(deliveryProcedure)
  }
  if (message.includes('how many') || message.includes('stock of') || message.includes('side panel')) {
    return scenario(stockFound)
  }
  if (message.includes('kit a')) {
    return scenario(ambiguousAssembly)
  }
  if (message.includes('assemble') || message.includes('build')) {
    return scenario(buildReady)
  }

  return scenario(deliveryProcedure)
}
