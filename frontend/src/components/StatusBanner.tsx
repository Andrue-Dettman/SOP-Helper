import { AlertTriangle, CircleAlert, WifiOff } from 'lucide-react'
import './StatusBanner.css'

export type StatusBannerVariant = 'insufficient_evidence' | 'temporarily_unavailable' | 'network_error'

export interface StatusBannerProps {
  variant: StatusBannerVariant
  /** Overrides the default copy, e.g. with the server's error.message. */
  message?: string
  onRetry?: () => void
}

const DEFAULT_MESSAGE: Record<StatusBannerVariant, string> = {
  insufficient_evidence:
    'There is not enough evidence in the current procedures to answer that. Try rephrasing or ask about a specific procedure.',
  temporarily_unavailable: 'This part of the assistant is temporarily unavailable. Please try again shortly.',
  network_error: "Couldn't reach the server. Check your connection and try again.",
}

const ICON: Record<StatusBannerVariant, typeof AlertTriangle> = {
  insufficient_evidence: AlertTriangle,
  temporarily_unavailable: CircleAlert,
  network_error: WifiOff,
}

export function StatusBanner({ variant, message, onRetry }: StatusBannerProps) {
  const Icon = ICON[variant]
  return (
    <div className={`status-banner status-banner--${variant}`} role="status">
      <Icon aria-hidden="true" size={18} className="status-banner__icon" />
      <p className="status-banner__message">{message ?? DEFAULT_MESSAGE[variant]}</p>
      {onRetry && (
        <button type="button" className="status-banner__retry" onClick={onRetry}>
          Retry
        </button>
      )}
    </div>
  )
}
