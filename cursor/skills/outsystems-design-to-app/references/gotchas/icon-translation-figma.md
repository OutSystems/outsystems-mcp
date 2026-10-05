# Figma React sources use Lucide — translate to Phosphor

**The trap:** Most Figma-Make / Figma-React / shadcn-ui sources use [Lucide Icons](https://lucide.dev/) — rendered with `class="lucide lucide-<name>"` and an `<svg>` body. OutSystemsUI doesn't ship Lucide — it ships **Phosphor Icons**. If you carry Lucide class names verbatim into the spec, the icons don't render, or end up as raw inline `<svg>` with unreliable colour (see [`svg-icon-baking.md`](svg-icon-baking.md)).

**The fix:** translate each Lucide occurrence to its Phosphor equivalent and use it on an OutSystemsUI Icon widget (bare name). Inline SVG is the fallback only when no Phosphor match exists. Don't try to add Lucide as a second library — too much theme integration work.

## Detection

Search the source markup (the Figma design-context code, or the HTML / TSX file) for `lucide lucide-<name>` classes, or for `lucide-react` imports in code.

If you see any matches, the source is Lucide-based and you must translate each one.

## Lucide → Phosphor translation table (the common ones)

| Lucide | Phosphor | Notes |
|---|---|---|
| `lucide-layout-dashboard` | `squares-four` | Dashboard tile grid |
| `lucide-users` | `users` | Plural users / clients |
| `lucide-user` | `user` | Single user |
| `lucide-user-plus` | `user-plus` | Add user / prospect |
| `lucide-briefcase` | `briefcase` | Portfolio / AuM |
| `lucide-calendar` | `calendar-blank` | Or `calendar` for one with grid |
| `lucide-clock` | `clock` | Time / appointment |
| `lucide-bell` | `bell` | Notifications (use `bell-ringing` for active alerts) |
| `lucide-circle-alert` | `warning-circle` | Alert / warning state |
| `lucide-info` | `info` | Info tooltip |
| `lucide-chart-column` | `chart-bar` | Vertical bar chart |
| `lucide-chart-line` | `chart-line` | Line chart (use `chart-line-up` for positive-trend) |
| `lucide-trending-up` | `trend-up` | Positive metric delta |
| `lucide-trending-down` | `trend-down` | Negative metric delta |
| `lucide-target` | `target` | Goal / pipeline stage |
| `lucide-eye` | `eye` | View / preview |
| `lucide-search` | `magnifying-glass` | Search |
| `lucide-mail` | `envelope` | Email |
| `lucide-phone` | `phone` | Phone call |
| `lucide-video` | `video-camera` | Video call |
| `lucide-settings` | `gear` | Settings / config (or `gear-six`) |
| `lucide-log-out` | `sign-out` | Sign out |
| `lucide-plus` | `plus` | Add / create |
| `lucide-arrow-right` | `arrow-right` | Trailing arrow on action links |
| `lucide-chevron-right` | `caret-right` | |
| `lucide-message-circle` | `chat-circle` | Single chat / message |
| `lucide-message-square` | `chats` | Multiple messages |
| `lucide-file-text` | `file-text` | Document / report |
| `lucide-handshake` | `handshake` | Meeting / partnership |
| `lucide-house` | `house` | Home / dashboard |

If the source uses an icon not on this list, browse [phosphoricons.com](https://phosphoricons.com/) for the closest match. There are 1500+ Phosphor icons; almost everything Lucide has an equivalent.

## How to apply in the spec.json

For each Lucide icon in the source, the anatomy node uses a **real OutSystemsUI Icon widget** with the bare Phosphor name as its `Icon` property (e.g., `Icon="squares-four"`, not `"ph-squares-four"` or `"ph ph-squares-four"`). `<i class="ph ph-X">` font icons DON'T render in ODC (see [`svg-icon-baking.md`](svg-icon-baking.md)). Only if no Phosphor match exists, fall back to an inline `<svg>` with an explicit `fill` (white for dark containers).

In the `spec.json`'s top-level `icon_mapping` field, record translations so Mentor can apply them consistently:

```json
"icon_mapping": [
  { "role": "navigation-dashboard", "outsystems_icon": "squares-four" },
  { "role": "navigation-clients", "outsystems_icon": "users" },
  { "role": "kpi-delta-positive", "outsystems_icon": "trend-up" }
]
```
