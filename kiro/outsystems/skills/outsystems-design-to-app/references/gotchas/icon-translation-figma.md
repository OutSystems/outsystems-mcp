# Figma React sources use Lucide — translate to Phosphor

**The trap:** Most Figma-Make / Figma-React / shadcn-ui sources use [Lucide Icons](https://lucide.dev/) — rendered with `class="lucide lucide-<name>"` and an `<svg>` body. OutSystemsUI doesn't ship Lucide — it ships **Phosphor Icons**. If you carry Lucide class names verbatim into the spec, the icons render as raw `<svg>` (no glyph translation), and you've also re-introduced the SVG bake problem (see [`svg-icon-baking.md`](svg-icon-baking.md)).

**The fix:** translate each Lucide occurrence to its Phosphor equivalent in the spec.json. Don't try to add Lucide as a second library — too much theme integration work.

## Detection

```bash
grep -oE 'lucide lucide-[a-z-]+' /tmp/oml-source/rendered.html | sort -u
```

If you see any matches, the source is Lucide-based and you must translate each one.

## Lucide → Phosphor translation table (the common ones)

| Lucide | Phosphor | Notes |
|---|---|---|
| `lucide-layout-dashboard` | `ph-squares-four` | Dashboard tile grid |
| `lucide-users` | `ph-users` | Plural users / clients |
| `lucide-user` | `ph-user` | Single user |
| `lucide-user-plus` | `ph-user-plus` | Add user / prospect |
| `lucide-briefcase` | `ph-briefcase` | Portfolio / AuM |
| `lucide-calendar` | `ph-calendar-blank` | Or `ph-calendar` for one with grid |
| `lucide-clock` | `ph-clock` | Time / appointment |
| `lucide-bell` | `ph-bell` | Notifications (use `ph-bell-ringing` for active alerts) |
| `lucide-circle-alert` | `ph-warning-circle` | Alert / warning state |
| `lucide-info` | `ph-info` | Info tooltip |
| `lucide-chart-column` | `ph-chart-bar` | Vertical bar chart |
| `lucide-chart-line` | `ph-chart-line` | Line chart (use `ph-chart-line-up` for positive-trend) |
| `lucide-trending-up` | `ph-trend-up` | Positive metric delta |
| `lucide-trending-down` | `ph-trend-down` | Negative metric delta |
| `lucide-target` | `ph-target` | Goal / pipeline stage |
| `lucide-eye` | `ph-eye` | View / preview |
| `lucide-search` | `ph-magnifying-glass` | Search |
| `lucide-mail` | `ph-envelope` | Email |
| `lucide-phone` | `ph-phone` | Phone call |
| `lucide-video` | `ph-video-camera` | Video call |
| `lucide-settings` | `ph-gear` | Settings / config (or `ph-gear-six`) |
| `lucide-log-out` | `ph-sign-out` | Sign out |
| `lucide-plus` | `ph-plus` | Add / create |
| `lucide-arrow-right` | `ph-arrow-right` | Trailing arrow on action links |
| `lucide-chevron-right` | `ph-caret-right` | |
| `lucide-message-circle` | `ph-chat-circle` | Single chat / message |
| `lucide-message-square` | `ph-chats` | Multiple messages |
| `lucide-file-text` | `ph-file-text` | Document / report |
| `lucide-handshake` | `ph-handshake` | Meeting / partnership |
| `lucide-house` | `ph-house` | Home / dashboard |

If the source uses an icon not on this list, browse [phosphoricons.com](https://phosphoricons.com/) for the closest match. There are 1500+ Phosphor icons; almost everything Lucide has an equivalent.

## How to apply in the spec.json

For each Lucide icon in the source, the anatomy node specifies the Phosphor equivalent — but remember that **`<i class="ph ph-X">` font icons DON'T render** in ODC's SPA runtime (see [`svg-icon-baking.md`](svg-icon-baking.md) §3). The agent should either:

1. Emit an **inline `<svg>`** with the Phosphor glyph's path data + explicit `fill` (white for dark containers).
2. OR use a **real OutSystemsUI Icon widget** with the bare Phosphor name as the `Icon` property (e.g., `Icon="squares-four"`, not `"ph-squares-four"` or `"ph ph-squares-four"`). The OutSystemsUI Icon widget handles the rendering; this is the preferred path when the source name maps cleanly.

In the `spec.json`'s `design_system.icon_mapping` field, record translations as a dict so Mentor can apply them consistently:

```json
"icon_mapping": {
  "lucide-layout-dashboard": "squares-four",
  "lucide-users": "users",
  "lucide-trending-up": "trend-up",
  ...
}
```

## Bonus: weight modifiers

The default Phosphor weight is `regular`. For thinner / bolder strokes:
- Thin: `ph-thin` modifier class
- Bold: `ph-bold`
- Fill: `ph-fill`

Pick the weight that matches the source's visual style.

## Attribution

- [`claude-oml-tool/oml-tool/skills/odc/validated/phosphor-icons.md`](https://github.com/OutSystems/claude-oml-tool/blob/main/oml-tool/skills/odc/validated/phosphor-icons.md) — Phosphor 2.0 names validated against the OutSystemsUI plugin DLL's 1512-name catalog
