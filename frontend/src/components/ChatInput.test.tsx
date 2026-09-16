import { describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { ChatInput } from './ChatInput'

describe('ChatInput', () => {
  it('sends the trimmed message on Enter and clears the input', async () => {
    const onSend = vi.fn()
    render(<ChatInput onSend={onSend} />)
    const textbox = screen.getByRole('textbox', { name: /ask a question/i })
    await userEvent.type(textbox, '  How do I receive a delivery?  {Enter}')
    expect(onSend).toHaveBeenCalledWith('How do I receive a delivery?')
    expect(textbox).toHaveValue('')
  })

  it('inserts a newline on Shift+Enter instead of sending', async () => {
    const onSend = vi.fn()
    render(<ChatInput onSend={onSend} />)
    const textbox = screen.getByRole('textbox', { name: /ask a question/i })
    await userEvent.type(textbox, 'line one{Shift>}{Enter}{/Shift}line two')
    expect(onSend).not.toHaveBeenCalled()
    expect(textbox).toHaveValue('line one\nline two')
  })

  it('sends via the Send button', async () => {
    const onSend = vi.fn()
    render(<ChatInput onSend={onSend} />)
    await userEvent.type(screen.getByRole('textbox', { name: /ask a question/i }), 'hello')
    await userEvent.click(screen.getByRole('button', { name: /send/i }))
    expect(onSend).toHaveBeenCalledWith('hello')
  })

  it('does not send an empty or whitespace-only message', async () => {
    const onSend = vi.fn()
    render(<ChatInput onSend={onSend} />)
    await userEvent.type(screen.getByRole('textbox', { name: /ask a question/i }), '   {Enter}')
    expect(onSend).not.toHaveBeenCalled()
  })
})
