---
name: osui-utilities-patterns
description: OutSystems UI utility patterns — AlignCenter, ButtonLoading, CenterContent, InlineSVG, MarginContainer, Separator, SwipeEvents, TouchEvents, MouseEvents. Use for small layout helpers, gesture detection, or visual dividers.
---

# Utility Patterns

> **Category:** Utilities — small building-block helpers used inside other patterns or screens.
> **Module:** OutSystemsUI

Patterns covered: `AlignCenter`, `ButtonLoading`, `CenterContent`, `InlineSVG`, `MarginContainer`, `MouseEvents`, `Separator`, `SwipeEvents`, `TouchEvents`.

## Requirement → block

| Requirement | Block |
|---|---|
| Center content (1D) | `AlignCenter` |
| Top/center/bottom layout in fixed height | `CenterContent` |
| Loading spinner inside a button | `ButtonLoading` |
| Constrain content width on wide screens | `MarginContainer` |
| Inline SVG (custom icon, illustration) | `InlineSVG` |
| Visual divider | `Separator` |
| Detect swipe gestures | `SwipeEvents` |
| Detect touch drag | `TouchEvents` |
| Detect mouse drag | `MouseEvents` |

## AlignCenter

Centers content along one axis.

| Parameter | Type | Default | Purpose |
|---|---|---|---|
| `AlignCenter.IsHorizontal` | Boolean | `True` | `True` = horizontal centering, `False` = vertical centering. |

| Placeholder | Contents |
|---|---|
| `AlignCenter.Content` | What to center. |

For both-axis centering, use `CenterContent` instead.

## ButtonLoading

Wraps a `Button` to swap its content for a spinner while loading.

| Parameter | Type | Purpose |
|---|---|---|
| `ButtonLoading.IsLoading` | Boolean | Bind to a LocalVariable. `True` → spinner. |
| `ButtonLoading.ShowLabelOnLoading` | Boolean | Keep the button label visible alongside the spinner. |

| Placeholder | Contents |
|---|---|
| `ButtonLoading.Button` | The Button widget. |

**Composition**

- Set `IsLoading = True` at the start of an async server action; reset to `False` in the end node (or the failure branch).
- Always pair with disabling the button click (`Enabled = not IsLoading`) to prevent double-submit.

## CenterContent

Three-zone vertical layout in a fixed-height container.

| Parameter | Type | Purpose |
|---|---|---|
| `CenterContent.Height` | Integer | Container height in pixels. |

| Placeholder | Contents |
|---|---|
| `CenterContent.Top` | Top-pinned content. |
| `CenterContent.Center` | Vertically-centered main content. |
| `CenterContent.Bottom` | Bottom-pinned content. |

Use for login screens, empty-state cards, and any "vertical center with header/footer" layout.

## InlineSVG

Renders raw SVG markup inline.

| Parameter | Type | Purpose |
|---|---|---|
| `InlineSVG.SVGCode` | Text | The complete SVG string (including `<svg>` tags). |

No placeholders. Use for custom icons or illustrations that need to be inline (rather than image files), e.g. for runtime color theming via CSS `currentColor`.

## MarginContainer

Wraps content with responsive horizontal margins so it doesn't span 100% on wide screens.

| Parameter | Type | Purpose |
|---|---|---|
| `MarginContainer.ExtendedClass` | Text | Extra CSS. |

| Placeholder | Contents |
|---|---|
| `MarginContainer.MarginContainer` | The content to constrain. |

Use at the top of `MainContent` on landing/marketing screens.

## Separator

Horizontal or vertical visual divider.

| Parameter | Type | Default | Purpose |
|---|---|---|---|
| `Separator.IsVertical` | Boolean | `False` | `True` = vertical line. |
| `Separator.Color` | `Entities.Color` | — | Line color. |
| `Separator.Space` | `Entities.Space` | — | Margin around the line. |

No placeholders. Self-contained.

## SwipeEvents

Invisible event listener that detects swipe gestures on a target widget.

| Parameter | Type | Purpose |
|---|---|---|
| `SwipeEvents.WidgetId` | Text | The `Name` of the target widget on the page. |

**Events**

| Event | Purpose |
|---|---|
| `SwipeEvents.SwipeUp` | User swiped up on target. |
| `SwipeEvents.SwipeDown` | User swiped down. |
| `SwipeEvents.SwipeLeft` | User swiped left. |
| `SwipeEvents.SwipeRight` | User swiped right. |

Place anywhere on the screen — placement doesn't matter, the binding is via `WidgetId`.

## TouchEvents

Continuous touch-drag detection.

| Parameter | Type | Purpose |
|---|---|---|
| `TouchEvents.WidgetId` | Text | Target widget `Name`. |
| `TouchEvents.PreventDefaults` | Boolean | Prevent default browser scroll behavior. |

Event `TouchEvents.Move` — payload `OffsetX`, `OffsetY`.

## MouseEvents

Continuous mouse-drag detection (desktop equivalent of `TouchEvents`).

| Parameter | Type | Purpose |
|---|---|---|
| `MouseEvents.WidgetId` | Text | Target widget `Name`. |

Event `MouseEvents.Move` — payload `OffsetX`, `OffsetY`.

## Cross-cutting rules

1. **Gesture event blocks (`SwipeEvents`, `TouchEvents`, `MouseEvents`) are invisible.** Don't try to style them — they emit no DOM beyond a script handle.
2. **`WidgetId` must match an existing widget's `Name` exactly.** If the name is misspelled, the event handler never fires.
3. **`Separator` and `InlineSVG` have no placeholders.** They're entirely argument-driven.
4. **`AlignCenter` is one-axis only.** For both-axis centering, use `CenterContent` (with header/footer empty if not needed).
5. **`MarginContainer` has a placeholder named `MarginContainer`** — the placeholder name matches the block name. This is unusual; double-check when writing the patch.

## Accessibility notes

- Gesture event blocks emit no semantic markup — they're pure JS handlers. Always provide a non-gesture fallback (button, link) so keyboard and assistive-tech users can perform the same action.
- `Separator` renders as `<hr>` (horizontal) or a styled `<span>` (vertical). Don't use it purely for spacing — use `MarginContainer` or token spacing classes for that.
- `InlineSVG` content is inserted as raw SVG. If the SVG conveys meaning, set `role="img"` and `aria-label` directly inside `SVGCode`. If purely decorative, set `aria-hidden="true"`.
