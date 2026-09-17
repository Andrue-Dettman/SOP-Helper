import { describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { ClarificationPrompt } from './ClarificationPrompt'
import type { Clarification } from '../api/types'

const assemblyClarification: Clarification = {
  kind: 'assembly',
  question: '"Kit A" matches more than one assembly. Which one do you mean?',
  choices: [
    { id: 'asm-kit-a-std', label: 'Kit A — Standard' },
    { id: 'asm-kit-a-hd', label: 'Kit A — Heavy Duty' },
  ],
}

const quantityClarification: Clarification = {
  kind: 'quantity',
  question: 'How many units do you want to build?',
  choices: [],
}

describe('ClarificationPrompt', () => {
  it('renders the question and a button per choice', () => {
    render(<ClarificationPrompt clarification={assemblyClarification} onSelectChoice={vi.fn()} />)
    expect(screen.getByText(assemblyClarification.question)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Kit A — Standard' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Kit A — Heavy Duty' })).toBeInTheDocument()
  })

  it('calls onSelectChoice with the chosen option', async () => {
    const onSelectChoice = vi.fn()
    render(<ClarificationPrompt clarification={assemblyClarification} onSelectChoice={onSelectChoice} />)
    await userEvent.click(screen.getByRole('button', { name: 'Kit A — Heavy Duty' }))
    expect(onSelectChoice).toHaveBeenCalledWith(assemblyClarification.choices[1])
  })

  it('renders a quantity input instead of choice buttons when choices are empty', () => {
    render(
      <ClarificationPrompt
        clarification={quantityClarification}
        onSelectChoice={vi.fn()}
        onSubmitQuantity={vi.fn()}
      />,
    )
    expect(screen.getByRole('spinbutton', { name: /quantity/i })).toBeInTheDocument()
  })

  it('submits a valid quantity and rejects an empty one', async () => {
    const onSubmitQuantity = vi.fn()
    render(
      <ClarificationPrompt
        clarification={quantityClarification}
        onSelectChoice={vi.fn()}
        onSubmitQuantity={onSubmitQuantity}
      />,
    )
    await userEvent.click(screen.getByRole('button', { name: /submit/i }))
    expect(onSubmitQuantity).not.toHaveBeenCalled()

    await userEvent.type(screen.getByRole('spinbutton', { name: /quantity/i }), '20')
    await userEvent.click(screen.getByRole('button', { name: /submit/i }))
    expect(onSubmitQuantity).toHaveBeenCalledWith(20)
  })
})
