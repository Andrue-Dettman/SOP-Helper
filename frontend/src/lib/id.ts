let counter = 0

/** Simple monotonic ID for conversation turns; avoids depending on crypto.randomUUID availability. */
export function nextId(): string {
  counter += 1
  return `turn-${counter}`
}
