import { Loader2 } from 'lucide-react'
import './LoadingIndicator.css'

export function LoadingIndicator() {
  return (
    <div className="loading-indicator" role="status" aria-live="polite">
      <Loader2 aria-hidden="true" size={16} className="loading-indicator__spinner" />
      <span>Thinking…</span>
    </div>
  )
}
