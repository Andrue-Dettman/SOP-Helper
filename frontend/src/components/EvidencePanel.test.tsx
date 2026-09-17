import { describe, expect, it, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { EvidencePanel } from './EvidencePanel'
import type { ApiClient } from '../api/client'
import type { Citation, SopSection } from '../api/types'

const citation: Citation = {
  citation_id: 'cit-recv-001',
  document_id: 'sop-receiving',
  version: '3',
  section_id: 'sec-2',
  title: 'Receiving Deliveries — Dock Intake',
  quoted_text: 'Verify the packing slip.',
  source_uri: '/sops/sop-receiving/sections/sec-2?version=3',
}

const fullSection: SopSection = {
  document_id: 'sop-receiving',
  version: '3',
  section_id: 'sec-2',
  title: 'Receiving Deliveries — Dock Intake',
  text: 'Verify the packing slip against the purchase order. Route to the dock lane.',
  source_uri: '/sops/sop-receiving/sections/sec-2?version=3',
  is_current: true,
}

function fakeClient(overrides: Partial<ApiClient> = {}): ApiClient {
  return {
    sendChat: vi.fn(),
    getSection: vi.fn().mockResolvedValue(fullSection),
    ...overrides,
  }
}

describe('EvidencePanel', () => {
  it('shows a placeholder when no citation is active', () => {
    render(<EvidencePanel citation={null} apiClient={fakeClient()} onClose={vi.fn()} />)
    expect(screen.getByText(/select a source/i)).toBeInTheDocument()
  })

  it('shows the quoted excerpt for the active citation', () => {
    render(<EvidencePanel citation={citation} apiClient={fakeClient()} onClose={vi.fn()} />)
    expect(screen.getByText('Verify the packing slip.')).toBeInTheDocument()
  })

  it('moves focus into the panel when a citation becomes active', () => {
    render(<EvidencePanel citation={citation} apiClient={fakeClient()} onClose={vi.fn()} />)
    expect(screen.getByRole('region', { name: /evidence/i })).toHaveFocus()
  })

  it('fetches and shows the full section text on request', async () => {
    const client = fakeClient()
    render(<EvidencePanel citation={citation} apiClient={client} onClose={vi.fn()} />)
    await userEvent.click(screen.getByRole('button', { name: /view full section/i }))
    expect(client.getSection).toHaveBeenCalledWith('sop-receiving', 'sec-2', '3')
    await waitFor(() => expect(screen.getByText(/route to the dock lane/i)).toBeInTheDocument())
  })

  it('reports when a version has no full section instead of substituting one', async () => {
    const client = fakeClient({ getSection: vi.fn().mockResolvedValue(null) })
    render(<EvidencePanel citation={citation} apiClient={client} onClose={vi.fn()} />)
    await userEvent.click(screen.getByRole('button', { name: /view full section/i }))
    await waitFor(() => expect(screen.getByText(/not available/i)).toBeInTheDocument())
  })

  it('reports unavailable rather than leaving the loading state stuck when the request throws', async () => {
    const client = fakeClient({ getSection: vi.fn().mockRejectedValue(new Error('server error')) })
    render(<EvidencePanel citation={citation} apiClient={client} onClose={vi.fn()} />)
    await userEvent.click(screen.getByRole('button', { name: /view full section/i }))
    await waitFor(() => expect(screen.getByText(/not available/i)).toBeInTheDocument())
  })

  it('calls onClose when Escape is pressed inside the panel', async () => {
    const onClose = vi.fn()
    render(<EvidencePanel citation={citation} apiClient={fakeClient()} onClose={onClose} />)
    await userEvent.keyboard('{Escape}')
    expect(onClose).toHaveBeenCalledTimes(1)
  })
})
