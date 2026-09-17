import { describe, expect, it } from 'vitest'
import { buildHistory } from './conversation'
import type { ConversationTurn } from './conversation'
import type { ChatResponse } from '../api/types'

function answered(answer: string): ChatResponse {
  return {
    answer,
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
}

describe('buildHistory', () => {
  it('maps user and answered-assistant turns to role/content pairs', () => {
    const turns: ConversationTurn[] = [
      { id: '1', role: 'user', text: 'How do I receive a delivery?' },
      { id: '2', role: 'assistant', response: answered('Verify the packing slip.') },
    ]
    expect(buildHistory(turns)).toEqual([
      { role: 'user', content: 'How do I receive a delivery?' },
      { role: 'assistant', content: 'Verify the packing slip.' },
    ])
  })

  it('omits clarification and error turns, which carry no answer content', () => {
    const turns: ConversationTurn[] = [
      { id: '1', role: 'user', text: 'Can we build Kit A?' },
      {
        id: '2',
        role: 'assistant',
        response: {
          answer: '',
          answer_citation_ids: [],
          status: 'needs_clarification',
          citations: [],
          procedure_result: null,
          inventory_result: null,
          clarification: { kind: 'assembly', question: 'Which one?', choices: [] },
          error: null,
          trace_id: 't',
          data_mode: 'synthetic',
        },
      },
      { id: '3', role: 'assistant-error', message: 'Network request failed' },
    ]
    expect(buildHistory(turns)).toEqual([{ role: 'user', content: 'Can we build Kit A?' }])
  })

  it('keeps only the most recent 8 messages', () => {
    const turns: ConversationTurn[] = Array.from({ length: 10 }, (_, i) => ({
      id: String(i),
      role: 'user' as const,
      text: `message ${i}`,
    }))
    const history = buildHistory(turns)
    expect(history).toHaveLength(8)
    expect(history[0].content).toBe('message 2')
    expect(history[7].content).toBe('message 9')
  })

  it('truncates any single message to 2000 characters', () => {
    const longText = 'a'.repeat(2500)
    const turns: ConversationTurn[] = [{ id: '1', role: 'user', text: longText }]
    expect(buildHistory(turns)[0].content).toHaveLength(2000)
  })
})
