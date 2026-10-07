# Reusable Block Patterns

## When to Extract a Reusable Block

Extract a UI pattern as a reusable block when:
- The same visual pattern (3+ elements) appears on 2+ screens with different data
- A component needs different data bindings but identical structure
- A component has its own interaction logic (events, state changes) independent of the host screen

Don't wrap an OutSystems UI block or platform widget that already does the job (BlankSlate for empty states, the Popup widget for confirmations, Tag for status); use it directly.

**Common extraction candidates:**
- Status badge: Tag with the entity-status colour mapping (Active/Pending/Closed) — used across all list and detail screens
- User card: UserAvatar + name + role — used in headers, activity feeds, team lists
- Filter bar: search input + dropdown filters + date range + Apply/Clear buttons — used on every list screen
- KPI tile: icon + metric value + label + trend indicator — used on dashboards
- Delete confirmation (when the design shows none of its own): Popup with title + message + destructive button + cancel — used for all delete operations

## Block Design Principles

1. **Input parameters for all variable data**: entity Id, display values (name, status text), boolean flags (isEditable, showAvatar), CSS class override (ExtendedClass)
2. **Events for user interactions**: OnSave, OnDelete, OnFilterChanged, OnClose, OnItemSelected — let the parent screen handle the business logic
3. **ExtendedClass parameter**: Always include an ExtendedClass (Text) input parameter so the parent screen can add CSS classes to the block wrapper for contextual spacing/sizing
4. **No block stylesheet**: use OutSystems UI utility classes; any custom class goes once in `design_system.theme_extensions`
5. **Self-contained data**: Block should fetch its own data via parameters (Id-based) or accept data via input parameters — not rely on the parent screen's aggregates

## Component Quality Rules

- **Buttons**: hover, focus, disabled, and loading states — not just a default resting state
- **Inputs**: consistently styled with validation/error states, labels persistent above inputs (never placeholder-only)
- **One version of each component**: the same button, input and dropdown style reused everywhere
