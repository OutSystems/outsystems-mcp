# Timeline / Activity Feed Screen

## Anatomy

A chronological stream of events, actions, or updates. Used for activity logs, audit trails, notification feeds, and social-style feeds.

1. **Feed header**: Title (heading3) + optional filter controls (date range, actor, action type) + optional "Mark all read" action
2. **Timeline stream**: stacked `TimelineItem` blocks (one per entry; there is no Timeline container block), ordered by timestamp (newest first or oldest first depending on context):
   - **Date separator**: When entries span multiple days, insert a date heading between day groups ("Today", "Yesterday", "April 28, 2026")
   - **Entry anatomy**:
     - `Icon` placeholder: actor photo (UserAvatar block, small) or action-type Icon
     - `Title` placeholder: Actor name (font-semi-bold) + action description + target entity link
     - `Content` placeholder: timestamp (text-neutral-7, font-size-xs), optional preview snippet, attachment thumbnail, or comment text
     - `Right` placeholder (optional): timestamp or status tag aligned right
   - The TimelineItem draws its own connector line; don't hand-build one
3. **Load more / pagination**: "Load older" button at bottom, or infinite scroll for casual feeds
4. **Empty state**: BlankSlate block — "No activity yet" with icon + description

## Variants

- **Audit trail**: Formal log — actor + action + entity + timestamp. No avatars, icon-based. Compact density
- **Notification feed**: Read/unread state. Unread entries bold/highlighted. Dismiss or mark-read actions per entry
- **Social-style feed**: Rich content — images, comments, reactions. Cards per entry with more padding
- **Conversation / chat**: Messages alternating left (received) and right (sent). Timestamp per message or per group

## Layout

- Stream: single-column, centered with max-width (~700px) for readability. Or full-width in a sidebar panel
- Date separators: centered text with horizontal rules on each side

## Styling

- Entries: padding-s vertically between entries. No card wrapper needed (the TimelineItem line provides structure)
- Avatars: UserAvatar block, small
- Action text: "**John Smith** updated the status of **Order #1234** to Shipped" — actor and entity names in font-semi-bold or as clickable links
- Timestamps: text-neutral-7, font-size-xs, positioned right of action text or below
- Unread items (notification variant): background-neutral-1 or left border in primary color

## Data Patterns

- Data source: activity/event records with actor, action type, target entity, timestamp, and optional detail text
- Default sort: newest first (descending timestamp)
- Pagination: load 20-50 at a time, "Load more" at bottom
- Real-time updates: new entries prepended to top with subtle animation (slide-in)

## Responsive Behavior

- Desktop/Tablet: single-column stream with avatars
- Phone: simplified — smaller avatars or icons only, shortened action text, timestamps abbreviated ("2h ago")
