// Hand-authored from docs/CONTRACTS.md v1. Provisional until G1 publishes
// generated types from the frozen OpenAPI schema (see contract gaps in
// docs/agent-reports/C2-frontend.md). Keep in sync manually until then.

export type ChatStatus =
  | 'answered'
  | 'needs_clarification'
  | 'insufficient_evidence'
  | 'temporarily_unavailable'

export type DataMode = 'synthetic'

export interface ChatHistoryMessage {
  role: 'user' | 'assistant'
  content: string
}

export interface ProcedureSelection {
  document_id: string
  version: string
  section_id: string
}

export interface ChatSelection {
  assembly_id?: string
  part_id?: string
  procedure?: ProcedureSelection
}

export interface ChatRequest {
  message: string
  history?: ChatHistoryMessage[]
  selection?: ChatSelection
}

export interface Citation {
  citation_id: string
  document_id: string
  version: string
  section_id: string
  title: string
  quoted_text: string
  source_uri: string
}

export interface ProcedureStep {
  step_id: string
  order: number
  original_text: string
  explanation?: string
  is_mandatory: boolean
  quantity?: string
  warning?: string
  citation_ids: string[]
}

export interface ProcedureResult {
  state: 'complete' | 'incomplete'
  document_id: string
  version: string
  section_id: string
  title: string
  is_current: boolean
  steps: ProcedureStep[]
}

export interface InventorySnapshot {
  snapshot_id: string
  captured_at: string
}

export interface BuildComponent {
  part_id: string
  label: string
  per_assembly: number
  required: number
  available: number | null
  shortage: number | null
}

export interface BuildInventoryResult {
  kind: 'build'
  state: 'ok' | 'incomplete' | 'not_found' | 'unavailable'
  snapshot: InventorySnapshot
  assembly_id: string
  assembly_label: string
  requested_units: number
  ready: boolean | null
  components: BuildComponent[]
}

export interface StockMatch {
  part_id: string
  label: string
  quantity: number | null
  unit: string
}

export interface StockInventoryResult {
  kind: 'stock'
  state: 'ok' | 'ambiguous' | 'not_found' | 'incomplete' | 'unavailable'
  snapshot: InventorySnapshot
  matches: StockMatch[]
}

export type InventoryResult = BuildInventoryResult | StockInventoryResult

export type ClarificationKind = 'assembly' | 'part' | 'quantity' | 'procedure'

export interface ClarificationChoice {
  id: string
  label: string
}

export interface Clarification {
  kind: ClarificationKind
  question: string
  choices: ClarificationChoice[]
}

export interface ApiError {
  code: string
  message: string
  retryable: boolean
}

export interface ChatResponse {
  answer: string | null
  answer_citation_ids: string[]
  status: ChatStatus
  citations: Citation[]
  procedure_result: ProcedureResult | null
  inventory_result: InventoryResult | null
  clarification: Clarification | null
  error: ApiError | null
  trace_id: string
  data_mode: DataMode
}

export interface SopSection {
  document_id: string
  version: string
  section_id: string
  title: string
  text: string
  source_uri: string
  is_current: boolean
}

export interface AssemblyOption {
  id: string
  label: string
}
