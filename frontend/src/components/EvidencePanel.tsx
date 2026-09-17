import { useEffect, useRef, useState } from 'react'
import { ExternalLink } from 'lucide-react'
import './EvidencePanel.css'
import { SourcePassage } from './SourcePassage'
import { LoadingIndicator } from './LoadingIndicator'
import type { ApiClient } from '../api/client'
import type { Citation, SopSection } from '../api/types'

export interface EvidencePanelProps {
  citation: Citation | null
  apiClient: ApiClient
  onClose: () => void
}

type FullSectionState =
  | { status: 'idle' }
  | { status: 'loading' }
  | { status: 'loaded'; section: SopSection }
  | { status: 'unavailable' }

export function EvidencePanel({ citation, apiClient, onClose }: EvidencePanelProps) {
  const panelRef = useRef<HTMLElement>(null)
  const [fullSection, setFullSection] = useState<FullSectionState>({ status: 'idle' })

  useEffect(() => {
    setFullSection({ status: 'idle' })
    if (citation) {
      panelRef.current?.focus()
    }
  }, [citation])

  async function handleViewFullSection() {
    if (!citation) return
    setFullSection({ status: 'loading' })
    try {
      const section = await apiClient.getSection(citation.document_id, citation.section_id, citation.version)
      setFullSection(section ? { status: 'loaded', section } : { status: 'unavailable' })
    } catch {
      setFullSection({ status: 'unavailable' })
    }
  }

  return (
    <section
      ref={panelRef}
      className="evidence-panel"
      aria-label="Evidence"
      tabIndex={-1}
      onKeyDown={(event) => {
        if (event.key === 'Escape') {
          onClose()
        }
      }}
    >
      <h3 className="evidence-panel__heading">Evidence</h3>
      {!citation ? (
        <p className="evidence-panel__placeholder">Select a source chip to see its passage here.</p>
      ) : (
        <div className="evidence-panel__body">
          <SourcePassage title={citation.title} text={citation.quoted_text} isFullText={false} />

          {fullSection.status === 'idle' && (
            <button type="button" className="evidence-panel__view-full" onClick={handleViewFullSection}>
              <ExternalLink aria-hidden="true" size={14} />
              View full section
            </button>
          )}
          {fullSection.status === 'loading' && <LoadingIndicator />}
          {fullSection.status === 'loaded' && (
            <SourcePassage
              title={fullSection.section.title}
              text={fullSection.section.text}
              isFullText
              isCurrent={fullSection.section.is_current}
            />
          )}
          {fullSection.status === 'unavailable' && (
            <p className="evidence-panel__unavailable">
              The full text for this version is not available.
            </p>
          )}
        </div>
      )}
    </section>
  )
}
