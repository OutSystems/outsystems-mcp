---
name: osui-content-patterns
description: OutSystems UI content patterns — Accordion, Alert, BlankSlate, Card, CardItem, CardBackground, CardSectioned, ChatMessage, FlipContent, FloatingContent, ListItemContent, Section, SectionGroup, Tag, Tooltip, UserAvatar. Use when adding surfaces, grouping containers, or contextual feedback to a screen.
---

# Content Patterns

> **Category:** Content — surfaces, grouping, and presentational containers.
> **Module:** OutSystemsUI

Patterns covered: `Accordion`, `AccordionItem`, `Alert`, `BlankSlate`, `Card`, `CardBackground`, `CardItem`, `CardSectioned`, `ChatMessage`, `FlipContent`, `FloatingContent`, `ListItemContent`, `Section`, `SectionGroup`, `Tag`, `Tooltip`, `UserAvatar`.

For the widget hierarchy, anti-patterns and `Entities` values, see `../ui-reference.md`.

## Requirement → block

| Requirement | Block(s) |
|---|---|
| Generic surface to wrap content | `Card` |
| List row with avatar + title + body + action | `CardItem` (standalone) or `ListItemContent` (inside `List`) |
| Hero card with background image | `CardBackground` |
| Image-on-top card | `CardSectioned` (vertical) |
| Image-on-side card | `CardSectioned` (horizontal) |
| Collapsible sections (FAQ, settings groups) | `Accordion` + `AccordionItem` |
| Titled grouped section | `Section` |
| Multiple `Section`s with sticky index | `SectionGroup` |
| Inline contextual feedback | `Alert` |
| Empty state ("no results") | `BlankSlate` |
| Hover/focus tooltip | `Tooltip` |
| Floating panel pinned to a screen position | `FloatingContent` |
| Inline label / chip | `Tag` |
| Chat message bubble | `ChatMessage` |
| Flip card animation | `FlipContent` |
| User photo with initials fallback | `UserAvatar` |

## Accordion + AccordionItem

Vertically stacked collapsible sections.

**`Accordion` arguments**

| Parameter | Type | Default | Purpose |
|---|---|---|---|
| `Accordion.MultipleItems` | Boolean | `False` | Allow multiple items expanded at once. |
| `Accordion.ExtendedClass` | Text | `""` | Extra CSS classes. |

**`Accordion` placeholders**

| Placeholder | Contents |
|---|---|
| `Accordion.Content` | One or more `AccordionItem` blocks. |

**`AccordionItem` arguments**

| Parameter | Type | Default | Purpose |
|---|---|---|---|
| `AccordionItem.StartsExpanded` | Boolean | `False` | Initial expanded state. |
| `AccordionItem.IsDisabled` | Boolean | `False` | Disables the toggle. |
| `AccordionItem.Icon` | `AccordionIconType` Identifier | `Entities.AccordionIconType.Caret` | `Caret` · `PlusMinus` · `Custom`. |
| `AccordionItem.IconPosition` | `AccordionIconPosition` Identifier | `Entities.AccordionIconPosition.Right` | `Left` · `Right`. |
| `AccordionItem.ExtendedClass` | Text | `""` | Extra CSS classes. |

**`AccordionItem` placeholders**

| Placeholder | Contents |
|---|---|
| `AccordionItem.Title` | Header text/widgets. |
| `AccordionItem.Content` | Body shown when expanded. |
| `AccordionItem.CustomIcon` | Optional override icon. |

**Composition**

- `Accordion.Content` MUST contain `AccordionItem` children — nothing else.
- Don't nest an `Accordion` inside another `Accordion`.
- For lazy-loading expensive content, handle the item's `OnToggle` (keep a per-item `IsExpanded` local variable) and gate the inner content with an `If`.


## Alert

Inline contextual feedback (success/warning/error/info).

**Arguments**

| Parameter | Type | Purpose |
|---|---|---|
| `Alert.AlertType` | `Entities.Alert` | `Success` · `Error` · `Warning` · `Info`. |
| `Alert.ExtendedClass` | Text | Extra CSS classes. |

**Placeholders**

| Placeholder | Contents |
|---|---|
| `Alert.MessageText` | Message body (text or rich content). The placeholder is `MessageText`, **not** `Content`. |

**Use Alert vs `Notification` vs `Popup`:** Alert sits inline in the page (use for "your password is too short"); Notification toasts in the corner and auto-dismisses; Popup is modal (blocks the page).

## BlankSlate

Empty-state block: shown when an aggregate returns no rows or before a user has done something.

**Arguments**

| Parameter | Type | Purpose |
|---|---|---|
| `BlankSlate.FullHeight` | Boolean | Stretches to fill parent vertically. |
| `BlankSlate.ExtendedClass` | Text | Extra CSS classes. |

**Placeholders**

| Placeholder | Contents |
|---|---|
| `BlankSlate.Icon` | Icon or illustration. |
| `BlankSlate.Content` | Heading + body text. |
| `BlankSlate.Actions` | Buttons that move the user out of the empty state ("Create one"). |

