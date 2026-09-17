import { describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MessageBubble } from './MessageBubble'
import type { ConversationTurn } from '../lib/conversation'
import type { ChatResponse, Citation } from '../api/types'

const citation: Citation = {
  citation_id: 'cit-recv-001',
  document_id: 'sop-receiving',
  version: '3',
  section_id: 'sec-2',
  title: 'Dock Intake',
  quoted_text: 'Verify the packing slip.',
  source_uri: '/sops/sop-receiving/sections/sec-2?version=3',
}

function baseResponse(overrides: Partial<ChatResponse>): ChatResponse {
  return {
    answer: '',
    answer_citation_ids: [],
    status: 'answered',
    citations: [],
    procedure_result: null,
    inventory_result: null,
    clarification: null,
    error: null,
    trace_id: 't',
    data_mode: 'synthetic',
    ...overrides,
  }
}

function renderBubble(turn: ConversationTurn, extra: Partial<Parameters<typeof MessageBubble>[0]> = {}) {
  return render(
    <MessageBubble
      turn={turn}
      activeCitationId={null}
      onActivateCitation={vi.fn()}
      onSelectChoice={vi.fn()}
      onSubmitQuantity={vi.fn()}
      onRetry={vi.fn()}
      {...extra}
    />,
  )
}

describe('MessageBubble', () => {
  it('renders a user turn as plain text', () => {
    renderBubble({ id: '1', role: 'user', text: 'How do I receive a delivery?' })
    expect(screen.getByText('How do I receive a delivery?')).toBeInTheDocument()
  })

  it('renders an answered turn with its answer text and a numbered source chip', async () => {
    const onActivateCitation = vi.fn()
    renderBubble(
      {
        id: '2',
        role: 'assistant',
        response: baseResponse({
          answer: 'Verify the slip first.',
          answer_citation_ids: ['cit-recv-001'],
          citations: [citation],
        }),
      },
      { onActivateCitation },
    )
    expect(screen.getByText('Verify the slip first.')).toBeInTheDocument()
    const chip = screen.getByRole('button', { name: /dock intake/i })
    await userEvent.click(chip)
    expect(onActivateCitation).toHaveBeenCalledWith(citation)
  })

  it('renders procedure steps when the response carries a procedure_result', () => {
    renderBubble({
      id: '3',
      role: 'assistant',
      response: baseResponse({
        answer: 'Here is how.',
        procedure_result: {
          state: 'ok',
          sources: [{ document_id: 'sop-receiving', version: '3', section_id: 'sec-2', is_current: true }],
          warnings: [],
          prerequisites: [],
          explanation: null,
          fallback_used: false,
          steps: [
            {
              step_id: 's1',
              ordinal: 1,
              text: 'Verify the slip.',
              citation_ids: [],
            },
          ],
        },
      }),
    })
    expect(screen.getByRole('button', { name: /show original/i })).toBeInTheDocument()
  })

  it('renders the inventory result when present', () => {
    renderBubble({
      id: '4',
      role: 'assistant',
      response: baseResponse({
        answer: 'Yes, ready.',
        inventory_result: {
          kind: 'build',
          state: 'ok',
          snapshot: { snapshot_id: 'snap-1', captured_at: '2026-09-14T08:00:00Z' },
          assembly_id: 'asm-1',
          requested_units: 20,
          ready: true,
          components: [],
        },
      }),
    })
    expect(screen.getByText('Ready')).toBeInTheDocument()
  })

  it('renders a clarification prompt for needs_clarification', async () => {
    const onSelectChoice = vi.fn()
    renderBubble(
      {
        id: '5',
        role: 'assistant',
        response: baseResponse({
          status: 'needs_clarification',
          clarification: {
            kind: 'assembly',
            question: 'Which one?',
            choices: [{ id: 'a', label: 'Option A' }],
          },
        }),
      },
      { onSelectChoice },
    )
    await userEvent.click(screen.getByRole('button', { name: 'Option A' }))
    expect(onSelectChoice).toHaveBeenCalledWith({ id: 'a', label: 'Option A' })
  })

  it('renders an insufficient-evidence banner', () => {
    renderBubble({
      id: '6',
      role: 'assistant',
      response: baseResponse({ status: 'insufficient_evidence' }),
    })
    expect(screen.getByText(/not enough evidence/i)).toBeInTheDocument()
  })

  it('renders a retryable temporarily-unavailable banner with the server message', async () => {
    const onRetry = vi.fn()
    renderBubble(
      {
        id: '7',
        role: 'assistant',
        response: baseResponse({
          status: 'temporarily_unavailable',
          error: { code: 'dependency_unavailable', message: 'Database is down.', retryable: true },
        }),
      },
      { onRetry },
    )
    expect(screen.getByText('Database is down.')).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: /retry/i }))
    expect(onRetry).toHaveBeenCalledTimes(1)
  })

  it('renders a network-error banner for a client-side transport failure', () => {
    renderBubble({ id: '8', role: 'assistant-error', message: 'Network request failed' })
    expect(screen.getByText(/couldn.t reach/i)).toBeInTheDocument()
  })
})
