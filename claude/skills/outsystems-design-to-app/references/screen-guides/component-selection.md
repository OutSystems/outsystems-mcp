# Component Selection Guide

Choose the right UI component for the content and interaction pattern when the design's intent is clear but the component isn't. Using the wrong component causes usability failures regardless of styling. For the block name behind a requirement keyword, see the Quick lookup in [`../outsystems-ui/ui-reference.md`](../outsystems-ui/ui-reference.md).

## Data Display

| Content Type | Correct Component | Wrong Choice |
|---|---|---|
| Tabular data (structured rows/columns, 10+ items) | TableRecords with sort, filter, Pagination | Cards (too much scrolling, no column comparison) |
| Image-heavy browsing (products, files, team) | Gallery block | Table (images don't fit tabular layout) |
| Hierarchical data (org chart, file tree) | Nested Accordion / AccordionItem, or an indented List | Flat table (loses hierarchy) |
| Key metrics at a glance | Counter tiles or KPI cards | Table row with numbers (no visual weight) |
| Trends over time | Line or area chart | Table of numbers (pattern invisible) |
| Part-of-whole comparison | Donut or pie chart | Bar chart (harder to see proportions) |
| Category comparison | Bar or column chart | Pie chart (hard to compare similar values) |

## Navigation & Organization

| Pattern | Correct Component | Wrong Choice |
|---|---|---|
| Mutually exclusive content sections | Tabs block | Stacked accordions (forces users to manage open/close state) |
| Supplementary/optional content | Accordion block | Tabs (hides content that may need simultaneous viewing) |
| Sequential flow | Wizard block | Single long form (overwhelming) |
| Deep navigation trail | Breadcrumbs block | Back button only (loses context) |
| Date / date range | DatePicker / DatePickerRange block | Free text input or two separate pickers |

## Form Controls

| Input Need | Correct Component | Wrong Choice |
|---|---|---|
| Select one from 2-5 options | RadioGroup | Dropdown (overhead for few options) |
| Select one from 6-20 options | Dropdown widget | Radio buttons (too much vertical space) |
| Select one from 20+ options | DropdownSearch block | Plain dropdown (hard to find items) |
| Select multiple from any set | Checkbox widgets (or DropdownTags) | Radio buttons (single-select only) |
| Boolean on/off | Switch widget | Checkbox (switches convey immediate effect) |
| Long text | TextArea widget | Single-line input (truncates content) |

## Actions & Feedback

| Interaction | Correct Component | Wrong Choice |
|---|---|---|
| Related actions (2-3) | ButtonGroup, or an OverflowMenu for secondary ones | Separate scattered buttons (no grouping) |
| Destructive action confirmation | Popup widget with clear explanation | Browser `window.confirm()` (not branded, no context) |
| Secondary information on hover | Tooltip block | Popup (too heavy for glanceable info) |
| Status indicators | Tag / Badge blocks with semantic colors | Plain text (no visual weight) |
| Transient confirmation | Notification block | Popup (too disruptive for simple confirmation) |
| Inline message in the page | Alert block | Notification (disappears before it is read) |
