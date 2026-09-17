import { describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { CitationChip } from './CitationChip'
import type { Citation } from '../api/types'

const citation: Citation = {
  citation_id: 'cit-recv-001',
  document_id: 'sop-receiving',
  version: '3',
  section_id: 'sec-2',
  title: 'Receiving Deliveries — Dock Intake',
  quoted_text: 'Verify the packing slip.',
  source_uri: '/sops/sop-receiving/sections/sec-2?version=3',
}

describe('CitationChip', () => {
  it('shows its position number and names the source in its accessible label', () => {
    render(<CitationChip citation={citation} index={1} isActive={false} onActivate={vi.fn()} />)
    const chip = screen.getByRole('button', { name: /receiving deliveries.*dock intake/i })
    expect(chip).toHaveTextContent('1')
  })

  it('calls onActivate with the citation when clicked', async () => {
    const onActivate = vi.fn()
    render(<CitationChip citation={citation} index={1} isActive={false} onActivate={onActivate} />)
    await userEvent.click(screen.getByRole('button'))
    expect(onActivate).toHaveBeenCalledWith(citation)
  })

  it('marks itself pressed when active', () => {
    render(<CitationChip citation={citation} index={1} isActive onActivate={vi.fn()} />)
    expect(screen.getByRole('button')).toHaveAttribute('aria-pressed', 'true')
  })
})
