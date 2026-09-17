import { useEffect, useRef } from 'react'
import './ChatThread.css'
import { LoadingIndicator } from './LoadingIndicator'
import { MessageBubble } from './MessageBubble'
import type { ConversationTurn } from '../lib/conversation'
import type { Citation, ClarificationChoice } from '../api/types'

export interface ChatThreadProps {
  turns: ConversationTurn[]
  isLoading: boolean
  activeCitationId: string | null
  onActivateCitation: (citation: Citation) => void
  onSelectChoice: (choice: ClarificationChoice) => void
  onSubmitQuantity: (quantity: number) => void
  onRetry: () => void
}

export function ChatThread({
  turns,
  isLoading,
  activeCitationId,
  onActivateCitation,
  onSelectChoice,
  onSubmitQuantity,
  onRetry,
}: ChatThreadProps) {
  const bubbleElements = useRef(new Map<string, HTMLDivElement>())
  const lastSeenTurnId = useRef<string | null>(null)

  useEffect(() => {
    const lastTurn = turns[turns.length - 1]
    if (!lastTurn || lastTurn.id === lastSeenTurnId.current) {
      return
    }
    lastSeenTurnId.current = lastTurn.id
    // Only a new answer (not the user's own message) claims focus. Skip it
    // if the user has already started typing the next question — an empty,
    // merely-focused textarea (the normal post-submit state) doesn't count.
    const active = document.activeElement
    const isComposingNextMessage =
      active instanceof HTMLTextAreaElement && active.value.trim() !== ''
    if (lastTurn.role === 'user' || isComposingNextMessage) {
      return
    }
    bubbleElements.current.get(lastTurn.id)?.focus()
  }, [turns])

  return (
    <div className="chat-thread" role="log" aria-live="polite" aria-relevant="additions">
      {turns.map((turn) => (
        <MessageBubble
          key={turn.id}
          turn={turn}
          activeCitationId={activeCitationId}
          onActivateCitation={onActivateCitation}
          onSelectChoice={onSelectChoice}
          onSubmitQuantity={onSubmitQuantity}
          onRetry={onRetry}
          bubbleRef={(element) => {
            if (element) {
              bubbleElements.current.set(turn.id, element)
            } else {
              bubbleElements.current.delete(turn.id)
            }
          }}
        />
      ))}
      {isLoading && <LoadingIndicator />}
    </div>
  )
}
