import { describe, expect, it } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import App from './App'
import { createMockClient } from './api/client'

function renderApp() {
  return render(<App apiClient={createMockClient()} />)
}

async function sendMessage(text: string) {
  const textbox = screen.getByRole('textbox', { name: /ask a question/i })
  await userEvent.type(textbox, `${text}{Enter}`)
}

describe('App', () => {
  it('answers a delivery-procedure question end to end', async () => {
    renderApp()
    await sendMessage('How do I receive a delivery?')

    expect(screen.getByText('How do I receive a delivery?')).toBeInTheDocument()
    await waitFor(() =>
      expect(
        screen.getByText(/verify the packing slip against the purchase order/i),
      ).toBeInTheDocument(),
    )
  })

  it('resolves an ambiguous assembly through the clarification prompt', async () => {
    renderApp()
    await sendMessage('Can we assemble 20 units of Kit A?')

    const choice = await screen.findByRole('button', { name: /kit a — standard/i })
    await userEvent.click(choice)

    await waitFor(() => expect(screen.getByText('Ready')).toBeInTheDocument())
  })

  it('shows a citation passage in the evidence panel when its chip is activated', async () => {
    renderApp()
    await sendMessage('How do I receive a delivery?')

    await waitFor(() => expect(screen.getAllByRole('button', { name: /dock intake/i }).length).toBeGreaterThan(0))
    const [chip] = screen.getAllByRole('button', { name: /dock intake/i })
    await userEvent.click(chip)

    expect(
      screen.getByText('Verify the packing slip against the purchase order before opening any pallet. Route confirmed deliveries to the assigned dock lane.'),
    ).toBeInTheDocument()
  })

  it('returns focus to the triggering chip when Escape closes the evidence panel', async () => {
    renderApp()
    await sendMessage('How do I receive a delivery?')

    await waitFor(() => expect(screen.getAllByRole('button', { name: /dock intake/i }).length).toBeGreaterThan(0))
    const [chip] = screen.getAllByRole('button', { name: /dock intake/i })
    await userEvent.click(chip)
    await waitFor(() => expect(screen.getByRole('region', { name: 'Evidence' })).toHaveFocus())

    await userEvent.keyboard('{Escape}')
    expect(chip).toHaveFocus()
  })

  it('shows a retry action on a temporarily-unavailable response and recovers', async () => {
    renderApp()
    await sendMessage('The system seems unavailable')

    const retryButton = await screen.findByRole('button', { name: /retry/i })
    await userEvent.click(retryButton)

    // Same trigger text still resolves to the same fixture; retry replaces the failed turn.
    await waitFor(() => expect(screen.getAllByRole('button', { name: /retry/i })).toHaveLength(1))
  })
})
