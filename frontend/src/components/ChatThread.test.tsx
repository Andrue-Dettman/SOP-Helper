import { describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { ChatThread } from './ChatThread'
import type { ConversationTurn } from '../lib/conversation'

const turns: ConversationTurn[] = [
  { id: '1', role: 'user', text: 'How do I receive a delivery?' },
]

function renderThread(extra: Partial<Parameters<typeof ChatThread>[0]> = {}) {
  return render(
    <ChatThread
      turns={turns}
      isLoading={false}
      activeCitationId={null}
      onActivateCitation={vi.fn()}
      onSelectChoice={vi.fn()}
      onSubmitQuantity={vi.fn()}
      onRetry={vi.fn()}
      {...extra}
    />,
  )
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
})
