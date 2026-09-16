import { useState } from 'react'
import type { KeyboardEvent } from 'react'
import { Send } from 'lucide-react'
import './ChatInput.css'

export interface ChatInputProps {
  onSend: (message: string) => void
}

export function ChatInput({ onSend }: ChatInputProps) {
  const [value, setValue] = useState('')

  function trySend() {
    const trimmed = value.trim()
    if (trimmed === '') return
    onSend(trimmed)
    setValue('')
  }

  function handleKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault()
      trySend()
    }
  }

  return (
    <div className="chat-input">
      <textarea
        className="chat-input__textarea"
        aria-label="Ask a question"
        value={value}
        onChange={(event) => setValue(event.target.value)}
        onKeyDown={handleKeyDown}
        rows={1}
      />
      <button type="button" className="chat-input__send" onClick={trySend} aria-label="Send">
        <Send aria-hidden="true" size={16} />
        Send
      </button>
    </div>
  )
}
