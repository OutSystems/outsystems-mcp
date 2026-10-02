# Reusable Block Patterns

## When to Extract a Reusable Block

Extract a UI pattern as a reusable block when:
- The same visual pattern (3+ elements) appears on 2+ screens with different data
- A component needs different data bindings but identical structure
- A component has its own interaction logic (events, state changes) independent of the host screen

**Common extraction candidates:**
- Status badge: colored tag showing entity status (Active/Pending/Closed) — used across all list and detail screens
- User avatar card: avatar image + name + role — used in headers, activity feeds, team lists
- Filter bar: search input + dropdown filters + date range + Apply/Clear buttons — used on every list screen
- Action button group: Save/Cancel or Edit/Delete with consistent styling and spacing
- KPI tile: icon + metric value + label + trend indicator — used on dashboards
- Empty state: illustration + heading + description + CTA — used in every list/table/grid
- Confirmation modal: title + message + destructive action button + cancel — used for all delete operations

## Block Design Principles

1. **Input parameters for all variable data**: entity Id, display values (name, status text), boolean flags (isEditable, showAvatar), CSS class override (ExtendedClass)
2. **Events for user interactions**: OnSave, OnDelete, OnFilterChanged, OnClose, OnItemSelected — let the parent screen handle the business logic
3. **ExtendedClass parameter**: Always include an ExtendedClass (Text) input parameter so the parent screen can add CSS classes to the block wrapper for contextual spacing/sizing
4. **Minimal internal StyleSheet**: Only styles specific to this block's internal layout. Use OutSystems UI utility classes for spacing/colors — don't create block-specific classes for common patterns
5. **Self-contained data**: Block should fetch its own data via parameters (Id-based) or accept data via input parameters — not rely on the parent screen's aggregates

## Component Quality Rules

All interactive components within blocks (and across the app) must follow these rules:
- **Buttons**: Must have hover, focus, disabled, and loading states — not just a default resting state
- **Inputs**: Consistently styled with validation/error states. All inputs use the form-control pattern
- **Checkboxes**: For multi-select (any number of selections). Never use for single-select
- **Radio buttons**: For mutually exclusive single-select. Never use for multi-select
- **Labels**: Always persistent above inputs — never use placeholder text as the only label
- **One version of each component**: The same button style, input style, dropdown style reused everywhere. Two visually different "primary" buttons on the same screen = failure
