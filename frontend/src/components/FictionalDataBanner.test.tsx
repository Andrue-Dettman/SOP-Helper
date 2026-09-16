import { describe, expect, it } from 'vitest'
import { render, screen } from '@testing-library/react'
import { FictionalDataBanner } from './FictionalDataBanner'

describe('FictionalDataBanner', () => {
  it('discloses that the data is fictional sample data', () => {
    render(<FictionalDataBanner />)
    expect(screen.getByText(/fictional/i)).toBeInTheDocument()
  })
})
