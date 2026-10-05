# Dashboard / Analytics Screen

## Anatomy

A dashboard presents a high-level overview of key metrics and recent activity. Expected sections, top to bottom:

1. **Page header**: Title (heading3) + optional date range or period selector
2. **KPI counter row**: 3-5 counter tiles in a responsive grid (columns layout, 3-4 columns desktop). Each tile contains:
   - Icon or small graphic representing the metric
   - Large numeric value (heading2 or heading3 weight)
   - Label describing the metric
   - Optional trend indicator (up/down arrow + percentage change)
3. **Charts row**: 1-2 charts showing trends or distributions (bar, line, donut). Place in a 2-column layout or full-width depending on chart count
4. **Summary list**: Recent or top items (5-10 rows), sorted by recency or priority. Use a compact data table (TableRecords) or card list (List widget)
5. **Optional filter bar**: Date range selector, category dropdown, status filter — placed above the KPI row or in the header

## Layout

- Use `Columns2` / `Columns3` blocks to arrange sections side-by-side. Without them, all sections stack vertically
- Counter tiles: wrap 3 counters in a `Columns3`, or 2 in a `Columns2` — so they appear as a row
- Charts: wrap 2 charts in a `Columns2` so they appear side-by-side
- Summary list: place as a flat section below the columns — it takes full width

## Styling

- Counter tiles: card container with soft shadow, border-radius, and internal padding. Background neutral-0 or neutral-1. Icon on the left or top, value prominently sized
- Charts: card container with title heading and padding. Ensure minimum height for readability (~300px)
- Summary list: compact table with striping for readability, or card-based list items
- Trend indicators: semantic colors — green/success for positive, red/error for negative, neutral for flat
- Grid: use gutter-m or gutter-base between columns. Add phone-break-all for responsive stacking

## Data Patterns

- **KPI values:** each headline number comes from a stored metric entity, or from a seed that produces exactly the value the design shows. Never a live count over a tiny seed (a "1,284 clients" tile must not render "5").
- Charts need aggregated/grouped data — typically a separate data source per chart with appropriate grouping, seeded so the chart matches the design
- Summary list: sorted by date descending or by priority, limited to 5-10 rows (no pagination needed)

## When the design leaves a region unspecified

Only then, use the data model to fill it:

1. **Charts**: a `Status`, `State`, `Type`, `Category`, `Priority`, or `Level` attribute → Bar or Donut chart grouping records by that attribute; a `CreatedAt`, `Date`, or datetime attribute → Line chart over time
2. **Summary list**: the entity with a date/time attribute, 5-10 most recent records: name/title + status + date

Never add charts, lists or tiles the design doesn't have.

## Responsive Behavior

- Desktop: 3-4 column KPI grid, 2-column charts, full-width summary
- Tablet: 2-column KPI grid, charts stack vertically
- Phone: single-column everything, charts full-width, summary list simplified
