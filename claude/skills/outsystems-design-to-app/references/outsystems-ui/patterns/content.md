---
name: osui-content-patterns
description: OutSystems UI content patterns — Accordion, Alert, BlankSlate, Card, CardItem, CardBackground, CardSectioned, ChatMessage, FlipContent, FloatingContent, ListItemContent, Section, SectionGroup, Tag, Tooltip, UserAvatar. Use when adding surfaces, grouping containers, or contextual feedback to a screen.
---

# Content Patterns

> **Category:** Content — surfaces, grouping, and presentational containers.
> **Module:** OutSystemsUI

Patterns covered: `Accordion`, `AccordionItem`, `Alert`, `BlankSlate`, `Card`, `CardBackground`, `CardItem`, `CardSectioned`, `ChatMessage`, `FlipContent`, `FloatingContent`, `ListItemContent`, `Section`, `SectionGroup`, `Tag`, `Tooltip`, `UserAvatar`.

For format conventions (FULL PATH parameters, required `Arguments: []` and `PlaceholdersContent: []`), see `../ui-reference.md`.

## Requirement → block

| Requirement | Block(s) |
|---|---|
| Generic surface to wrap content | `Card` |
| List row with avatar + title + body + action | `CardItem` (standalone) or `ListItemContent` (inside `IList`) |
| Hero card with background image | `CardBackground` |
| Image-on-top card | `CardSectioned` (vertical) |
| Image-on-side card | `CardSectioned` (horizontal) |
| Collapsible sections (FAQ, settings groups) | `Accordion` + `AccordionItem` |
| Titled grouped section | `Section` |
| Multiple `Section`s with sticky index | `SectionGroup` |
| Inline contextual feedback | `Alert` |
| Empty state ("no results") | `BlankSlate` |
| Hover/focus tooltip | `Tooltip` |
| Floating panel anchored to a trigger | `FloatingContent` |
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
| `AccordionItem.Icon` | Text | `"\"Caret\""` | Icon name as a quoted string (`"\"Caret\""`, `"\"PlusMinus\""`, `"\"Custom\""`). |
| `AccordionItem.IconPosition` | Text | `"\"right\""` | Lowercase quoted string: `"\"left\""` or `"\"right\""`. |
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
- For lazy-loading expensive content, wire an `OnToggle` ScreenAction (per-item `IsExpanded` LocalVariable) and gate the inner content with `IfWidget`.


## Alert

Inline contextual feedback (success/warning/error/info).

**Arguments**

| Parameter | Type | Purpose |
|---|---|---|
| `Alert.AlertType` | `Entities.Alert` | `Success` · `Error` · `Warning` · `Info`. |
| `Alert.IsDismissible` | Boolean | Show close X. |
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

Wrap inside `IfWidget(<Aggregate>.IsDataFetched and <Aggregate>.List.Empty)` to show only after the fetch completes — otherwise it flashes during loading.

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
| `CardBackground.MinHeight` | Text (CSS) | Minimum height, e.g. `"\"300px\""`. |
| `CardBackground.ExtendedClass` | Text | Extra CSS. |

| Placeholder | Contents |
|---|---|
| `CardBackground.BackgroundImage` | An `IImage` widget (the image rendered behind). |
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
| `CardSectioned.Image` | `IImage`/`IVideo`/visual element. |
| `CardSectioned.Title` | Title text/widgets. |
| `CardSectioned.Content` | Body. |
| `CardSectioned.Footer` | Actions, metadata. |

## ChatMessage

Chat bubble.

| Parameter | Type | Purpose |
|---|---|---|
| `ChatMessage.MessageStatus` | Identifier | `Sent` · `Delivered` · `Read`. |
| `ChatMessage.IsRight` | Boolean | `True` = current user (right-aligned). |
| `ChatMessage.ExtendedClass` | Text | Extra CSS. |

| Placeholder | Contents |
|---|---|
| `ChatMessage.MessageText` | Message body. |
| `ChatMessage.Actions` | Inline actions (react, reply). |

## FlipContent

Flippable two-sided card.

| Parameter | Type | Default | Purpose |
|---|---|---|---|
| `FlipContent.StartsFlipped` | Boolean | `False` | Initial side. |
| `FlipContent.FlipOnClick` | Boolean | `True` | Click to flip. |
| `FlipContent.ExtendedClass` | Text | `""` | Extra CSS. |

| Placeholder | Contents |
|---|---|
| `FlipContent.Front` | Front content (typically a `Card`/`CardSectioned`). |
| `FlipContent.Back` | Back content. |

