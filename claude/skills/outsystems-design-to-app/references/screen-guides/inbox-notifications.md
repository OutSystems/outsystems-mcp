# Inbox / Notification Center Screen

## Anatomy

A list of messages, alerts, or actionable items with read/unread state management. Used for email inboxes, notification feeds, task inboxes, and approval queues.

1. **Inbox header**: Title (heading3) + unread count badge + action buttons:
   - "Mark All Read" button (secondary)
   - Filter/sort controls (unread only, by date, by type)
   - Optional: "Compose" / "New" button for email-style inboxes
2. **Item list**: Scrollable list of inbox items, each showing:
   - Read/unread indicator: unread items visually distinct (bold title, background-neutral-1, or left border accent)
   - Sender/source: avatar or icon + name/source label
   - Preview: title (font-semi-bold) + first line of content (text-neutral-7, truncated)
   - Timestamp: relative time ("2h ago", "Yesterday") aligned right
   - Action buttons on hover/swipe: Mark read, Archive, Delete, Reply
3. **Item detail panel** (optional, for email/message style):
   - Full content display when item is selected
   - Reply/forward/action controls
   - Shown as right panel (master-detail layout) or as a separate screen on phone
4. **Empty state**: "No notifications" / "Inbox zero" illustration with positive message

## Variants

- **Notification dropdown**: Compact list in a dropdown panel triggered by bell icon. 5-10 most recent items + "View all" link
- **Task inbox**: Each item is an actionable task with "Approve" / "Reject" buttons inline
- **Email inbox**: Full sender, subject, preview. Checkbox for multi-select. Toolbar with bulk actions (archive, delete, mark read)

## Layout

- Full-page inbox: single-column list, or master-detail split (list left ~40%, detail right ~60%)
- Notification dropdown: max-width ~400px, max-height ~500px, positioned under bell icon
- Items: consistent height per item for visual rhythm. Generous padding for touch targets

## Styling

- Unread items: font-semi-bold title, background-neutral-1, or 3px left border in primary color
- Read items: regular font weight, background-neutral-0
- Timestamps: text-neutral-6, font-size-xs, right-aligned
- Hover state: background-neutral-1, reveal action icons
- Badge count: small rounded badge on the nav icon/tab with error or primary background color
- Grouped by date: date separator headings ("Today", "This Week", "Older")

## Data Patterns

- Data source: items with read/unread status, sender, title, preview text, timestamp, type/category
- Default sort: newest first (descending timestamp)
- Filter: unread only, by type/category
- Mark read: on item click or explicit action. Update read status server-side
- Polling or push: check for new items periodically (or real-time via data action refresh)

## Responsive Behavior

- Desktop: full inbox with optional detail panel
- Tablet: same, detail panel may overlap as a drawer
- Phone: list only; clicking an item navigates to full-screen detail. Swipe actions (swipe left to delete/archive)
