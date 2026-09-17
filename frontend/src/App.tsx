import { useRef, useState } from 'react'
import './App.css'
import { ChatInput } from './components/ChatInput'
import { ChatThread } from './components/ChatThread'
import { EvidencePanel } from './components/EvidencePanel'
import { FictionalDataBanner } from './components/FictionalDataBanner'
import { getApiClient } from './api/client'
import { buildHistory } from './lib/conversation'
import { nextId } from './lib/id'
import type { ApiClient } from './api/client'
import type { ConversationTurn } from './lib/conversation'
import type { ChatSelection, Citation, ClarificationChoice, ClarificationKind } from './api/types'

export interface AppProps {
  apiClient?: ApiClient
}

function App({ apiClient: apiClientProp }: AppProps) {
  const [apiClient] = useState<ApiClient>(() => apiClientProp ?? getApiClient())
  const [turns, setTurns] = useState<ConversationTurn[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [activeCitation, setActiveCitation] = useState<Citation | null>(null)
  const citationTriggerRef = useRef<HTMLElement | null>(null)
  // Selection resolved through a clarification choice (e.g. a disambiguated
  // assembly) carries forward to later requests in this simplified,
  // fixture-driven flow, until a fresh clarification replaces it.
  const [carrySelection, setCarrySelection] = useState<ChatSelection | undefined>(undefined)
  const [lastRequest, setLastRequest] = useState<{ text: string; selection?: ChatSelection } | null>(null)

  async function runRequest(
    text: string,
    selection: ChatSelection | undefined,
    historyBase: ConversationTurn[],
    mode: 'append' | 'replace-last',
  ) {
    setIsLoading(true)
    try {
      const response = await apiClient.sendChat({ message: text, history: buildHistory(historyBase), selection })
      const turn: ConversationTurn = { id: nextId(), role: 'assistant', response }
      setTurns((prev) => (mode === 'append' ? [...prev, turn] : [...prev.slice(0, -1), turn]))
    } catch (error) {
      const turn: ConversationTurn = {
        id: nextId(),
        role: 'assistant-error',
        message: error instanceof Error ? error.message : 'Request failed',
      }
      setTurns((prev) => (mode === 'append' ? [...prev, turn] : [...prev.slice(0, -1), turn]))
    } finally {
      setIsLoading(false)
    }
  }

  function sendMessage(text: string, selection?: ChatSelection) {
    const effectiveSelection = selection ?? carrySelection
    const historyBase = turns
    setLastRequest({ text, selection: effectiveSelection })
    setTurns((prev) => [...prev, { id: nextId(), role: 'user', text }])
    void runRequest(text, effectiveSelection, historyBase, 'append')
  }

  function handleSelectChoice(choice: ClarificationChoice) {
    const lastTurn = turns[turns.length - 1]
    const kind: ClarificationKind | undefined =
      lastTurn?.role === 'assistant' ? (lastTurn.response.clarification?.kind ?? undefined) : undefined
    const selection: ChatSelection | undefined =
      kind === 'assembly' ? { assembly_id: choice.id } : kind === 'part' ? { part_id: choice.id } : undefined
    if (selection) {
      setCarrySelection(selection)
    }
    sendMessage(choice.label, selection ?? carrySelection)
  }

  function handleSubmitQuantity(quantity: number) {
    sendMessage(String(quantity), carrySelection)
  }

  function handleRetry() {
    if (!lastRequest) return
    const historyBase = turns.slice(0, -1)
    void runRequest(lastRequest.text, lastRequest.selection, historyBase, 'replace-last')
  }

  function handleActivateCitation(citation: Citation) {
    citationTriggerRef.current = document.activeElement instanceof HTMLElement ? document.activeElement : null
    setActiveCitation(citation)
  }

  function handleCloseEvidence() {
    setActiveCitation(null)
    citationTriggerRef.current?.focus()
    citationTriggerRef.current = null
  }

  return (
    <div className="app-shell">
      <FictionalDataBanner />
      <header className="app-shell__header">
        <h1>Warehouse Procedure &amp; Inventory Assistant</h1>
      </header>
      <div className="app-shell__body">
        <div className="app-shell__chat">
          <ChatThread
            turns={turns}
            isLoading={isLoading}
            activeCitationId={activeCitation?.citation_id ?? null}
            onActivateCitation={handleActivateCitation}
            onSelectChoice={handleSelectChoice}
            onSubmitQuantity={handleSubmitQuantity}
            onRetry={handleRetry}
          />
          <ChatInput onSend={(text) => sendMessage(text)} />
        </div>
        <aside className="app-shell__evidence" aria-label="Evidence panel region">
          <EvidencePanel citation={activeCitation} apiClient={apiClient} onClose={handleCloseEvidence} />
        </aside>
      </div>
    </div>
  )
}

export default App
