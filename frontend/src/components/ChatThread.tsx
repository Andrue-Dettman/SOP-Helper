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
        />
      ))}
      {isLoading && <LoadingIndicator />}
    </div>
  )
}
