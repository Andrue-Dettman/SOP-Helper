import type { Citation } from '../api/types'

/**
 * Maps stable citation IDs to their full Citation objects. IDs with no
 * matching citation are dropped rather than rendered as a broken or
 * fabricated link (see CONTRACTS.md: "Unknown citation IDs cannot become
 * valid links").
 */
export function resolveCitations(ids: string[], citations: Citation[]): Citation[] {
  const byId = new Map(citations.map((citation) => [citation.citation_id, citation]))
  const resolved: Citation[] = []
  for (const id of ids) {
    const citation = byId.get(id)
    if (citation) {
      resolved.push(citation)
    }
  }
  return resolved
}
