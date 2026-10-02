# Master-Detail Screen

## Anatomy

A split-panel layout showing a selectable list on one side and the selected record's detail on the other. Best for workflows where users browse and inspect records without full page navigation.

1. **List panel** (left, ~1/3 width): Compact list of records showing primary identifier + brief metadata. Includes:
   - Search input at top
   - Scrollable list of items
   - Selected item highlighted with distinct background
   - Item count indicator
2. **Detail panel** (right, ~2/3 width): Full detail view of the selected record (follows the [detail-view recipe](detail-view.md)):
   - Record header with title + status
   - Label-value field pairs
   - Related data or action buttons
   - Placeholder / empty state when no record is selected ("Select an item to view details")
3. **Optional action bar**: Above the split, with bulk actions or "Add New" button

## Layout

- Split container: responsive columns (ColumnsSmallLeft block) — ~33% left, ~67% right
- List panel: fixed height with vertical scroll, search pinned at top
- Detail panel: scrolls independently
- Responsive collapse: on phone, show only the list; tapping an item navigates to a full-screen detail view

## Styling

- List items: padding-s vertically, border-bottom divider between items
- Selected item: background-primary with text-neutral-0, or background-neutral-2 for subtle highlight
- List hover: background-neutral-1 on hover
- Detail panel: card container or plain background with padding
- Split gutter: minimal (gutter-s or gutter-none with a vertical border separator)

## Data Patterns

- List aggregate: fetch all records (or filtered subset) with minimal columns for compact display
- Detail aggregate: fetch full record by the selected Id (local variable tracking selection)
- On list item click: update selected Id, detail panel re-fetches
- Handle empty selection: show placeholder in detail panel initially

## Responsive Behavior

- Desktop/Tablet: side-by-side split layout
- Phone: list-only view; selecting an item navigates to a separate detail screen (or uses a slide-in panel)