**Composition**

Wrap inside an `If` (`<Aggregate>.IsDataFetched and <Aggregate>.List.Empty`) to show only after the fetch completes — otherwise it flashes during loading.

## Card / CardItem / CardBackground / CardSectioned

Four card variants for different layouts.

| Block | When |
|---|---|
| `Card` | Generic content surface, single placeholder. |
| `CardItem` | Row layout: Left (icon/avatar) · Title · Content · Right (action). Standalone. |
| `CardBackground` | Hero with background image and overlay content. |
| `CardSectioned` | Image + Title + Content + Footer with vertical or horizontal split. |

### Card

| Parameter | Type | Default | Purpose |
|---|---|---|---|
| `Card.UsePadding` | Boolean | `True` | Adds inner padding. |
| `Card.ExtendedClass` | Text | `""` | Extra CSS classes. |

| Placeholder | Contents |
|---|---|
| `Card.Content` | Anything. **Don't** wrap in another `Container` — put widgets directly. |

### CardItem

Single placeholder per zone — all four exist.

| Placeholder | Contents |
|---|---|
| `CardItem.Left` | Icon, avatar, or thumbnail. |
| `CardItem.Title` | Primary text. |
| `CardItem.Content` | Secondary text. |
| `CardItem.Right` | Action button or status badge. |

### CardBackground

| Parameter | Type | Purpose |
|---|---|---|
| `CardBackground.Color` | `Entities.Color` or hex | Background tint when image fails. |
| `CardBackground.MinHeight` | Integer | Minimum height in px, e.g. `300`. |
| `CardBackground.ExtendedClass` | Text | Extra CSS. |

| Placeholder | Contents |
|---|---|
| `CardBackground.BackgroundImage` | An `Image` widget (the image rendered behind). |
| `CardBackground.Content` | Overlay text/buttons. |

### CardSectioned

| Parameter | Type | Default | Purpose |
|---|---|---|---|
| `CardSectioned.IsVertical` | Boolean | `True` | Vertical = image on top. Horizontal = image on left. |
| `CardSectioned.UsePadding` | Boolean | `True` | Inner padding around title/content/footer. |
| `CardSectioned.ImagePadding` | Boolean | `True` | Padding around the image cell. |
| `CardSectioned.ExtendedClass` | Text | `""` | Extra CSS. |

| Placeholder | Contents |
|---|---|
| `CardSectioned.Image` | `Image` or other visual element. |
| `CardSectioned.Title` | Title text/widgets. |
| `CardSectioned.Content` | Body. |
| `CardSectioned.Footer` | Actions, metadata. |

## ChatMessage

Chat bubble.

| Parameter | Type | Purpose |
|---|---|---|
| `ChatMessage.MessageStatus` | Identifier (required) | Delivery status of the message. |
| `ChatMessage.DisplayOnRight` | Boolean | `True` = current user (right-aligned). |
| `ChatMessage.Time` | Text | Timestamp shown with the message. |
| `ChatMessage.ExtendedClass` | Text | Extra CSS. |

| Placeholder | Contents |
|---|---|
| `ChatMessage.Content` | Message body. |
| `ChatMessage.Image` | Sender avatar / image. |

## FlipContent

Flippable two-sided card.

| Parameter | Type | Default | Purpose |
|---|---|---|---|
| `FlipContent.StartsFlipped` | Boolean | `False` | Initial side. |
| `FlipContent.FlipOnClick` | Boolean | `True` | Click to flip. |
| `FlipContent.ExtendedClass` | Text | `""` | Extra CSS. |

| Placeholder | Contents |
|---|---|
| `FlipContent.CardFront` | Front content (typically a `Card`/`CardSectioned`). |
| `FlipContent.CardBack` | Back content. |

Event `FlipContent.OnFlip` — fires when the card flips.

## FloatingContent