## FloatingContent

Anchored overlay (lighter than `Popup`, no backdrop).

| Parameter | Type | Purpose |
|---|---|---|
| `FloatingContent.Position` | `Entities.Position` | Where the overlay opens relative to the trigger. |
| `FloatingContent.UseFullWidth` | Boolean | Match trigger width. |
| `FloatingContent.UseMargin` | Boolean | Add gap between trigger and overlay. |
| `FloatingContent.ExtendedClass` | Text | Extra CSS. |

| Placeholder | Contents |
|---|---|
| `FloatingContent.Trigger` | Anchor element (button, icon, text). |
| `FloatingContent.Content` | Overlay body. |

## ListItemContent

Use **inside** an `IList` (or `ListItem`) — it's the row content, not a standalone surface.

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

Titled grouping container with optional Actions area.

| Parameter | Type | Default | Purpose |
|---|---|---|---|
| `Section.UsePadding` | Boolean | `True` | Inner padding around content. |
| `Section.ExtendedClass` | Text | `""` | Extra CSS. |

| Placeholder | Contents |
|---|---|
| `Section.Title` | Heading text. |
| `Section.Actions` | Action buttons / links rendered alongside the title (e.g. "View All"). |
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

Inline label / chip. No placeholder for content beyond text — pass children inside `Tag.Content`.

| Parameter | Type | Purpose |
|---|---|---|
| `Tag.Color` | `Entities.Color` | Tint. |
| `Tag.Size` | `Entities.Size` | `Small` · `Medium`. |
| `Tag.IsLight` | Boolean | Lighter background variant. |
| `Tag.Shape` | `Entities.Shape` | `Rounded` · `Sharp` · `SoftRounded`. |
| `Tag.ExtendedClass` | Text | Extra CSS. |

| Placeholder | Contents |
|---|---|
| `Tag.Content` | Label text. |

Tag vs `Badge`: Tag is a labelled chip ("Active", "Beta"); Badge is a numeric count ("12 unread").

## Tooltip

Hover/focus popup with extra info.

| Parameter | Type | Default | Purpose |
|---|---|---|---|
| `Tooltip.StartsOpen` | Boolean | `False` | Initial open state. |
| `Tooltip.Position` | `Entities.Position` | — | Where the popup appears relative to the trigger. `Top`, `Bottom`, `Left`, `Right`. |
| `Tooltip.Trigger` | `Entities.Trigger` | — | `Entities.Trigger.Hover` or `Entities.Trigger.Click`. |
| `Tooltip.ExtendedClass` | Text | `""` | Extra CSS. |

| Placeholder | Contents |
|---|---|
| `Tooltip.Content` | The popup body — the message shown when hovered/clicked. |
| `Tooltip.Trigger` | The anchor element (the thing the user hovers/clicks to reveal the tooltip). |

> **Watch out:** the placeholder names are non-obvious. `Tooltip.Content` is the *popup body*, and `Tooltip.Trigger` is the *anchor*. Easy to swap by mistake.

**Events**

| Event | Payload | Purpose |
|---|---|---|
| `Tooltip.OnToggle` | `IsOpened` (Boolean), `TooltipId` (Text) | Tooltip opened or closed. |
| `Tooltip.Initialized` | `TooltipId` (Text) | Block finished initializing. |

Tooltip body should be short. For dense help, use `FloatingContent` or a `Popover`.

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

1. **`*.Content` is the canonical placeholder name** for the main slot of single-slot blocks.
2. **Card variants are not interchangeable.** `CardItem` and `ListItemContent` look similar but `CardItem` is standalone, `ListItemContent` only goes inside an `IList`.
3. **Don't put a card inside a card.** Pick one variant.
4. **Tag and Badge are inline.** Place them inside table cells, list rows, or beside text — not as block-level page sections.
5. **Tooltip's placeholders are easy to confuse:** `Tooltip.Content` holds the *popup body* (the help message), `Tooltip.Trigger` holds the *anchor* (the hover target). Get them right.

## Accessibility notes

- `Accordion` titles are `<button>` elements with `aria-expanded` and `aria-controls`. Don't replace the title placeholder with a non-interactive widget.
- `Alert` carries `role="alert"` for `Error`/`Warning` types. Don't override.
- `BlankSlate` is decorative — its message text is read by screen readers but the icon should have empty alt text.
- `Tooltip` activates on focus as well as hover (keyboard-friendly). Don't disable focus styling on the trigger.
- `UserAvatar` uses the `Name` argument as the image alt text fallback. Always pass a real name.
