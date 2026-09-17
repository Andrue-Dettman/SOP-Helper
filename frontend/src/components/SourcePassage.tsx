import './SourcePassage.css'

export interface SourcePassageProps {
  title: string
  text: string
  isFullText: boolean
  isCurrent?: boolean
}

export function SourcePassage({ title, text, isFullText, isCurrent }: SourcePassageProps) {
  return (
    <div className="source-passage">
      <p className="source-passage__label">{isFullText ? 'Full section text' : 'Quoted excerpt'}</p>
      <h4 className="source-passage__title">{title}</h4>
      {isFullText && isCurrent === false && (
        <p className="source-passage__historical">Historical version — no longer the current procedure.</p>
      )}
      <blockquote className="source-passage__text">{text}</blockquote>
    </div>
  )
}
