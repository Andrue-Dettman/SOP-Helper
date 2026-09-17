import { describe, expect, it } from 'vitest'
import { render, screen, within } from '@testing-library/react'
import { ComponentTable } from './ComponentTable'
import type { BuildComponent } from '../api/types'

const components: BuildComponent[] = [
  { part_id: 'PRT-0001', per_assembly: 2, required: 40, available: 120, shortage: 0 },
  { part_id: 'PRT-0002', per_assembly: 1, required: 20, available: 12, shortage: 8 },
]

describe('ComponentTable', () => {
  it('lists every component with its required, available, and shortage figures', () => {
    render(<ComponentTable components={components} />)
    const rows = screen.getAllByRole('row')
    // header + 2 data rows
    expect(rows).toHaveLength(3)
    const shortRow = within(rows[2])
    expect(shortRow.getByText('PRT-0002')).toBeInTheDocument()
    expect(shortRow.getByText('20')).toBeInTheDocument()
    expect(shortRow.getByText('12')).toBeInTheDocument()
    expect(shortRow.getByText('8')).toBeInTheDocument()
  })

  it('renders a null available/shortage value as unknown rather than zero', () => {
    render(
      <ComponentTable
        components={[{ part_id: 'PRT-0003', per_assembly: 1, required: 5, available: null, shortage: null }]}
      />,
    )
    expect(screen.getAllByText('Unknown')).toHaveLength(2)
  })

  it('flags a component with a real shortage distinctly from one with none', () => {
    render(<ComponentTable components={components} />)
    const rows = screen.getAllByRole('row')
    expect(rows[1]).not.toHaveClass('component-table__row--short')
    expect(rows[2]).toHaveClass('component-table__row--short')
  })
})
