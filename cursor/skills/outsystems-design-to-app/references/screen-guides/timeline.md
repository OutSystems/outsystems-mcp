# Timeline / Activity Feed Screen

## Anatomy

A chronological stream of events, actions, or updates. Used for activity logs, audit trails, notification feeds, and social-style feeds.

1. **Feed header**: Title (heading3) + optional filter controls (date range, actor, action type) + optional "Mark all read" action
2. **Timeline stream**: Vertical list of entries, ordered by timestamp (newest first or oldest first depending on context):
   - **Date separator**: When entries span multiple days, insert a date heading between day groups ("Today", "Yesterday", "April 28, 2026")
   - **Entry anatomy**:
     - Avatar or icon (left side): actor photo (Avatar pattern, small) or action-type icon
     - Content (right side): Actor name (font-semi-bold) + action description + target entity link + timestamp (text-neutral-7, font-size-xs)
     - Optional: preview snippet, attachment thumbnail, or comment text below the action line
   - **Connector line**: Vertical line connecting entry icons/avatars (left-aligned)
3. **Load more / pagination**: "Load older" button at bottom, or infinite scroll for casual feeds
4. **Empty state**: "No activity yet" with illustration + description

## Variants

- **Audit trail**: Formal log — actor + action + entity + timestamp. No avatars, icon-based. Compact density
- **Notification feed**: Read/unread state. Unread entries bold/highlighted. Dismiss or mark-read actions per entry
- **Social-style feed**: Rich content — images, comments, reactions. Cards per entry with more padding
- **Conversation / chat**: Messages alternating left (received) and right (sent). Timestamp per message or per group

## Layout

- Stream: single-column, centered with max-width (~700px) for readability. Or full-width in a sidebar panel
- Entries: avatar/icon fixed-width left column (~40px), content fills remaining width
- Connector line: 2px vertical line through the avatar/icon column center
- Date separators: centered text with horizontal rules on each side

## Styling

- Entries: padding-s vertically between entries. No card wrapper needed (connector line provides structure)
- Avatars: 32-36px circle (Avatar pattern, small)
- Action text: "**John Smith** updated the status of **Order #1234** to Shipped" — actor and entity names in font-semi-bold or as clickable links
- Timestamps: text-neutral-7, font-size-xs, positioned right of action text or below
- Unread items (notification variant): background-neutral-1 or left border in primary color
- Connector line: border-left on the avatar column, color neutral-3

## Data Patterns

- Data source: activity/event records with actor, action type, target entity, timestamp, and optional detail text
- Default sort: newest first (descending timestamp)
- Pagination: load 20-50 at a time, "Load more" at bottom
- Real-time updates: new entries prepended to top with subtle animation (slide-in)

## Responsive Behavior

- Desktop/Tablet: single-column stream with avatars and connector line
- Phone: simplified — smaller avatars or icons only, shortened action text, timestamps abbreviated ("2h ago")
