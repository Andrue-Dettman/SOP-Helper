import { CircleCheck, CircleX, HelpCircle } from 'lucide-react'
import './InventoryResult.css'
import { ComponentTable } from './ComponentTable'
import type { InventoryResult as InventoryResultData } from '../api/types'

export interface InventoryResultProps {
  result: InventoryResultData
}

function ReadinessBanner({ ready }: { ready: boolean | null }) {
  if (ready === true) {
    return (
      <p className="inventory-result__banner inventory-result__banner--ready">
        <CircleCheck aria-hidden="true" size={18} />
        Ready
      </p>
    )
  }
  if (ready === false) {
    return (
      <p className="inventory-result__banner inventory-result__banner--not-ready">
        <CircleX aria-hidden="true" size={18} />
        Not ready
      </p>
    )
  }
  return (
    <p className="inventory-result__banner inventory-result__banner--unknown">
      <HelpCircle aria-hidden="true" size={18} />
      Readiness unknown (incomplete data)
    </p>
  )
}

function formatCapturedAt(iso: string): string {
  try {
    return new Date(iso).toLocaleString()
  } catch {
    return iso
  }
}

export function InventoryResult({ result }: InventoryResultProps) {
  return (
    <section className="inventory-result" aria-label="Inventory result">
      {result.kind === 'build' ? (
        <>
          <h3>
            {result.assembly_id} — {result.requested_units} units
          </h3>
          <ReadinessBanner ready={result.ready} />
          <ComponentTable components={result.components} />
        </>
      ) : (
        <>
          <h3>Stock lookup</h3>
          <ul className="inventory-result__stock-list">
            {result.matches.map((match) => (
              <li key={match.part_id}>
                <span>{match.label}</span>
                <span>{match.available === null ? 'Unknown' : `${match.available} ${match.unit}`}</span>
              </li>
            ))}
          </ul>
        </>
      )}
      {result.snapshot && (
        <p className="inventory-result__snapshot">
          Data snapshot {result.snapshot.snapshot_id} · captured {formatCapturedAt(result.snapshot.captured_at)}
        </p>
      )}
    </section>
  )
}
