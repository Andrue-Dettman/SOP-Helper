import { describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { ChatThread } from './ChatThread'
import type { ConversationTurn } from '../lib/conversation'

const turns: ConversationTurn[] = [
  { id: '1', role: 'user', text: 'How do I receive a delivery?' },
]

function baseProps(extra: Partial<Parameters<typeof ChatThread>[0]> = {}): Parameters<typeof ChatThread>[0] {
  return {
    turns,
    isLoading: false,
    activeCitationId: null,
    onActivateCitation: vi.fn(),
    onSelectChoice: vi.fn(),
    onSubmitQuantity: vi.fn(),
    onRetry: vi.fn(),
    ...extra,
  }
}

function renderThread(extra: Partial<Parameters<typeof ChatThread>[0]> = {}) {
  return render(<ChatThread {...baseProps(extra)} />)
}

function answeredTurn(id: string): ConversationTurn {
  return {
    id,
    role: 'assistant',
    response: {
      answer: 'Verify the packing slip.',
      answer_citation_ids: [],
      status: 'answered',
      citations: [],
      procedure_result: null,
      inventory_result: null,
      clarification: null,
      error: null,
      trace_id: 't',
      data_mode: 'synthetic',
    },
  }
}

describe('ChatThread', () => {
  it('renders as an accessible log that only announces additions', () => {
    renderThread()
    const log = screen.getByRole('log')
    expect(log).toHaveAttribute('aria-live', 'polite')
  })

  it('renders a message bubble per turn', () => {
    renderThread()
    expect(screen.getByText('How do I receive a delivery?')).toBeInTheDocument()
  })

  it('shows the loading indicator while a request is pending', () => {
    renderThread({ isLoading: true })
    expect(screen.getByRole('status')).toHaveTextContent(/thinking/i)
  })

  it('hides the loading indicator once the request resolves', () => {
    renderThread({ isLoading: false })
    expect(screen.queryByRole('status')).not.toBeInTheDocument()
  })

  it('moves focus to a newly added assistant answer', () => {
    const { rerender } = renderThread({ turns: [turns[0]] })
    rerender(<ChatThread {...baseProps({ turns: [turns[0], answeredTurn('2')] })} />)
    expect(screen.getByText('Verify the packing slip.').closest('[tabindex="-1"]')).toHaveFocus()
  })

  it('does not steal focus from the chat input while the user is typing', () => {
    const { rerender } = render(
      <div>
        <textarea aria-label="Ask a question" />
        <ChatThread {...baseProps({ turns: [turns[0]] })} />
      </div>,
    )
    screen.getByRole('textbox', { name: /ask a question/i }).focus()
    rerender(
      <div>
        <textarea aria-label="Ask a question" />
        <ChatThread {...baseProps({ turns: [turns[0], answeredTurn('2')] })} />
      </div>,
    )
    expect(screen.getByRole('textbox', { name: /ask a question/i })).toHaveFocus()
  })

  it('does not move focus when the newly added turn is the user’s own message', () => {
    const secondUserTurn: ConversationTurn = { id: '2', role: 'user', text: 'A follow-up question' }
    const { rerender } = renderThread({ turns: [turns[0]] })
    rerender(<ChatThread {...baseProps({ turns: [turns[0], secondUserTurn] })} />)
    expect(document.body).toHaveFocus()
  })
})
