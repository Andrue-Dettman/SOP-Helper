import { describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
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
  state: 'complete',
  document_id: 'sop-receiving',
  version: '3',
  section_id: 'sec-2',
  title: 'Receiving Deliveries',
  is_current: true,
  steps: [
    {
      step_id: 'step-1',
      order: 1,
      original_text: 'Verify the packing slip against the purchase order.',
      explanation: 'Check the slip matches what was ordered.',
      is_mandatory: true,
      citation_ids: ['cit-recv-001'],
    },
    {
      step_id: 'step-2',
      order: 2,
      original_text: 'Log any exceptions before stocking.',
      is_mandatory: true,
      warning: 'Do not stock a pallet with unresolved damage exceptions.',
      citation_ids: [],
    },
  ],
}

function renderSteps(onActivateCitation = vi.fn()) {
  const citationIndex = buildCitationIndex([procedureResult.steps.map((s) => s.citation_ids).flat()])
  return render(
    <AnswerSteps
      procedureResult={procedureResult}
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
    const items = screen.getAllByRole('listitem')
    expect(items).toHaveLength(2)
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

  it('keeps the mandatory warning visible regardless of toggle state', () => {
    renderSteps()
    expect(screen.getByText(/do not stock a pallet/i)).toBeInTheDocument()
  })

  it('marks a mandatory step as required in text, not color alone', () => {
    renderSteps()
    expect(screen.getAllByText(/required/i).length).toBeGreaterThan(0)
  })

  it('renders a numbered citation chip that resolves and activates the right citation', async () => {
    const onActivateCitation = vi.fn()
    renderSteps(onActivateCitation)
    const chip = screen.getByRole('button', { name: /dock intake/i })
    expect(chip).toHaveTextContent('1')
    await userEvent.click(chip)
    expect(onActivateCitation).toHaveBeenCalledWith(citations[0])
  })
})
