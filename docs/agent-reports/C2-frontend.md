## C2: Frontend and plain-language experience — planning report

### Decisions

**Layout.** Two-region shell: a chat column (question input, message history) and a persistent Evidence panel that holds the citation text and inventory result for the most recently answered turn. Desktop: side-by-side columns, each independently scrollable. Mobile: single column; the Evidence panel becomes a collapsible section directly under the answer it belongs to, expanded by default for the latest turn. No route changes — this is a one-page assistant, not a multi-page app, consistent with "no marketing landing page."

**Source viewing.** Citations render as inline numbered chips (e.g. `[1]`) inside the plain-language answer. Activating a chip moves focus into the Evidence panel and shows the quoted passage plus a "view full section" action that calls `GET /api/sops/{document_id}/sections/{section_id}`. Original text stays one action away, per the skill, rather than requiring navigation away from the answer.

**Explanation depth.** The plain-language answer is rendered as a semantic `<ol>` that preserves the backend's steps, quantities, sequence, and warnings verbatim — the UI does not re-summarize or drop warning text. A "show original procedure text" toggle reveals the source section inline for direct comparison, addressing the brief's requirement to preserve required steps/warnings when simplifying.

**Ambiguity choices.** `needs_clarification` and inventory `ambiguous` results render as a list of selectable option buttons (not a free-text re-ask). Selecting an option resends `/api/chat` with the choice folded into history and moves focus to the new answer. This keeps disambiguation deterministic and testable.

**Inventory results.** A dedicated component shows: assembly name/id, requested quantity, a readiness banner (icon + text, not color alone), a per-component table (required/available/shortage) that scrolls within its own region on narrow screens, and a snapshot id/timestamp footer so users can see the data's age.

**Keyboard behavior.** Logical top-to-bottom tab order; Enter sends, Shift+Enter inserts a newline; sending an answer moves focus to it and announces it via `aria-live="polite"`; Escape collapses an expanded Evidence panel and returns focus to the triggering chip; no focus traps anywhere.

**Responsive layout.** No horizontal page overflow at any width; tables and code-like content scroll within their own bounded region instead of the page. Verified visually via Playwright screenshots at a desktop (1280px) and mobile (375px) viewport, not by an accessibility claim.

**Error/loading states.** Distinct, clearly labeled components for: loading (pending request), `insufficient_evidence`, `temporarily_unavailable`, and client-side network/transport failure (which is not one of the backend's `status` values and needs its own path). Each has icon, text, and a retry affordance where applicable; the chat input stays usable throughout.

**Fixture-driven development.** `src/api/types.ts` mirrors `CONTRACTS.md`'s `/api/chat` and `/api/sops/.../sections/...` shapes by hand, pending OpenAPI generation. A fixture set under `frontend/tests/fixtures/` covers every `status` value, an ambiguous clarification, a ready and a not-ready inventory result, a delayed response, and a failed response. A thin fetch wrapper swaps between fixtures and a live base URL behind an env flag, so all components and Playwright tests build against fixtures before the backend exists.

### Contract gaps for G1/coordinator

1. `clarification` has no defined shape. It needs a stable list of selectable options (id + label), not just a question string, or the UI cannot render deterministic buttons.
2. No guaranteed linkage between inline citation markers in `answer` text and the `citations` array order/index — needed so chips can be generated reliably.
3. `GET /api/sops/{document_id}/sections/{section_id}` response fields are unspecified (heading text, prior/next section, version display string).
4. No standard error envelope for transport-level (4xx/5xx) failures, distinct from the modeled `temporarily_unavailable` status.
5. Unclear whether `trace_id` is meant to be user-visible (e.g., for support) or log-only.

### Components

`AppShell`, `FictionalDataBanner`, `ChatThread`, `MessageBubble`, `ChatInput`, `AnswerSteps`, `CitationChip`, `EvidencePanel`, `SourcePassage`, `ClarificationPrompt`, `InventoryResult`, `ComponentTable`, `StatusBanner` (needs_clarification/insufficient_evidence/temporarily_unavailable/network-error variants), `LoadingIndicator`. Icons from the existing lucide set only (e.g., `AlertTriangle`, `CircleCheck`, `Loader2`, `ExternalLink`).

### Ordered tasks and file ownership (all under `frontend/`, owned by C2)

1. Scaffold Vite + React + TypeScript app and package manifest.
2. Hand-author `src/api/types.ts` and fixture JSON per response state in `tests/fixtures/`.
3. Build the mock/live fetch wrapper for fixture-driven dev.
4. `ChatThread` / `MessageBubble` / `ChatInput` with keyboard behavior.
5. `AnswerSteps`, `CitationChip`, `EvidencePanel`, `SourcePassage`.
6. `ClarificationPrompt` wired to ambiguous fixtures.
7. `InventoryResult` / `ComponentTable`.
8. `StatusBanner` variants, `LoadingIndicator`, `FictionalDataBanner`.
9. Responsive pass at desktop/mobile widths; verify no overflow.
10. Playwright acceptance suite against fixtures, plus an automated accessibility scan (axe) as supporting evidence only.
11. Swap fixtures for the live API once G1's contract is frozen.

### Dependencies

Types and fixtures are provisional until G1/coordinator resolves the clarification shape, citation-to-marker linkage, and section-endpoint fields above; component structure can proceed in parallel since it targets the fixture layer, not the live API.

### Acceptance tests (Playwright, fixture-backed)

- Delivery-procedure answer: ordered steps render; citation chip opens Evidence panel with matching quoted text; warnings visible.
- Term-explanation answer: quantities/sequence/warnings match fixture text verbatim.
- Ambiguous case: two options render as buttons; selecting one resends chat and moves focus to the new answer.
- Build readiness (ready): banner shows ready, component table shortages are zero, snapshot id shown.
- Build readiness (not ready): banner is visually and textually distinct, shortages match fixture values.
- `insufficient_evidence`: explicit banner, no fabricated citations.
- `temporarily_unavailable` and network failure: distinct banners, retry action, input stays usable.
- Loading: indicator shown during a delayed fixture; no layout shift/overflow.
- Keyboard-only pass: input → send → citation chip → Evidence panel → Escape returns focus; no traps.
- Responsive screenshots at 1280px and 375px with no horizontal scroll; tables scroll within their region.

### Risks

- Contract gaps above could force rework of `EvidencePanel`/`ClarificationPrompt`; mitigated by isolating fixtures/types behind `src/api`.
- The skill explicitly warns against claiming accessibility effectiveness without user testing; this report describes implemented mechanisms (focus order, aria-live, contrast, no color-only signaling), not a compliance claim.
- If stable section IDs don't hold across versions, Evidence panel deep-linking breaks — flag to coordinator before implementation.
