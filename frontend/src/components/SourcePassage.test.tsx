import { describe, expect, it } from 'vitest'
import { render, screen } from '@testing-library/react'
import { SourcePassage } from './SourcePassage'

describe('SourcePassage', () => {
  it('renders the title and text of a quoted excerpt', () => {
    render(<SourcePassage title="Receiving — Dock Intake" text="Verify the packing slip." isFullText={false} />)
    expect(screen.getByText('Receiving — Dock Intake')).toBeInTheDocument()
    expect(screen.getByText('Verify the packing slip.')).toBeInTheDocument()
    expect(screen.getByText(/quoted excerpt/i)).toBeInTheDocument()
  })

  it('labels full section text distinctly from a quoted excerpt', () => {
    render(<SourcePassage title="Receiving" text="Full text." isFullText isCurrent />)
    expect(screen.getByText(/full section/i)).toBeInTheDocument()
  })

  it('flags a full section as historical when it is not the current version', () => {
    render(<SourcePassage title="Receiving" text="Full text." isFullText isCurrent={false} />)
    expect(screen.getByText(/historical/i)).toBeInTheDocument()
  })

  it('does not show a historical flag for the current version', () => {
    render(<SourcePassage title="Receiving" text="Full text." isFullText isCurrent />)
    expect(screen.queryByText(/historical/i)).not.toBeInTheDocument()
  })
})
