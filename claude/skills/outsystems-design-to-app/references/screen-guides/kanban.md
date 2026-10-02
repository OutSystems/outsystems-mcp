# Kanban / Board View Screen

## Anatomy

A board layout with columns representing stages or statuses, and cards that can be moved between columns. Ideal for workflow/pipeline visualization.

1. **Board header**: Title (heading3) + optional filter controls (assignee, priority, date range) + "Add New" button
2. **Column strip**: Horizontal row of columns, each representing a stage/status:
   - **Column header**: Stage name + item count badge (Badge pattern) + optional "Add" button per column
   - **Card stack**: Vertically stacked cards within the column, scrollable if many items
   - **Drop zone indicator**: Visual feedback area at bottom of column for card placement
3. **Card anatomy** (each card in the stack):
   - Title / primary identifier (font-semi-bold)
   - Assignee avatar (Avatar pattern, small) or initials badge
   - Due date (font-size-xs, text-neutral-7). Overdue dates highlighted in error color
   - Priority or category tag (Tag pattern with semantic color)
   - Optional: progress indicator, comment count, attachment count
4. **Optional swimlanes**: Horizontal grouping rows (by team, priority, or category) dividing the board

## Layout

- Board: horizontal scroll container for columns. Each column fixed-width (~280-320px) or fluid with min-width
- Columns: equal width, separated by gutter-s or gutter-base
- Cards: full-width within column, margin-bottom-s between cards
- Responsive: on phone, show one column at a time with horizontal swipe or collapse to list view grouped by status

## Styling

- Columns: background-neutral-1 or background-neutral-2, border-radius on top corners, padding-s internally
- Column headers: font-semi-bold, padding-bottom-s, with subtle bottom border
- Cards: background-neutral-0 (white), border-radius-soft, shadow-s, padding-s. Hover: shadow-m for lift effect
- Status colors: map each column/stage to a semantic or extended-palette color for the column header accent
- Overdue: due date text in text-error, optional background-error on card border
- Item count badge: small rounded badge next to column title

## Data Patterns

- One data source returning all items with a status/stage field
- Group client-side by status value into columns
- Card click: navigate to detail view or open inline edit panel
- Status update: move card between columns updates the status field (optimistic UI — update immediately, sync in background)

## Responsive Behavior

- Desktop: all columns visible side-by-side with horizontal scroll if >4 columns
- Tablet: 2-3 columns visible, horizontal scroll for rest
- Phone: single column view (tab or dropdown to switch stages), or collapsible accordion per stage
