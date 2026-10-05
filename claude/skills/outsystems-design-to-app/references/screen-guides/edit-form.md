# Edit / Create Form Screen

## Anatomy

A form screen for creating new records or editing existing ones. Expected sections:

1. **Page header**: Conditional title — "New [Entity]" in create mode, "Edit [Entity]" in edit mode. Optional breadcrumb trail
2. **Form container** (Form widget with card styling): Groups all input fields. Structure:
   - **Section headings** (heading5 or heading6): Group related fields under logical sections (e.g., "Basic Info", "Contact Details", "Address")
   - **Field rows**: Each field is a vertical group: Label above + Input below + validation message below input. Wrapped in a container with margin-bottom-base
   - **Foreign key fields**: Dropdown (Dropdown or DropdownSearch block) bound to related entity data source
   - **Boolean fields**: Toggle switch (Switch widget) or checkbox
   - **Multi-line text**: Text area (TextArea widget) with appropriate row count
3. **Button group**: At the bottom of the form, right-aligned:
   - "Cancel" button (secondary/cancel style) — navigates back without saving
   - "Save" / "Create" button (primary style) — validates and submits
   - Optional: "Save & Add Another" for batch creation flows
4. **Validation feedback**: Inline per-field validation messages. Form-level error summary at top if multiple errors

## Variants

- **Single-column** (default): For forms with up to 5-6 fields. Fields stacked vertically, full-width
- **Two-column**: For 6+ fields. Place related short fields side-by-side (e.g., First Name / Last Name, City / Postal Code). Use responsive columns (Columns2 block) that stack on phone
- **Tabbed**: For 10+ fields with distinct logical groups. Use tabs (Tabs block) with one section per tab. Show validation errors per tab with tab-level error indicator
- **Multi-step wizard**: For complex forms (see [wizard recipe](wizard.md)). Break into steps, validate per step

## Layout

- Form: card container with padding-base or padding-m, centered with max-width on desktop (avoid full-width stretched forms)
- Field rows: label above input (never placeholder-only labels). Margin-bottom-base between fields
- Two-column: equal columns with gutter-base. Stack on phone (phone-break-all)
- Button group: margin-top-l above buttons, right-aligned. Cancel on left, Primary on right

## Styling

- Form container: card styling with soft shadow, border-radius
- Labels: font-semi-bold, font-size smaller than input text. Linked to input via TargetWidget
- Mandatory indicator: asterisk or "(required)" text next to label
- Input fields: full-width within column, consistent sizing (form-control class)
- Validation errors: text-error color, font-size-xs, displayed below the input with margin-top-xs
- Disabled fields: visually distinct (reduced opacity, different background)

## Data Patterns

- Edit mode: aggregate to fetch existing record by Id (from input parameter). Pre-populate form fields with current values
- Create mode: empty local variable record. Set sensible defaults (current date, logged-in user as owner)
- Dropdown data sources: separate aggregates for each foreign key relationship
- On save: validate form, call server action (CreateOrUpdate), navigate to detail view on success, show error feedback on failure

## Responsive Behavior

- Desktop: two-column for 6+ fields, centered form with max-width
- Tablet: two-column preserved, slightly narrower
- Phone: all fields single-column, full-width. Button group stacks or stays side-by-side
