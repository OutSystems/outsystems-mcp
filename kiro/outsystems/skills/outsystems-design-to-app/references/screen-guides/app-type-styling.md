# Styling Defaults When the Design Is Silent

The design is the contract: take colours, type, spacing, radius and density from it. Use these defaults only for something the design leaves unspecified (a state it doesn't show, a colour it doesn't define), never to restyle what it does show.

- **Contrast (WCAG AA):** 4.5:1 for body text, 3:1 for large text and UI components. Light surfaces get dark text, dark surfaces get light text and light icons.
- **Never colour alone** for status or errors: pair the colour with an icon or text label.
- **Semantic colours** for undefined states: success (green), warning (amber), error (red), info (blue), used for status, not branding.
- **Text hierarchy** when the design gives none: headings `text-neutral-9`/`10`, body `text-neutral-8`, muted `text-neutral-7`, disabled `text-neutral-5`.
- **Touch targets** ≥ 44px on phone, ≥ 8px apart.
