import { useState } from 'react'
import { AlertTriangle } from 'lucide-react'
import './AnswerSteps.css'
import { CitationChip } from './CitationChip'
import { resolveCitations } from '../lib/citations'
import type { Citation, ProcedureResult } from '../api/types'

export interface AnswerStepsProps {
  procedureResult: ProcedureResult
  citations: Citation[]
  citationIndex: Map<string, number>
  activeCitationId: string | null
  onActivateCitation: (citation: Citation) => void
}

export function AnswerSteps({
  procedureResult,
  citations,
  citationIndex,
  activeCitationId,
  onActivateCitation,
}: AnswerStepsProps) {
  const [showOriginal, setShowOriginal] = useState(false)
  const steps = [...procedureResult.steps].sort((a, b) => a.order - b.order)

  return (
    <div className="answer-steps">
      <button
        type="button"
        className="answer-steps__toggle"
        onClick={() => setShowOriginal((value) => !value)}
      >
        {showOriginal ? 'Show plain-language explanation' : 'Show original procedure text'}
      </button>
      <ol className="answer-steps__list">
        {steps.map((step) => {
          const text = showOriginal || !step.explanation ? step.original_text : step.explanation
          const stepCitations = resolveCitations(step.citation_ids, citations)
          return (
            <li key={step.step_id} className="answer-steps__item">
              <p className="answer-steps__text">
                {text}
                {stepCitations.map((citation) => (
                  <CitationChip
                    key={citation.citation_id}
                    citation={citation}
                    index={citationIndex.get(citation.citation_id) ?? 0}
                    isActive={citation.citation_id === activeCitationId}
                    onActivate={onActivateCitation}
                  />
                ))}
              </p>
              <p className="answer-steps__meta">
                {step.is_mandatory && <span className="answer-steps__tag">Required</span>}
                {step.quantity && <span className="answer-steps__tag">{step.quantity}</span>}
              </p>
              {step.warning && (
                <p className="answer-steps__warning">
                  <AlertTriangle aria-hidden="true" size={14} />
                  {step.warning}
                </p>
              )}
            </li>
          )
        })}
      </ol>
    </div>
  )
}
