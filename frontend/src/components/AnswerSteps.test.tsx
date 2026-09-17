import { describe, expect, it, vi } from 'vitest'
import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { AnswerSteps } from './AnswerSteps'
import { buildCitationIndex } from '../lib/citations'
import type { Citation, ProcedureResult } from '../api/types'

const citations: Citation[] = [
  {
    citation_id: 'cit-recv-001',
    document_id: 'sop-receiving',
    version: '3',
    section_id: 'sec-2',
    title: 'Dock Intake',
    quoted_text: 'Verify the packing slip.',
    source_uri: '/sops/sop-receiving/sections/sec-2?version=3',
  },
]

const procedureResult: ProcedureResult = {
  state: 'ok',
  sources: [{ document_id: 'sop-receiving', version: '3', section_id: 'sec-2', is_current: true }],
  prerequisites: [{ id: 'pre-1', text: 'Have the delivery note ready.', citation_ids: [] }],
  warnings: [
    {
      warning_id: 'warn-1',
      text: 'Do not stock a pallet with unresolved damage exceptions.',
      applies_to_step_ids: ['step-2'],
      citation_ids: [],
    },
  ],
  explanation: null,
  fallback_used: false,
  steps: [
    {
      step_id: 'step-1',
      ordinal: 1,
      text: 'Verify the packing slip against the purchase order.',
      explanation: 'Check the slip matches what was ordered.',
      citation_ids: ['cit-recv-001'],
    },
    {
      step_id: 'step-2',
      ordinal: 2,
      text: 'Log any exceptions before stocking.',
      citation_ids: [],
    },
  ],
}

function renderSteps(overrides: Partial<ProcedureResult> = {}, onActivateCitation = vi.fn()) {
  const result = { ...procedureResult, ...overrides }
  const citationIndex = buildCitationIndex([result.steps.flatMap((s) => s.citation_ids)])
  return render(
    <AnswerSteps
      procedureResult={result}
      citations={citations}
      citationIndex={citationIndex}
      activeCitationId={null}
      onActivateCitation={onActivateCitation}
    />,
  )
}

describe('AnswerSteps', () => {
  it('renders one ordered list item per step', () => {
    renderSteps()
    const list = document.querySelector('.answer-steps__list')
    expect(list).not.toBeNull()
    expect(within(list as HTMLElement).getAllByRole('listitem')).toHaveLength(2)
  })

  it('shows the plain-language explanation by default when one exists', () => {
    renderSteps()
    expect(screen.getByText('Check the slip matches what was ordered.')).toBeInTheDocument()
  })

  it('falls back to the original text when a step has no explanation', () => {
    renderSteps()
    expect(screen.getByText('Log any exceptions before stocking.')).toBeInTheDocument()
  })

  it('reveals the original source text for every step when toggled', async () => {
    renderSteps()
    await userEvent.click(screen.getByRole('button', { name: /show original/i }))
    expect(screen.getByText('Verify the packing slip against the purchase order.')).toBeInTheDocument()
    expect(screen.queryByText('Check the slip matches what was ordered.')).not.toBeInTheDocument()
  })

  it('shows a warning next to the step it applies to', () => {
    renderSteps()
    expect(screen.getByText(/do not stock a pallet/i)).toBeInTheDocument()
  })

  it('shows a warning that applies to no listed step in a general section instead of dropping it', () => {
    renderSteps({
      warnings: [
        {
          warning_id: 'warn-general',
          text: 'General caution applies throughout.',
          applies_to_step_ids: ['step-does-not-exist'],
          citation_ids: [],
        },
      ],
    })
    expect(screen.getByText('General caution applies throughout.')).toBeInTheDocument()
  })

  it('shows prerequisites before the steps', () => {
    renderSteps()
    expect(screen.getByText('Have the delivery note ready.')).toBeInTheDocument()
  })

  it('shows the overall explanation when present', () => {
    renderSteps({ explanation: 'Overall, follow the receiving checklist.' })
    expect(screen.getByText('Overall, follow the receiving checklist.')).toBeInTheDocument()
  })

  it('discloses when the plain-language draft fell back to original wording', () => {
    renderSteps({ fallback_used: true })
    expect(screen.getByText(/didn.t pass a preservation check/i)).toBeInTheDocument()
  })

  it('renders a numbered citation chip that resolves and activates the right citation', async () => {
    const onActivateCitation = vi.fn()
    renderSteps({}, onActivateCitation)
    const chip = screen.getByRole('button', { name: /dock intake/i })
    expect(chip).toHaveTextContent('1')
    await userEvent.click(chip)
    expect(onActivateCitation).toHaveBeenCalledWith(citations[0])
  })
})
