---
name: warehouse-interface
description: Build a readable, keyboard-accessible procedure and inventory interface for the synthetic warehouse assistant.
---

Create the usable app first: question input, answer steps, source passages, and inventory results. Keep original text one action away, with stable focus behavior. Show required warnings and uncertainty without relying on color alone. Distinguish fictional data and service errors from a successful answer.

Use React/TypeScript with typed API responses, lucide icons, visible labels, appropriate buttons/menus, and semantic ordered lists. Plan desktop and mobile layouts with no overlapping text, keyboard traps, or horizontal page overflow. Tables can scroll within their own region. Do not claim accessibility effectiveness without user testing.

Choose quiet operational styling and restrained color. Avoid marketing heroes, decorative cards around page sections, and instructional walls of text. Use a meaningful product/parts visual only where it improves recognition. Reduced motion, clear focus, text resizing, contrast, and announcements for async results are testable requirements.

Mock only at the API boundary, following shared schemas. Cover all response states and delayed/failed requests. Use Playwright screenshots and keyboard checks on desktop/mobile, plus automated accessibility checks as supporting evidence, not certification.
