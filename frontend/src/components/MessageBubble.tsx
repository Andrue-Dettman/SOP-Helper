import './MessageBubble.css'
import { AnswerSteps } from './AnswerSteps'
import { CitationChip } from './CitationChip'
import { ClarificationPrompt } from './ClarificationPrompt'
import { InventoryResult } from './InventoryResult'
import { StatusBanner } from './StatusBanner'
import { buildCitationIndex, resolveCitations } from '../lib/citations'
import type { ConversationTurn } from '../lib/conversation'
import type { Citation, ClarificationChoice } from '../api/types'

export interface MessageBubbleProps {
  turn: ConversationTurn
  activeCitationId: string | null
  onActivateCitation: (citation: Citation) => void
  onSelectChoice: (choice: ClarificationChoice) => void
  onSubmitQuantity: (quantity: number) => void
  onRetry: () => void
}

export function MessageBubble({
  turn,
  activeCitationId,
  onActivateCitation,
  onSelectChoice,
  onSubmitQuantity,
  onRetry,
}: MessageBubbleProps) {
  if (turn.role === 'user') {
    return (
      <div className="message-bubble message-bubble--user">
        <p>{turn.text}</p>
      </div>
    )
  }

  if (turn.role === 'assistant-error') {
    return (
      <div className="message-bubble message-bubble--assistant">
        <StatusBanner variant="network_error" onRetry={onRetry} />
      </div>
    )
  }

  const { response } = turn

  if (response.status === 'insufficient_evidence') {
    return (
      <div className="message-bubble message-bubble--assistant">
        <StatusBanner variant="insufficient_evidence" />
      </div>
    )
  }

  if (response.status === 'temporarily_unavailable') {
    return (
      <div className="message-bubble message-bubble--assistant">
        <StatusBanner
          variant="temporarily_unavailable"
          message={response.error?.message}
          onRetry={response.error?.retryable ? onRetry : undefined}
        />
      </div>
    )
  }

  if (response.status === 'needs_clarification' && response.clarification) {
    return (
      <div className="message-bubble message-bubble--assistant">
        <ClarificationPrompt
          clarification={response.clarification}
          onSelectChoice={onSelectChoice}
          onSubmitQuantity={onSubmitQuantity}
        />
      </div>
    )
  }

  const citationIndex = buildCitationIndex([
    response.answer_citation_ids,
    ...response.procedure_result?.steps.map((step) => step.citation_ids) ?? [],
  ])
  const answerCitations = resolveCitations(response.answer_citation_ids, response.citations)

  return (
    <div className="message-bubble message-bubble--assistant">
      {response.answer && (
        <p className="message-bubble__answer">
          {response.answer}
          {answerCitations.map((citation) => (
            <CitationChip
              key={citation.citation_id}
              citation={citation}
              index={citationIndex.get(citation.citation_id) ?? 0}
              isActive={citation.citation_id === activeCitationId}
              onActivate={onActivateCitation}
            />
          ))}
        </p>
      )}
      {response.procedure_result && (
        <AnswerSteps
          procedureResult={response.procedure_result}
          citations={response.citations}
          citationIndex={citationIndex}
          activeCitationId={activeCitationId}
          onActivateCitation={onActivateCitation}
        />
      )}
      {response.inventory_result && <InventoryResult result={response.inventory_result} />}
    </div>
  )
}
