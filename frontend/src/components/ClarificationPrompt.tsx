import { useId, useState } from 'react'
import './ClarificationPrompt.css'
import type { Clarification, ClarificationChoice } from '../api/types'

export interface ClarificationPromptProps {
  clarification: Clarification
  onSelectChoice: (choice: ClarificationChoice) => void
  onSubmitQuantity?: (quantity: number) => void
}

export function ClarificationPrompt({ clarification, onSelectChoice, onSubmitQuantity }: ClarificationPromptProps) {
  const [quantityInput, setQuantityInput] = useState('')
  const inputId = useId()

  function handleSubmitQuantity() {
    const quantity = Number(quantityInput)
    if (quantityInput.trim() === '' || !Number.isInteger(quantity) || quantity <= 0) {
      return
    }
    onSubmitQuantity?.(quantity)
  }

  return (
    <div className="clarification-prompt" role="group" aria-label="Clarification needed">
      <p className="clarification-prompt__question">{clarification.question}</p>
      {clarification.choices.length > 0 ? (
        <div className="clarification-prompt__choices">
          {clarification.choices.map((choice) => (
            <button
              key={choice.id}
              type="button"
              className="clarification-prompt__choice"
              onClick={() => onSelectChoice(choice)}
            >
              {choice.label}
            </button>
          ))}
        </div>
      ) : clarification.kind === 'quantity' ? (
        <div className="clarification-prompt__quantity">
          <label htmlFor={inputId}>Quantity</label>
          <input
            id={inputId}
            type="number"
            min={1}
            step={1}
            value={quantityInput}
            onChange={(event) => setQuantityInput(event.target.value)}
          />
          <button type="button" onClick={handleSubmitQuantity}>
            Submit
          </button>
        </div>
      ) : null}
    </div>
  )
}
