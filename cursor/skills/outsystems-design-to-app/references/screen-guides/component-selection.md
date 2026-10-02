# Component Selection Guide

Choose the right UI component for the content and interaction pattern. Using the wrong component causes usability failures regardless of styling.

## Data Display

| Content Type | Correct Component | Wrong Choice |
|---|---|---|
| Tabular data (structured rows/columns, 10+ items) | Data table (TableRecords) with sort, filter, pagination | Cards (too much scrolling, no column comparison) |
| Image-heavy browsing (products, files, team) | Card grid (Gallery block or responsive card layout) | Table (images don't fit tabular layout) |
| Hierarchical data (org chart, file tree) | Tree view or nested list with expand/collapse | Flat table (loses hierarchy) |
| Key metrics at a glance | Counter tiles or KPI cards | Table row with numbers (no visual weight) |
| Trends over time | Line or area chart | Table of numbers (pattern invisible) |
| Part-of-whole comparison | Donut or pie chart | Bar chart (harder to see proportions) |
| Category comparison | Bar or column chart | Pie chart (hard to compare similar values) |

## Navigation & Organization

| Pattern | Correct Component | Wrong Choice |
|---|---|---|
| Mutually exclusive content sections | Tabs (Tabs block) | Stacked accordions (forces users to manage open/close state) |
| Supplementary/optional content | Accordion (Accordion block) | Tabs (hides content that may need simultaneous viewing) |
| Sequential flow | Wizard with step indicator | Single long form (overwhelming) |
| Breadcrumb trail for deep navigation | Breadcrumbs (Breadcrumbs block) | Back button only (loses context) |
| Date selection | Date picker (DatePicker block) | Free text input (error-prone formatting) |
| Date range selection | Date range picker (DatePickerRange block) | Two separate date pickers (disconnected UX) |

## Form Controls

| Input Need | Correct Component | Wrong Choice |
|---|---|---|
| Select one from 2-5 options | Radio buttons (RadioGroup) | Dropdown (overhead for few options) |
| Select one from 6+ options | Dropdown (Dropdown widget) or search dropdown (DropdownSearch block) | Radio buttons (too much vertical space) |
| Select one from 20+ options | Searchable dropdown (DropdownSearch block) | Plain dropdown (hard to find items) |
| Select multiple from any set | Checkboxes (Checkbox widgets) | Radio buttons (single-select only — misuse) |
| Boolean on/off | Toggle switch (Switch widget) | Checkbox (switches convey immediate effect) |
| Long text | Text area (TextArea widget) | Single-line input (truncates content) |
| Free text where structured input exists | N/A — use the structured component | Free text input (error-prone) |

## Actions & Feedback

| Interaction | Correct Component | Wrong Choice |
|---|---|---|
| Single primary action | Button (btn-primary) | Link styled as button (inconsistent affordance) |
| Related actions (2-3) | Button group or split button | Separate scattered buttons (no grouping) |
| Destructive action confirmation | Custom modal with clear explanation | Browser dialog / window.confirm() (not branded, no context) |
| Secondary information on hover | Tooltip (Tooltip block) | Modal (too heavy for glanceable info) |
| Detailed preview on hover | Popover / hover card | Modal (interrupts flow) |
| Status indicators | Tags/badges with semantic colors | Plain text (no visual weight) |
| Inline simple messages | Toast / snackbar notification | Full modal (too disruptive for simple confirmation) |

## Universal Rules

- Same action = same control everywhere. Don't mix toggles and checkboxes for the same purpose on the same screen
- Labels always persistent above inputs — never use placeholder text as the only label (disappears on entry)
- Checkboxes for multi-select, radio buttons for single-select — never misuse
- Goal-oriented search (finding a specific item) → pagination. Casual browsing → infinite scroll is acceptable
- Progressive disclosure for complex forms: show only relevant fields per step, not all at once
