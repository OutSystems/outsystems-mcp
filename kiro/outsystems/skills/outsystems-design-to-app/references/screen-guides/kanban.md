# Kanban / Board View Screen

## Anatomy

A board layout with columns representing stages or statuses, and cards that move between columns via an action on the card (OutSystems UI has no drag-and-drop). Ideal for workflow/pipeline visualization.

1. **Board header**: Title (`AdvancedHtml Tag="h1"` in the Layout's `Title` placeholder) + optional filter controls (assignee, priority, date range) + "Add New" button
2. **Column strip**: Horizontal row of columns, each representing a stage/status:
   - **Column header**: Stage name + item count badge (Badge pattern) + optional "Add" button per column
   - **Card stack**: Vertically stacked cards within the column, scrollable if many items
3. **Card anatomy** (each card in the stack):
   - Title / primary identifier (font-semi-bold)
   - Assignee avatar (UserAvatar block, small) or initials badge
   - Due date (font-size-xs, text-neutral-7). Overdue dates highlighted in error color
   - Priority or category tag (Tag pattern with semantic color)
   - Optional: progress indicator, comment count, attachment count
   - **Move control**: a status Dropdown, a Button, or an OverflowMenu ("Move to…") on the card
4. **Optional swimlanes**: Horizontal grouping rows (by team, priority, or category) dividing the board

## Layout

- Board: one column per stage from a `Columns2`–`Columns6` block, or a `Gallery` with `RowItemsDesktop` = the stage count. Beyond 6 stages, only a named class defined once in `theme_extensions` (Step 3a exception 2), never a custom scroll container
- Columns: equal width; the gap is the block's `GutterSize` input (`Small` or `Base`), or `ItemsGap` on a Gallery
- Cards: full-width within column, margin-bottom-s between cards
- Responsive: on phone, stack the stages (`PhoneBehavior = All`, or `RowItemsPhone = 1`) or collapse to a list view grouped by status

## Styling

- Columns: background-neutral-1 or background-neutral-2, border-radius on top corners, padding-s internally
- Column headers: font-semi-bold, padding-bottom-s, with subtle bottom border
- Cards: `Card` block, background-neutral-0 (white), border-radius-soft, shadow-s, padding-s. Hover: shadow-m for lift effect
- Status colors: map each column/stage to a semantic or extended-palette color for the column header accent
- Overdue: due date text in text-error, optional background-error on card border
- Item count badge: small rounded badge next to column title

## Data Patterns

- One data source returning all items with a status/stage field
- Group client-side by status value into columns
- Card click: navigate to detail view or open inline edit panel
- Status update: the card's move control updates the status field and refreshes the board

## Responsive Behavior

- Desktop: all stage columns visible side-by-side
- Tablet: the block's `TabletBehavior` (or the Gallery's `RowItemsTablet`) sets how the stages wrap
- Phone: single column view (tab or dropdown to switch stages), or collapsible accordion per stage
