import { describe, expect, it } from 'vitest'
import type { Citation } from '../api/types'
import { resolveCitations } from './citations'

const citations: Citation[] = [
  {
    citation_id: 'cit-a',
    document_id: 'doc-1',
    version: '1',
    section_id: 'sec-1',
    title: 'Section A',
    quoted_text: 'Quote A',
    source_uri: '/sops/doc-1/sections/sec-1?version=1',
  },
  {
    citation_id: 'cit-b',
    document_id: 'doc-1',
    version: '1',
    section_id: 'sec-2',
    title: 'Section B',
    quoted_text: 'Quote B',
    source_uri: '/sops/doc-1/sections/sec-2?version=1',
  },
]

describe('resolveCitations', () => {
  it('returns full citation objects in the order the ids were given', () => {
    const result = resolveCitations(['cit-b', 'cit-a'], citations)
    expect(result.map((c) => c.citation_id)).toEqual(['cit-b', 'cit-a'])
  })

  it('drops ids that have no matching citation instead of fabricating one', () => {
    const result = resolveCitations(['cit-a', 'cit-unknown'], citations)
    expect(result).toEqual([citations[0]])
  })

  it('returns an empty array for no ids', () => {
    expect(resolveCitations([], citations)).toEqual([])
  })
})
