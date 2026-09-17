import type { ChatHistoryMessage, ChatResponse } from '../api/types'

export type ConversationTurn =
  | { id: string; role: 'user'; text: string }
  | { id: string; role: 'assistant'; response: ChatResponse }
  | { id: string; role: 'assistant-error'; message: string }

const MAX_HISTORY_MESSAGES = 8
const MAX_MESSAGE_LENGTH = 2000

/**
 * Builds the `history` field CONTRACTS.md bounds to at most eight prior
 * user/assistant messages of 2000 characters each. Clarification and
 * transport-error turns carry no answer text, so they're left out rather
 * than sent as empty content.
 */
export function buildHistory(turns: ConversationTurn[]): ChatHistoryMessage[] {
  const messages: ChatHistoryMessage[] = []
  for (const turn of turns) {
    if (turn.role === 'user') {
      messages.push({ role: 'user', content: turn.text.slice(0, MAX_MESSAGE_LENGTH) })
    } else if (turn.role === 'assistant' && turn.response.status === 'answered' && turn.response.answer) {
      messages.push({ role: 'assistant', content: turn.response.answer.slice(0, MAX_MESSAGE_LENGTH) })
    }
  }
  return messages.slice(-MAX_HISTORY_MESSAGES)
}
