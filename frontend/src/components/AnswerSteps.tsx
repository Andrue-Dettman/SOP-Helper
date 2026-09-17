import { useState } from 'react'
import { AlertTriangle } from 'lucide-react'
import './AnswerSteps.css'
import { CitationChip } from './CitationChip'
import { resolveCitations } from '../lib/citations'
import type { Citation, ProcedureResult, WarningBlock } from '../api/types'

export interface AnswerStepsProps {
  procedureResult: ProcedureResult
  citations: Citation[]
  citationIndex: Map<string, number>
  activeCitationId: string | null
  onActivateCitation: (citation: Citation) => void
}

function renderCitationChips(
  ids: string[],
  citations: Citation[],
  citationIndex: Map<string, number>,
  activeCitationId: string | null,
  onActivateCitation: (citation: Citation) => void,
) {
  return resolveCitations(ids, citations).map((citation) => (
    <CitationChip
      key={citation.citation_id}
      citation={citation}
      index={citationIndex.get(citation.citation_id) ?? 0}
      isActive={citation.citation_id === activeCitationId}
      onActivate={onActivateCitation}
    />
  ))
}

export function AnswerSteps({
  procedureResult,
  citations,
  citationIndex,
  activeCitationId,
  onActivateCitation,
}: AnswerStepsProps) {
  const [showOriginal, setShowOriginal] = useState(false)
  const steps = [...procedureResult.steps].sort((a, b) => a.ordinal - b.ordinal)
  const stepIds = new Set(steps.map((step) => step.step_id))
  const generalWarnings = procedureResult.warnings.filter(
    (warning) => !warning.applies_to_step_ids.some((id) => stepIds.has(id)),
  )

  function warningsFor(stepId: string): WarningBlock[] {
    return procedureResult.warnings.filter((warning) => warning.applies_to_step_ids.includes(stepId))
  }

  const chips = (ids: string[]) =>
    renderCitationChips(ids, citations, citationIndex, activeCitationId, onActivateCitation)

  return (
    <div className="answer-steps">
      {procedureResult.explanation && <p className="answer-steps__intro">{procedureResult.explanation}</p>}

      {procedureResult.fallback_used && (
        <p className="answer-steps__fallback-note">
          The simplified wording didn't pass a preservation check, so the original procedure text is shown below.
        </p>
      )}

      {procedureResult.prerequisites.length > 0 && (
        <div className="answer-steps__prerequisites">
          <p className="answer-steps__prerequisites-heading">Before you start</p>
          <ul>
            {procedureResult.prerequisites.map((prerequisite) => (
              <li key={prerequisite.id}>
                {prerequisite.text}
                {chips(prerequisite.citation_ids)}
              </li>
            ))}
          </ul>
        </div>
      )}

      {generalWarnings.map((warning) => (
        <p key={warning.warning_id} className="answer-steps__warning">
          <AlertTriangle aria-hidden="true" size={14} />
          {warning.text}
          {chips(warning.citation_ids)}
        </p>
      ))}

      <button
        type="button"
        className="answer-steps__toggle"
        onClick={() => setShowOriginal((value) => !value)}
      >
        {showOriginal ? 'Show plain-language explanation' : 'Show original procedure text'}
      </button>
      <ol className="answer-steps__list">
        {steps.map((step) => {
          const text = showOriginal || !step.explanation ? step.text : step.explanation
          return (
            <li key={step.step_id} className="answer-steps__item">
              <p className="answer-steps__text">
                {text}
                {chips(step.citation_ids)}
              </p>
              {warningsFor(step.step_id).map((warning) => (
                <p key={warning.warning_id} className="answer-steps__warning">
                  <AlertTriangle aria-hidden="true" size={14} />
                  {warning.text}
                  {chips(warning.citation_ids)}
                </p>
              ))}
            </li>
          )
        })}
      </ol>
    </div>
  )
}
