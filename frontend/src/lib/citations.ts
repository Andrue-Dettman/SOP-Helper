import type { Citation } from '../api/types'

/**
 * Maps stable citation IDs to their full Citation objects. IDs with no
 * matching citation are dropped rather than rendered as a broken or
 * fabricated link (see CONTRACTS.md: "Unknown citation IDs cannot become
 * valid links").
 */
/**
 * Assigns each citation ID a stable 1-based number by first appearance
 * across every list given (answer-level ids, then each step's ids, in
 * order), so the same citation shows the same chip number everywhere it
 * is referenced in one answer.
 */
export function buildCitationIndex(idLists: string[][]): Map<string, number> {
  const index = new Map<string, number>()
  for (const ids of idLists) {
    for (const id of ids) {
      if (!index.has(id)) {
        index.set(id, index.size + 1)
      }
    }
  }
  return index
}

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
