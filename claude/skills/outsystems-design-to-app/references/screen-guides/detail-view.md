# Detail / View Screen

## Anatomy

A read-only screen showing a single record with its related data. Expected sections:

1. **Page header row**: Entity name/title (heading3) + status badge (Tag pattern with semantic color) + action button group:
   - "Edit" button (primary) — navigates to edit form with this record's Id
   - "Delete" button (error/destructive style) — with confirmation modal
   - "Back" button or breadcrumb — returns to list
   - Optional contextual actions: "Print", "Export", "Approve", "Clone"
2. **Primary info card** (CardSectioned block or card container): Read-only fields displayed as label-value pairs:
   - Label (font-semi-bold, text-neutral-7) on left or above
   - Value (text-neutral-9) on right or below
   - Group fields into sections with heading5 separators (e.g., "General", "Contact Info", "Address")
   - For two-column layout: use responsive columns with labels left and values right, or two label-value columns side-by-side
3. **Related data sections**: One section per related entity. Each section has:
   - Section heading (heading5) with optional "Add New" link
   - Data table (TableRecords) showing related records (e.g., Contracts for a Client, Tasks for an Audit)
   - Row actions: view detail, edit, delete for each related record
   - Empty state message if no related records exist
4. **Optional tabs**: When there are 3+ related data sections, wrap them in a tab container (Tabs block) to reduce vertical scrolling

## Layout

- Header row: flex layout, title left, action buttons right
- Primary info card: full-width or centered with max-width. Generous internal padding
- Related data sections: full-width below primary card, each with margin-top-l
- Tabs (if used): full-width, one tab per related entity group

## Styling

- Status badge: Tag pattern — semantic background (success/warning/error/info) with contrasting text
- Label-value pairs: labels muted (text-neutral-7, font-size-s), values standard (text-neutral-9)
- Action buttons: primary for Edit, error for Delete (with margin-left between buttons). Destructive actions require confirmation
- Related tables: same styling as list screen tables (striping, compact rows)
- Section separators: heading5 with margin-top-l, optional bottom border

## Data Patterns

- Main aggregate: fetch record by Id (input parameter) with joins to display related entity names (e.g., owner name, category label)
- Related data aggregates: one per related entity, filtered by the current record's Id, sorted by date descending
- Handle missing record: if main aggregate returns empty, show "Record not found" message with back navigation

## Responsive Behavior

- Desktop: header + card + related sections stacked, card may use two-column label-value layout
- Tablet: same layout, slightly narrower
- Phone: single-column label-value pairs (label above, value below), tables may switch to card list
