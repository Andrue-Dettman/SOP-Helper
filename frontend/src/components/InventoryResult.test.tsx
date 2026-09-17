import { describe, expect, it } from 'vitest'
import { render, screen } from '@testing-library/react'
import { InventoryResult } from './InventoryResult'
import type { BuildInventoryResult, StockInventoryResult } from '../api/types'

const readyBuild: BuildInventoryResult = {
  kind: 'build',
  state: 'ok',
  snapshot: { snapshot_id: 'snap-1', captured_at: '2026-09-14T08:00:00Z' },
  assembly_id: 'ASM-0001',
  requested_units: 20,
  ready: true,
  components: [{ part_id: 'PRT-0001', per_assembly: 2, required: 40, available: 120, shortage: 0 }],
}

const notReadyBuild: BuildInventoryResult = {
  ...readyBuild,
  ready: false,
  components: [{ part_id: 'PRT-0002', per_assembly: 1, required: 20, available: 12, shortage: 8 }],
}

const unknownReadyBuild: BuildInventoryResult = {
  ...readyBuild,
  state: 'incomplete',
  ready: null,
  components: [{ part_id: 'PRT-0003', per_assembly: 1, required: 20, available: null, shortage: null }],
}

const stockResult: StockInventoryResult = {
  kind: 'stock',
  state: 'ok',
  snapshot: { snapshot_id: 'snap-1', captured_at: '2026-09-14T08:00:00Z' },
  matches: [{ part_id: 'PRT-0002', label: 'Side Panel A', available: 32, unit: 'each' }],
}

describe('InventoryResult', () => {
  it('shows a ready banner and the assembly/quantity for a ready build', () => {
    render(<InventoryResult result={readyBuild} />)
    expect(screen.getByText('Ready')).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: /asm-0001.*20 units/i })).toBeInTheDocument()
  })

  it('shows a distinct not-ready banner for a build with a known shortage', () => {
    render(<InventoryResult result={notReadyBuild} />)
    expect(screen.getByText(/not ready/i)).toBeInTheDocument()
  })

  it('shows an unknown-readiness banner rather than claiming ready or not ready', () => {
    render(<InventoryResult result={unknownReadyBuild} />)
    expect(screen.getByText(/readiness unknown/i)).toBeInTheDocument()
  })

  it('shows the snapshot id so the data age is visible', () => {
    render(<InventoryResult result={readyBuild} />)
    expect(screen.getByText(/snap-1/)).toBeInTheDocument()
  })

  it('omits the snapshot line when no snapshot is available', () => {
    render(<InventoryResult result={{ ...readyBuild, snapshot: null }} />)
    expect(screen.queryByText(/data snapshot/i)).not.toBeInTheDocument()
  })

  it('renders stock matches for a stock-kind result', () => {
    render(<InventoryResult result={stockResult} />)
    expect(screen.getByText('Side Panel A')).toBeInTheDocument()
    expect(screen.getByText(/32/)).toBeInTheDocument()
  })
})
