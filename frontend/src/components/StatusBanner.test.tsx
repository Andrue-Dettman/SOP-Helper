import { describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { StatusBanner } from './StatusBanner'

describe('StatusBanner', () => {
  it('renders the insufficient-evidence message', () => {
    render(<StatusBanner variant="insufficient_evidence" />)
    expect(screen.getByText(/not enough evidence/i)).toBeInTheDocument()
  })

  it('renders the temporarily-unavailable message', () => {
    render(<StatusBanner variant="temporarily_unavailable" />)
    expect(screen.getByText(/temporarily unavailable/i)).toBeInTheDocument()
  })

  it('renders the network-error message', () => {
    render(<StatusBanner variant="network_error" />)
    expect(screen.getByText(/couldn.t reach/i)).toBeInTheDocument()
  })

  it('prefers a server-supplied message when given', () => {
    render(<StatusBanner variant="temporarily_unavailable" message="The inventory database is down." />)
    expect(screen.getByText('The inventory database is down.')).toBeInTheDocument()
  })

  it('calls onRetry when the retry button is activated', async () => {
    const onRetry = vi.fn()
    render(<StatusBanner variant="network_error" onRetry={onRetry} />)
    await userEvent.click(screen.getByRole('button', { name: /retry/i }))
    expect(onRetry).toHaveBeenCalledTimes(1)
  })

  it('omits the retry button when onRetry is not provided', () => {
    render(<StatusBanner variant="network_error" />)
    expect(screen.queryByRole('button', { name: /retry/i })).not.toBeInTheDocument()
  })
})