Content that floats over the page at a fixed screen position (no backdrop). For a panel anchored to a trigger element, use `OverflowMenu` or `Tooltip` (see [`interaction.md#overflowmenu`](./interaction.md#overflowmenu)).

| Parameter | Type | Purpose |
|---|---|---|
| `FloatingContent.Position` | `Entities.Position` (required) | Where on the screen the content floats. |
| `FloatingContent.ExtendedClass` | Text | Extra CSS. |

| Placeholder | Contents |
|---|---|
| `FloatingContent.Content` | The floating content. |

## ListItemContent

Use **inside** a `List` (or `ListItem`) — it's the row content, not a standalone surface.

| Parameter | Type | Purpose |
|---|---|---|
| `ListItemContent.ExtendedClass` | Text | Extra CSS. |

| Placeholder | Contents |
|---|---|
| `ListItemContent.Left` | Icon / avatar. |
| `ListItemContent.Title` | Primary text. |
| `ListItemContent.Content` | Secondary text. |
| `ListItemContent.Right` | Action / status / chevron. |

For a standalone card row outside a list, use `CardItem`.

## Section

Titled grouping container.

| Parameter | Type | Default | Purpose |
|---|---|---|---|
| `Section.UsePadding` | Boolean | `True` | Inner padding around content. |
| `Section.ExtendedClass` | Text | `""` | Extra CSS. |

| Placeholder | Contents |
|---|---|
| `Section.Title` | Heading text. A title-row action ("View All") goes inside `Title` (or `Content`) — there is no `Actions` placeholder. |
| `Section.Content` | Section body. |

## SectionGroup

Groups multiple `Section` blocks; can render a sticky index.

| Parameter | Type | Default | Purpose |
|---|---|---|---|
| `SectionGroup.HasStickyTitles` | Boolean | `True` | Show sticky index of section titles on the side. |
| `SectionGroup.ExtendedClass` | Text | `""` | Extra CSS. |

| Placeholder | Contents |
|---|---|
| `SectionGroup.Sections` | One or more `Section` children. |

## Tag

Inline label / chip. The label goes in the `Tag` placeholder.

| Parameter | Type | Purpose |
|---|---|---|
| `Tag.Color` | `Entities.Color` | Tint. |
| `Tag.Size` | `Entities.Size` | `Small` · `Medium`. |
| `Tag.IsLight` | Boolean | Lighter background variant. |
| `Tag.Shape` | `Entities.Shape` | `Rounded` · `Sharp` · `SoftRounded`. |
| `Tag.ExtendedClass` | Text | Extra CSS. |

| Placeholder | Contents |
|---|---|
| `Tag.Tag` | Label text. |

Tag vs `Badge`: Tag is a labelled chip ("Active", "Beta"); Badge is a numeric count ("12 unread").

## Tooltip

Hover/click popup with extra info.

| Parameter | Type | Default | Purpose |
|---|---|---|---|
| `Tooltip.Trigger` | `Trigger` Identifier | `Entities.Trigger.OnHover` | `OnHover` or `OnClick`. This is an **input**, not a placeholder. |
| `Tooltip.Position` | `Entities.Position` | `Right` | Where the popup appears relative to the anchor. |
| `Tooltip.StartsOpen` | Boolean | `False` | Initial open state. |
| `Tooltip.ExtendedClass` | Text | `""` | Extra CSS. |

| Placeholder | Contents |
|---|---|
| `Tooltip.Content` | The anchor element (the thing the user hovers/clicks). |
| `Tooltip.Tooltip` | The popup body — the message shown when open. |

**Events**

| Event | Payload | Purpose |
|---|---|---|
| `Tooltip.OnToggle` | `IsOpened` (Boolean), `TooltipId` (Text) | Tooltip opened or closed. |
| `Tooltip.Initialized` | `TooltipId` (Text) | Block finished initializing. |

Tooltip body should be short. For a click-open menu of actions, use `OverflowMenu` (see [`interaction.md#overflowmenu`](./interaction.md#overflowmenu)).

## UserAvatar

User photo with initials fallback. No placeholders — entirely argument-driven.

| Parameter | Type | Purpose |
|---|---|---|
| `UserAvatar.Name` | Text | Display name (drives initials when no image). |
| `UserAvatar.Image` | Binary | Avatar image. |
| `UserAvatar.Color` | `Entities.Color` | Background color for initials. |
| `UserAvatar.Size` | `Entities.Size` | `Small` · `Medium`. |
| `UserAvatar.Shape` | `Entities.Shape` | `Rounded` (circle) · `SoftRounded` (squircle) · `Sharp` (square). |
| `UserAvatar.IsLight` | Boolean | Lighter color variant. |
| `UserAvatar.ExtendedClass` | Text | Extra CSS. |

## Cross-cutting rules

1. **`*.Content` is the usual placeholder name** for the main slot of single-slot blocks — exceptions: `Alert.MessageText`, `Tag.Tag`.
2. **Card variants are not interchangeable.** `CardItem` and `ListItemContent` look similar but `CardItem` is standalone, `ListItemContent` only goes inside a `List`.
3. **Don't put a card inside a card.** Pick one variant.
4. **Tag and Badge are inline.** Place them inside table cells, list rows, or beside text — not as block-level page sections.
5. **Tooltip's names are easy to confuse:** `Tooltip.Content` holds the *anchor*, `Tooltip.Tooltip` holds the *popup body*, and `Trigger` is an input (`OnHover` / `OnClick`).

## Accessibility notes

- `Accordion` titles are `<button>` elements with `aria-expanded` and `aria-controls`. Don't replace the title placeholder with a non-interactive widget.
- `Alert` carries `role="alert"` for `Error`/`Warning` types. Don't override.
- `BlankSlate` is decorative — its message text is read by screen readers but the icon should have empty alt text.
- `Tooltip` activates on focus as well as hover (keyboard-friendly). Don't disable focus styling on the trigger.
- `UserAvatar` uses the `Name` argument as the image alt text fallback. Always pass a real name.
