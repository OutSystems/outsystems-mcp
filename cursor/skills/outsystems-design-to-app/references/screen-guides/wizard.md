# Multi-Step Wizard / Onboarding Screen

## Anatomy

A guided flow that breaks a complex task into sequential steps. Used for onboarding, multi-part forms, checkout flows, and setup processes.

1. **Step indicator**: Shows current position in the flow:
   - Progress bar (ProgressBar block) showing percentage complete, OR
   - Numbered steps with labels (Wizard block) — active step highlighted, completed steps with checkmark, future steps dimmed
2. **Step content area**: One form section per step, showing only the fields relevant to this step:
   - Step title (heading4) + optional description text
   - Input fields for this step only (progressive disclosure — don't show all fields at once)
   - Inline validation feedback for current step fields
3. **Navigation buttons**: Bottom of step content:
   - "Back" button (secondary style) — returns to previous step. Hidden on first step
   - "Next" button (primary style) — validates current step and advances. Changes to "Submit" / "Finish" on final step
   - Optional "Skip" link — for optional steps, text-link style below the buttons
4. **Summary / confirmation step** (final step): Review of all entered data across steps before final submission. Edit links per section to jump back
5. **Success state**: After submission — confirmation message with summary + next-action links

## Layout

- Step indicator: full-width, fixed at top of the wizard container
- Content area: centered with max-width (~600px), generous padding
- Navigation buttons: right-aligned. Back on left, Next/Submit on right
- Responsive: same layout on all breakpoints, content area full-width on phone

## Styling

- Step indicator: active step in primary color, completed steps in success color with checkmark icon, future steps in neutral-4
- Step transitions: content area transitions smoothly between steps (fade or slide)
- Current step content: card container or plain background with clear section boundaries
- Progress text: "Step 2 of 4" displayed near the step indicator
- Button group: margin-top-l above buttons

## Data Patterns

- Local variables for each step's form data (persisted across steps — not cleared on navigation)
- Validation per step: validate current step fields before allowing "Next"
- Final submit: combine all step data and send to server action
- Back navigation: restore previous step's values from local variables (no re-fetch needed)
- Optional: save progress server-side for resumable flows (especially for long onboarding)

## Responsive Behavior

- Desktop/Tablet: centered wizard with step indicator
- Phone: step indicator simplified (progress bar instead of numbered steps), full-width content
