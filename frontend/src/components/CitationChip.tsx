import './CitationChip.css'
import type { Citation } from '../api/types'

export interface CitationChipProps {
  citation: Citation
  index: number
  isActive: boolean
  onActivate: (citation: Citation) => void
}

export function CitationChip({ citation, index, isActive, onActivate }: CitationChipProps) {
  return (
    <button
      type="button"
      className="citation-chip"
      aria-pressed={isActive}
      aria-label={`Source ${index}: ${citation.title}`}
      onClick={() => onActivate(citation)}
    >
      {index}
    </button>
  )
}
