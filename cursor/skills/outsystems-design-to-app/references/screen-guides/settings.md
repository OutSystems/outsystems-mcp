# Settings / Preferences Screen

## Anatomy

A configuration screen for user, account, or application settings. Organized by categories with forms for each.

1. **Settings navigation** (left sidebar or top tabs):
   - Category list: Profile, Notifications, Security, Appearance, Integrations, etc.
   - Active category highlighted
   - Badge indicators for categories needing attention (e.g., unverified email)
2. **Settings content** (right panel): Form for the selected category:
   - **Section heading** (heading4) for the category name
   - **Setting groups**: Related settings grouped under heading5 subheadings with description text
   - **Setting rows**: Each setting as a labeled control:
     - Toggle switches (Switch widget) for on/off settings
     - Dropdowns for selection settings (language, timezone, theme)
     - Text inputs for value settings (display name, email)
     - Radio buttons for mutually exclusive choices
   - **Save behavior**: Auto-save per setting (with subtle "Saved" confirmation), OR explicit "Save Changes" button per section
3. **Danger zone** (bottom of relevant sections): Destructive actions styled differently:
   - "Delete Account", "Reset Settings" in error/destructive button style
   - Confirmation required before execution

## Layout

- Desktop: sidebar navigation (ColumnsSmallLeft — ~25% left, ~75% right). Sidebar scrollable if many categories
- Tablet: same split but narrower sidebar
- Phone: category list as top-level screen; selecting a category navigates to a full-screen settings form. Back button to return to category list

## Styling

- Sidebar: background-neutral-1, padding-base. Active item: background-neutral-0 or left border in primary color
- Settings content: background-neutral-0, padding-m
- Setting rows: each row with padding-s vertically, border-bottom divider between settings
- Toggle labels: regular weight, aligned left. Toggle control aligned right
- Danger zone: separated by margin-top-xl, optional background-error with low opacity, text-error for destructive action labels
- Auto-save confirmation: small text "Saved" in text-success, appearing briefly next to the changed setting

## Data Patterns

- Initial load: fetch current settings values from user profile / app configuration
- Auto-save: on each toggle/dropdown change, save immediately via server action. Show inline confirmation
- Explicit save: collect all changed values, save on button click, show success feedback
- Validation: validate email format, password requirements, etc. before saving

## Responsive Behavior

- Desktop: sidebar + content split
- Phone: navigation list → content form (two-screen pattern)
