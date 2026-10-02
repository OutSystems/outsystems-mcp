# Calendar / Scheduling View Screen

## Anatomy

A calendar display for time-based data (events, appointments, deadlines, tasks). Expected sections:

1. **Calendar header**: Month/year display + navigation arrows (prev/next) + view toggle (Month / Week / Day buttons)
2. **Calendar grid**:
   - **Month view**: 7-column grid (Mon-Sun), rows per week. Each day cell shows date number + up to 2-3 event previews. "Show more" link if >3 events
   - **Week view**: 7-column grid with hourly time slots on the left axis. Events as positioned blocks spanning their duration
   - **Day view**: Single column with hourly time slots. Events as full-width blocks
3. **Event cards** (within calendar cells):
   - Title (truncated to fit cell)
   - Color-coded left border or background by category/type
   - Time range (for week/day views)
4. **Sidebar** (optional): Mini-calendar for quick date navigation + upcoming events list (next 5-7 events)
5. **"Add event" interaction**: Click/tap on empty time slot or "+" button to create new event

## Layout

- Calendar: full-width grid with fixed header
- Month view: equal-width columns, flexible row heights based on content
- Week/Day view: time axis on left (~60px), event columns fill remaining width
- Sidebar: right panel (~250px desktop), hidden on tablet/phone or collapsible
- Responsive: month view on desktop/tablet; agenda list (chronological) on phone

## Styling

- Day cells: border-neutral-3 borders, padding-xs internally. Today highlighted with primary background accent or border
- Weekend columns: subtle background-neutral-1
- Event cards: border-radius-soft, padding-xs, font-size-xs. Color-coded by category using extended palette (not semantic colors — reserve those for status)
- Current time indicator: horizontal line in primary color across the time grid (week/day views)
- Header navigation: icon buttons for prev/next, button group for view toggle

## Data Patterns

- Data source: events/appointments with start datetime, end datetime, title, category, and optional location
- Month view: query events for the visible month range
- Week/Day view: query events for the visible date range
- On event click: navigate to detail view or open edit popup
- On empty cell click: open create form pre-filled with the clicked date/time

## Responsive Behavior

- Desktop: full calendar grid with optional sidebar
- Tablet: calendar grid without sidebar, or sidebar collapsed
- Phone: agenda/list view (chronological list of upcoming events grouped by date) replaces the grid
