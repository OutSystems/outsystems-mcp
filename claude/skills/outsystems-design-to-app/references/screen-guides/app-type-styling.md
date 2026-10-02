# Application-Type Styling Guide

## Universal Modern Design Rules

These rules apply to ALL application types. Violating them makes the UI feel dated regardless of the domain.

### Color Palette
- **1 brand color + neutrals + max 2-3 semantic colors**. No rainbow palettes or ad hoc accents
- Warm colors (red, orange) ONLY for errors, warnings, and destructive actions — never decorative
- Semantic colors: success (green), warning (amber/yellow), error (red), info (blue) — used consistently for status, not branding

### Typography
- 1-2 type families maximum. 3 size/weight variations: heading, subheading, body
- Body line-height ≥ 1.5 for readability
- Text hierarchy: headings in text-neutral-9/10, body in text-neutral-8, secondary/muted in text-neutral-7, disabled in text-neutral-5

### Spacing & Grid
- **8pt grid**: all spacing uses multiples of 8 (8, 16, 24, 32, 40, 48px)
- Consistent radius: one border-radius value across all surfaces (don't mix 0/4/8/16px)
- Shadows: soft (spread + blur, low opacity). Hard drop shadows = dated

### Icons
- One icon style per UI zone: outline for navigation/interactive, filled for content/illustration is fine
- Icons must be recognizable at the size used. Abstract icons need text labels
- Consistent icon sizing: use grid-aligned sizes (16, 20, 24px)

### Interaction Targets
- Touch targets ≥ 44px on mobile, ≥ 32px on desktop primary actions
- ≥ 8px gap between adjacent interactive targets
- Labels extend hit zones on checkboxes and radio buttons

### Visual Hierarchy
- One clear primary CTA per screen; secondary actions visually lighter; destructive actions separated
- Color contrast WCAG AA: 4.5:1 for body text, 3:1 for large text and UI components
- Never use color as the sole differentiator for status or errors — always pair with icon, text, or pattern

## How to Determine Application Type

1. Examine existing entities: product/cart/order/payment → ecommerce; contact/lead/pipeline → CRM; policy/audit/incident → compliance
2. Examine the app theme and existing screens for visual direction
3. If ambiguous, ask the user

## Ecommerce / Marketplace

- **Color palette**: Warm accent (coral, orange, or brand-specific) for CTAs and pricing highlights. Clean white/neutral backgrounds for product focus. Success green for "in stock" / "added to cart"
- **Key patterns**: Product cards with image + title + price + rating + CTA. Hero banners. Cart summary sidebar. Price display with original/sale formatting. Wishlist/favorite icons
- **ThemeValues**: color-primary → brand accent, border-radius-soft → 8-12px (rounder cards for friendly feel), shadow-s → softer elevation
- **Layout**: Gallery grid for product browsing (3-4 columns). Single-column checkout flow. Sticky cart summary on desktop

## CRM / Business Operations

- **Color palette**: Professional blues and grays. Minimal accent colors. Status-driven color coding (pipeline stages, deal status). Neutral backgrounds
- **Key patterns**: Data tables with sortable columns and inline actions. Status pills/tags (Tag pattern). Pipeline/kanban board. Activity timeline. Contact/company detail cards with labeled fields
- **ThemeValues**: color-primary → professional blue (#2563EB or similar), space-base → 16px (standard density)
- **Layout**: List screens with advanced filters. Master-detail for record management. Dashboard with KPIs and pipeline chart

## Compliance / Internal Tools

- **Color palette**: Neutral tones (neutral-1 through neutral-3 backgrounds). Muted semantic colors for status. Minimal brand presence — function over form
- **Key patterns**: Dense data tables (table-row-small) for audit trails and regulation lists. Form-heavy edit screens with section grouping. Approval workflow indicators. Document version lists. Multi-section detail views with tabs
- **ThemeValues**: font-base-size → 14px (higher density), space-base → 12px (tighter spacing for data-dense views)
- **Layout**: Sidebar navigation for modules. Two-column forms. Data-dense list screens with multiple filter dimensions

## Consumer / Social / Lifestyle

- **Color palette**: Vibrant primary color. Generous whitespace and breathing room. Playful accent colors for engagement features (likes, achievements, badges)
- **Key patterns**: Card-based feeds (CardBackground for hero/image cards). Avatar + content layouts. Floating action buttons. Image-heavy galleries. Rating and review patterns. Achievement/badge displays. Personalized greeting cards
- **ThemeValues**: border-radius-soft → 12-16px (rounded, friendly feel), shadow-s → subtle soft elevation, space-base → 20-24px (generous spacing)
- **Layout**: Single-column feed. Card grids with generous gutter-l. Bottom navigation on mobile. Full-bleed hero images

## Healthcare / Clinical

- **Color palette**: Calm blues and teals. High-contrast text for critical data. Error red reserved strictly for clinical alerts/warnings
- **Key patterns**: Patient detail cards with vital signs. Timeline for medical history. Status indicators with high-contrast colors. Form-heavy intake/assessment screens. Alert banners for critical information
- **ThemeValues**: color-primary → calm blue or teal, font-base-size → 15-16px (readability critical)
- **Layout**: Dashboard with patient metrics. Master-detail for patient records. Timeline for visit history. Dense but readable tables for lab results
