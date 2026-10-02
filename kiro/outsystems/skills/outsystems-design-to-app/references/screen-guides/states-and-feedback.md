# States & Feedback Guide

Every screen and interactive element must communicate its state. Missing state feedback is one of the top usability failures.

## Loading States

| Duration | Correct Pattern | Wrong Pattern |
|---|---|---|
| < 1 second | No indicator needed (instant feel) | Spinner (flashy, distracting) |
| 1-3 seconds | Skeleton screen or shimmer placeholder in the shape of expected content | Blank white area + generic spinner |
| 3-10 seconds | Progress bar with estimated progress or indeterminate loading bar | Nothing (user assumes page is broken) |
| > 10 seconds | Progress bar + status message explaining what's happening | Spinner only (feels stuck) |

### CTA Loading State (Critical)
After a user clicks a submit/save/action button:
- Button immediately shows loading state: disabled + spinner icon inside, or label changes to "Saving..."
- No "dead click" — user must see immediate visual feedback that their action registered
- Re-enable button after completion (success or error)

## Error States

- **Inline errors** (per field): Show below the input field in error color (text-error) with icon. Explain what's wrong AND how to fix it ("Email format invalid — use name@example.com")
- **Form-level errors**: Summary at top of form listing all errors. Each links/scrolls to the problematic field
- **API/server errors**: Inline message in the content area (Alert pattern, error variant). Explain what happened + what the user can do ("Connection lost. Your changes were saved locally. Retry when connected.")
- **Never use color alone** for errors: always pair red border/text with an icon or text label (accessibility — color-blind users miss color-only signals)
- **Recovery actions**: Every error message should offer a next step — "Retry", "Go back", "Contact support", or "Try a different value"

## Empty States

Every list, table, card grid, and data widget needs a designed empty state — never show a blank area or just "No results."

**Empty state anatomy:**
- Illustration or icon (centered, muted/light)
- Heading: short, descriptive ("No clients yet", "No matching results")
- Description: 1-2 sentences explaining why empty and what to do
- Primary action: CTA button to resolve the empty state ("Add your first client", "Clear filters", "Import data")

**Empty state variants:**
- **No data ever**: First-use state — welcoming tone, guide user to create first item
- **No matching results**: Search/filter returned nothing — offer "Clear filters" or "Try different search"
- **Error loading**: Data fetch failed — offer "Retry" button
- **Completed/archived**: All items processed — positive tone ("All caught up!", "Inbox zero")

## Validation Feedback

- **When to validate**: On blur (when user leaves a field) — not on every keystroke. Exception: password strength can update live
- **Success state**: Show subtle success indicator (checkmark icon, green border) after field passes validation — gives positive reinforcement
- **Mandatory fields**: Mark with asterisk (*) or "(required)" next to label. Don't rely on error-after-submit to communicate which fields are required
- **Cross-field validation**: Validate on form submit. Highlight all invalid fields simultaneously with scroll-to-first-error

## Destructive Actions

- **Preferred**: Undo pattern — execute immediately, show toast with "Undo" link (5-10 second window). Fastest and least disruptive
- **Acceptable**: Confirmation modal — "Are you sure you want to delete [item name]?" with clear explanation of consequences. "Delete" button in error style, "Cancel" in secondary style
- **Never**: Silent deletion with no feedback, or browser's native window.confirm()

## Task Completion

After a major action completes (form submission, checkout, onboarding):
- Show meaningful confirmation — not just a checkmark + "Success"
- Include: summary of what was done, reference number/ID if applicable, relevant next steps ("View the record", "Add another", "Return to list")
- For critical flows (payments, orders): include transaction details (amount, recipient, timestamp)

## Layout Shift Prevention

- Reserve space for content that loads asynchronously (fixed-height containers, skeleton screens)
- Images: set explicit width/height or use aspect-ratio containers to prevent reflow
- Error messages: reserve space below inputs (min-height) so adding an error doesn't push content down
- Toast/snackbar notifications: overlay content, don't insert into the document flow
