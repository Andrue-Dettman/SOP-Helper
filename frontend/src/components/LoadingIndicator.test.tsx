import { describe, expect, it } from 'vitest'
import { render, screen } from '@testing-library/react'
import { LoadingIndicator } from './LoadingIndicator'

describe('LoadingIndicator', () => {
  it('announces the pending request politely', () => {
    render(<LoadingIndicator />)
    const status = screen.getByRole('status')
    expect(status).toHaveTextContent(/thinking/i)
    expect(status).toHaveAttribute('aria-live', 'polite')
  })
})
