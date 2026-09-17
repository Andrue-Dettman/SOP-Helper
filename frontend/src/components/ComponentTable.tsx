import './ComponentTable.css'
import type { BuildComponent } from '../api/types'

export interface ComponentTableProps {
  components: BuildComponent[]
}

function formatQuantity(value: number | null): string {
  return value === null ? 'Unknown' : String(value)
}

export function ComponentTable({ components }: ComponentTableProps) {
  return (
    <div className="component-table__scroll">
      <table className="component-table">
        <thead>
          <tr>
            <th scope="col">Part</th>
            <th scope="col">Required</th>
            <th scope="col">Available</th>
            <th scope="col">Shortage</th>
          </tr>
        </thead>
        <tbody>
          {components.map((component) => {
            const isShort = Boolean(component.shortage)
            return (
              <tr
                key={component.part_id}
                className={isShort ? 'component-table__row--short' : undefined}
              >
                <th scope="row">{component.part_id}</th>
                <td>{component.required}</td>
                <td>{formatQuantity(component.available)}</td>
                <td>{formatQuantity(component.shortage)}</td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}
