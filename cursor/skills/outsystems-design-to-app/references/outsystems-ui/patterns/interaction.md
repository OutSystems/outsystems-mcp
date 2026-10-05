---
name: osui-interaction-patterns
description: OutSystems UI interaction patterns — DatePicker, DropdownSearch, DropdownServerSide, Carousel, Sidebar, BottomSheet, Notification, OverflowMenu, RangeSlider, StackedCards, etc. Use when adding overlays, pickers, dropdowns, gestures, or animated/live controls to a screen.
---

# Interaction Patterns

> **Category:** Interaction — overlays, inputs, gestures, and live controls.
> **Module:** OutSystemsUI

Patterns covered: `ActionSheet`, `Animate`, `AnimatedLabel`, `BottomSheet`, `Carousel`, `DatePicker`, `DatePickerRange`, `DropdownSearch`, `DropdownTags`, `DropdownServerSide`, `FloatingActions`, `InputWithIcon`, `LightboxImage`, `MonthPicker`, `Notification`, `OverflowMenu`, `RangeSlider`, `RangeSliderInterval`, `ScrollableArea`, `Search`, `Sidebar`, `StackedCards`, `TimePicker`, `Video`.

For the widget hierarchy and reference entity values, see `../ui-reference.md`. `Dropdown` and `Popup` are platform widgets, not OS UI blocks.

## Requirement → block

| Requirement | Block |
|---|---|
| Side panel that slides in | `Sidebar` |
| Bottom panel that slides up | `BottomSheet` |
| Bottom-anchored action menu (≤5 buttons) | `ActionSheet` |
| Floating action button (FAB) with sub-actions | `FloatingActions` |
| Toast notification (auto-dismiss) | `Notification` |
| Single-date picker | `DatePicker` |
| Date-range picker | `DatePickerRange` |
| Month/year picker | `MonthPicker` |
| Time picker | `TimePicker` |
| Searchable single-select | `DropdownSearch` |
| Searchable multi-select with tags | `DropdownTags` |
| Server-side / very large option list (single or multi-select) | `DropdownServerSide` + `DropdownServerSideItem` |
| Single-value slider | `RangeSlider` |
| Two-handle interval slider | `RangeSliderInterval` |
| Carousel / image slideshow | `Carousel` |
| Tinder-style swipe cards | `StackedCards` |
| Scrollable region with custom scrollbar | `ScrollableArea` |
| Click-thumbnail-to-zoom | `LightboxImage` |
| "⋯" / popover menu of actions anchored to a trigger | `OverflowMenu` |
| Input with leading/trailing icon | `InputWithIcon` |
| Search input | `Search` (or `InputWithIcon` with a search icon) |
| Input with floating animated label | `AnimatedLabel` |
| Entrance/exit animation wrapper | `Animate` |
| HTML5 video player | `Video` |

## Opening and closing overlays

Sidebar / BottomSheet / Notification / Popup share one shape:

1. **Initial state** — `Sidebar.StartsOpen` / `Notification.StartsOpen` set whether the block starts open. `BottomSheet` has no open input. `Popup` (platform widget) is bound to a Boolean local variable through `ShowPopup`.
2. **Open / close at runtime** — triggers (buttons elsewhere on the screen) call the block's OutSystems UI client action: `SidebarOpen` / `SidebarClose`, `BottomSheetOpen` / `BottomSheetClose`, `NotificationOpen` / `NotificationClose`, each taking the block's widget id as `WidgetId`. For `Popup`, assign the bound variable `True` / `False`. `ActionSheet` is the exception: it has a bound `IsOpen` input (see below).
3. **Keep state in sync** — handle the block's `OnToggle` event when the screen needs to know whether it is open.

This pattern applies to every overlay below unless noted otherwise.

## Sidebar

Slide-out side panel.

| Parameter | Type | Purpose |
|---|---|---|
| `Sidebar.StartsOpen` | Boolean | Initial open state. |
| `Sidebar.Direction` | `Entities.Direction` | `Left` or `Right`. |
| `Sidebar.Width` | Text (CSS) | e.g. `"320px"`. |
| `Sidebar.HasOverlay` | Boolean | Show backdrop. |
| `Sidebar.ExtendedClass` | Text | Extra CSS. |

| Placeholder | Contents |
|---|---|
| `Sidebar.Header` | Title + close icon (calls the close client action). |
| `Sidebar.Content` | Body — typically a list, menu, or form. |

**Event** `Sidebar.OnToggle` — payload `IsOpen` (Boolean), `SidebarId` (Text). Fires when the sidebar opens or closes (button click, overlay tap, swipe). Handler typically assigns the `IsOpen` payload to a local variable.

## BottomSheet

Slide-up panel from the bottom of the screen. Opened/closed through the OutSystems UI client actions (see [Opening and closing overlays](#opening-and-closing-overlays)) — there is no `IsOpen` input.

| Parameter | Type | Purpose |
|---|---|---|
| `BottomSheet.Shape` | `Entities.Shape` | Corner shape of the sheet. |
| `BottomSheet.ShowHandler` | Boolean | Show the drag handle. |
| `BottomSheet.ExtendedClass` | Text | Extra CSS. |

| Placeholder | Contents |
|---|---|
| `BottomSheet.TopBar` | Header row (title, close icon). |
| `BottomSheet.Content` | Body. |

**Event** `BottomSheet.OnToggle` — payload `IsOpen` (Boolean), `BottomSheetId` (Text).

## ActionSheet

Bottom-anchored action menu with up to 5 button slots.

| Parameter | Type | Purpose |
|---|---|---|
| `ActionSheet.IsOpen` | Boolean (required) | Visibility; bind it to a local variable. |
| `ActionSheet.ExtendedClass` | Text | Extra CSS. |

| Placeholder | Contents |
|---|---|
| `ActionSheet.Button1`–`Button5` | One Button per slot. |

Event `ActionSheet.OnClose` (no payload): set the bound variable back to `False` in it.

## FloatingActions

Speed-dial floating action button group. Shows/hides sub-actions on hover/click of the main FAB.

| Parameter | Type | Purpose |
|---|---|---|
| `FloatingActions.IsHover` | Boolean | Open sub-actions on hover (vs click). |
| `FloatingActions.ExtendedClass` | Text | Extra CSS. |

| Placeholder | Contents |
|---|---|
| `FloatingActions.Button` | The main FAB content (icon). |
| `FloatingActions.Items` | One `FloatingActionsItem` per sub-action. |

**`FloatingActionsItem`** placeholders: `Item` (the sub-action icon/button), `Label` (its text).

## Notification

Toast-style notification.

| Parameter | Type | Purpose |
|---|---|---|
| `Notification.StartsOpen` | Boolean | Initial visibility. |
| `Notification.Position` | `Entities.Position` | Where the toast anchors (default `Top`). Values: `Top`, `Bottom`, `Center`, `Left`, `Right`, `TopLeft`, `TopRight`, `BottomLeft`, `BottomRight`. |
| `Notification.Width` | Text (CSS) | Default `"370px"`. |
| `Notification.OptionalConfigs` | Record | Misc — auto-dismiss delay, animation. |

| Placeholder | Contents |
|---|---|
| `Notification.Content` | Toast body (icon + text + optional close X). |

**Events**

| Event | Payload | Purpose |
|---|---|---|
| `Notification.OnToggle` | `IsOpen` (Boolean) | Toast opened or closed (auto-dismiss or manual). |
| `Notification.Initialized` | `NotificationId` (Text) | Notification finished initializing. |

Compare: **`Alert`** is inline; **`Notification`** is a corner toast; **`Popup`** is a modal.

## Carousel

Horizontal slide gallery.

| Parameter | Type | Purpose |
|---|---|---|
| `Carousel.Navigation` | `Entities.CarouselNavigation` | `Arrows` · `Dots` · `Both` · `None`. |
| `Carousel.Height` | Text (CSS) | Slide height, e.g. `"300px"` or `"auto"`. |
| `Carousel.ItemsPerSlide` | `CarouselItems` record (`Desktop`, `Tablet`, `Phone`) | Responsive items-per-slide, e.g. Desktop 3 / Tablet 2 / Phone 1. **Defaults to 1-per-slide if omitted** — set this whenever the design shows multiple cards visible at once (gallery row, peek/overlap of neighboring cards). NOT an integer. |
| `Carousel.OptionalConfigs` | `CarouselOptionalConfigs` record | `{ AutoPlay: Boolean, Loop: Boolean, … }`. Does NOT contain items-per-slide fields — those live on the dedicated `ItemsPerSlide` input above. |
| `Carousel.ExtendedClass` | Text | Extra CSS. |

| Placeholder | Contents |
|---|---|
| `Carousel.CarouselItems` | Flat list of items, OR a `List` for data-bound slides. **Your content REPLACES the default**; the slide/navigation behavior remains intact. |

**Events**

| Event | Payload | Purpose |
|---|---|---|
| `Carousel.OnSlideMoved` | `ItemIndex` (Integer), `CarouselId` (Text) | Active slide changed. |
| `Carousel.Initialized` | `CarouselId` (Text) | Carousel finished initializing. |

For slides bound to data, place a `List` inside `Carousel.CarouselItems` — each list iteration becomes one slide.

## DatePicker

Single-date picker. The bound `Input` (Date or DateTime) goes in the `Datepicker` placeholder.

| Parameter | Type | Purpose |
|---|---|---|
| `DatePicker.DateFormat` | Text | e.g. `"DD/MM/YYYY"` or `"yyyy-MM-dd"`. |
| `DatePicker.ShowTodayButton` | Boolean | Show "Today" shortcut. |
| `DatePicker.TimeFormat` | `DatePickerTimeFormat` Identifier | Default `Entities.DatePickerTimeFormat.Disabled`; `Time24hFormat` / `Time12hFormat` to add time selection. |
| `DatePicker.OptionalConfigs` | Record | `{ ShowWeekNumbers, FirstDayOfWeek, MinDate, MaxDate, … }`. |
| `DatePicker.ExtendedClass` | Text | Extra CSS. |

| Placeholder | Contents |
|---|---|
| `DatePicker.Datepicker` | The `Input` bound to a Date / DateTime variable (e.g. `SelectedDate`). |

**Event** `DatePicker.OnSelected` — payload `SelectedDateTime` (Date Time). Assign the payload to the bound variable.

## DatePickerRange

Date-range picker. The bound `Input` goes in the `Datepicker` placeholder.

| Parameter | Type | Purpose |
|---|---|---|
| `DatePickerRange.DateFormat` | Text | Display format, e.g. `"DD/MM/YYYY"`. |
| `DatePickerRange.ShowTodayButton` | Boolean | "Today" shortcut. |
| `DatePickerRange.OptionalConfigs` | Record | Same as `DatePicker`. |
| `DatePickerRange.ExtendedClass` | Text | Extra CSS. |

| Placeholder | Contents |
|---|---|
| `DatePickerRange.Datepicker` | The `Input` bound to the range start variable. |

**Event** `DatePickerRange.OnSelected` — payload `SelectedStartDate`, `SelectedEndDate`. Assign each to its variable.

Use `DatePickerRange` (single block) for ranges — never two `DatePicker`s.

## MonthPicker

Month/year selector. The bound `Input` goes in the `MonthPicker` placeholder.

| Parameter | Type | Purpose |
|---|---|---|
| `MonthPicker.DateFormat` | Text | Display format, e.g. `"MM/YYYY"`. |
| `MonthPicker.InitialMonth` | MonthYear | Initially selected month. |
| `MonthPicker.MinMonth` | MonthYear | Earliest selectable month. |
| `MonthPicker.MaxMonth` | MonthYear | Latest selectable month. |
| `MonthPicker.ExtendedClass` | Text | Extra CSS. |

| Placeholder | Contents |
|---|---|
| `MonthPicker.MonthPicker` | The bound `Input`. |

Event `MonthPicker.OnSelected` — payload `SelectedMonth`.

## TimePicker

Time selector. The bound `Input` goes in the `Timepicker` placeholder.

| Parameter | Type | Purpose |
|---|---|---|
| `TimePicker.TimeFormat` | Text | Display format, e.g. `"HH:mm"`. |
| `TimePicker.InitialTime` | Time expression | Initial value (`"CurrTime()"`, `"#14:30:00#"`). |
| `TimePicker.Is24Hours` | Boolean | `True` for 24h, `False` for 12h with AM/PM. |
| `TimePicker.OptionalConfigs` | Record | Step interval, min/max time. |
| `TimePicker.ExtendedClass` | Text | Extra CSS. |

| Placeholder | Contents |
|---|---|
| `TimePicker.Timepicker` | The bound `Input`. |

Event `TimePicker.OnSelected` — payload `SelectedTime`.

## DropdownSearch

Searchable single-select dropdown bound to an aggregate. No placeholders.

| Parameter | Type | Purpose |
|---|---|---|
| `DropdownSearch.OptionsList` | Record List | Options to display — typed as `<Structure> List` (e.g. a custom `StatusOption` Structure with `Value`/`Label` attributes), or `ConvertList(<Aggregate>.List, { Value: "<Id>", Label: "<DisplayText>" })`. |
| `DropdownSearch.StartingSelection` | Text or Identifier | Initial value (matches an option's `Value`). |
| `DropdownSearch.Prompt` | Text | Placeholder text, e.g. `"Select…"`. |
| `DropdownSearch.OptionalConfigs` | Record | `{ NoResultsText, SearchPrompt, IsDisabled, … }`. |
| `DropdownSearch.ExtendedClass` | Text | Extra CSS. |

**Events**

| Event | Status | Purpose |
|---|---|---|
| `DropdownSearch.OnChanged` | **MANDATORY** | Fires when selection changes. Always wire a handler. |
| `DropdownSearch.Initialized` | Optional | Block finished initializing. |

The `OnChanged` handler is required for the block to function — without it, selections aren't propagated to your model.

**Composition**

- Define a Structure with `Value` and `Label` attributes (or use `ConvertList` to map an aggregate into that shape).
- Maintain selection in a LocalVariable matching the `Value` type.

### Dropdown widget vs DropdownSearch block

These are different things — don't confuse them:

| | `Dropdown` (platform widget) | `DropdownSearch` (OutSystems UI block) |
|---|---|---|
| Data source | `List` = `<Aggregate>.List` | `OptionsList` = a `DropdownOption List` |
| Variable type | MUST be Identifier (e.g. `ProductId`) | Any matching the option `Value` |
| Use for | Simple entity selection | Searchable, complex dropdown |

If you see error `'OptionsList' requires a value of 'DropdownOption List' data type`, you've mixed the two — pick one.

## DropdownTags

Multi-select dropdown rendering selected values as removable chips.

Same arguments and event shape as `DropdownSearch`. The `OnChanged` payload contains the full list of currently-selected options.

## DropdownServerSide

Use when the option list is too big to fetch upfront, or each option needs custom content. Options are `DropdownServerSideItem` blocks (typically inside a `List`), not an `OptionsList`.

| Parameter | Type | Purpose |
|---|---|---|
| `DropdownServerSide.AllowMultipleSelection` | Boolean | Multi-select (replaces the old "MultipleSelection" variants). |
| `DropdownServerSide.IsDisabled` | Boolean | Disable the dropdown. |
| `DropdownServerSide.ExtendedClass` | Text | Extra CSS. |

| Placeholder | Contents |
|---|---|
| `DropdownServerSide.SelectedValues` | What the closed dropdown shows (selected label / chips). |
| `DropdownServerSide.BalloonSearchInput` | Search `Input` inside the open balloon. |
| `DropdownServerSide.BalloonSearchInputIcon` | Icon beside the search input. |
| `DropdownServerSide.BalloonContent` | The options — `DropdownServerSideItem` blocks. |
| `DropdownServerSide.BalloonFooter` | Optional footer (Apply / Clear buttons). |

Events: `OnToggle`, `Initialized`.

**`DropdownServerSideItem`** — inputs `ItemId` (required), `IsSelected`; placeholder `DropdownItemContent`; event `OnSelected`.

Filtering / loading more is your own logic: the search input's `OnChange` refreshes the aggregate that feeds the items.

## RangeSlider

Single-value slider. No placeholders.

| Parameter | Type | Purpose |
|---|---|---|
| `RangeSlider.MinValue` | Decimal | Lower bound (`"0"`). |
| `RangeSlider.MaxValue` | Decimal | Upper bound (`"100"`). |
| `RangeSlider.StartingValue` | Decimal expression | Initial value (typically a local variable like `SliderValue`). |
| `RangeSlider.Orientation` | `Entities.Orientation` | `Horizontal` or `Vertical`. |
| `RangeSlider.Size` | Text (CSS) | Track length: `"300px"` or `"100%"`. |
| `RangeSlider.OptionalConfigs` | Record | Step, pips, tooltip configuration. |
| `RangeSlider.ExtendedClass` | Text | Extra CSS. |

**Event** `RangeSlider.OnValueChange` — **MANDATORY**. Wire a handler that assigns the new value to your local variable.

## RangeSliderInterval

Two-handle interval slider — pick a range with `From` and `To` handles.

| Parameter | Type | Purpose |
|---|---|---|
| `RangeSliderInterval.MinValue` | Decimal | Lower bound. |
| `RangeSliderInterval.MaxValue` | Decimal | Upper bound. |
| `RangeSliderInterval.StartingValueFrom` | Decimal | Initial lower handle. |
| `RangeSliderInterval.StartingValueTo` | Decimal | Initial upper handle. |
| `RangeSliderInterval.OptionalConfigs` | Record | Step, pips, tooltip. |
| `RangeSliderInterval.ExtendedClass` | Text | Extra CSS. |

Event `RangeSliderInterval.OnValueChange` — payload `IntervalStart`, `IntervalEnd` (Decimal). Wire a handler that updates the bound start/end variables.

Use `RangeSlider` for a single value; `RangeSliderInterval` for a range.

## ScrollableArea

Scrollable container with customizable scrollbar.

| Parameter | Type | Purpose |
|---|---|---|
| `ScrollableArea.ScrollbarStyle` | Identifier | Style of the scrollbar (slim, hidden, default). |
| `ScrollableArea.Orientation` | `Entities.Orientation` | Scroll direction. |
| `ScrollableArea.Height` | Text (CSS) | Fixed height (required for vertical scroll). |
| `ScrollableArea.Width` | Text (CSS) | Fixed width (for horizontal scroll). |
| `ScrollableArea.ExtendedClass` | Text | Extra CSS. |

| Placeholder | Contents |
|---|---|
| `ScrollableArea.Content` | Long content. |

## InputWithIcon

Input with a leading or trailing icon.

| Parameter | Type | Purpose |
|---|---|---|
| `InputWithIcon.AlignIconRight` | Boolean | `True` = trailing icon, `False` = leading icon. |
| `InputWithIcon.ExtendedClass` | Text | Extra CSS. |

| Placeholder | Contents |
|---|---|
| `InputWithIcon.Icon` | The icon widget. |
| `InputWithIcon.Input` | The Input widget bound to your variable. |

## AnimatedLabel

Input with a floating label that animates on focus.

| Placeholder | Contents |
|---|---|
| `AnimatedLabel.Label` | The `Label` widget that floats. |
| `AnimatedLabel.Input` | The `Input` widget. |

## Search

Search input block (current, not deprecated). Put the bound `Input` in its `Input` placeholder; handle filtering in the input's `OnChange`.

| Placeholder | Contents |
|---|---|
| `Search.Input` | The search `Input`. |

## LightboxImage

Click-thumbnail-to-zoom.

| Parameter | Type | Purpose |
|---|---|---|
| `LightboxImage.ImageURL` | Text | Full-size image shown in the lightbox. |
| `LightboxImage.Group` | Text | Group name — images with the same group page together. |
| `LightboxImage.Title` | Text | Caption. |
| `LightboxImage.ImageZoom` | Boolean | Allow zoom inside the lightbox. |

| Placeholder | Contents |
|---|---|
| `LightboxImage.Thumbnail` | The thumbnail `Image` widget. |

## OverflowMenu

"⋯" menu / popover-style panel of actions anchored to a trigger. There is no `Popover` block — use this, or a `Tooltip` with `Trigger=Entities.Trigger.OnClick` for short info.

| Parameter | Type | Purpose |
|---|---|---|
| `OverflowMenu.BalloonPosition` | Identifier | Where the menu opens relative to the trigger. |
| `OverflowMenu.BalloonShape` | Identifier | Corner shape of the menu. |
| `OverflowMenu.ExtendedClass` | Text | Extra CSS. |

| Placeholder | Contents |
|---|---|
| `OverflowMenu.TriggerContent` | The trigger (e.g. an `Icon` `dots-three`). |
| `OverflowMenu.Menu` | The menu items (`Link` / `Button` widgets). |

Event `OverflowMenu.OnMenuToggle` (`OverflowMenuId`, `IsOpen`) — fires when the menu opens or closes.

## StackedCards

Swipeable card stack (mostly a phone pattern).

| Parameter | Type | Purpose |
|---|---|---|
| `StackedCards.StackedOptions` | `StackedCardsPosition` Identifier | Where the stack is anchored (default `Bottom`). |
| `StackedCards.Items` | Integer | How many cards show in the stack (default 5). |
| `StackedCards.ElementsMargin` | Integer | Spacing between stacked cards (default 5). |
| `StackedCards.Rotate` | Boolean | Rotate cards while swiping (default True). |
| `StackedCards.UseOverlays` | Boolean | Show the swipe overlays (default True). |
| `StackedCards.ExtendedClass` | Text | Extra CSS. |

| Placeholder | Contents |
|---|---|
| `StackedCards.Content` | The cards (typically a `List`). |
| `StackedCards.OverlayLeft` / `OverlayRight` / `OverlayTop` | What shows while a card is swiped that way. |

Events: `OnLeftSwipe`, `OnRightSwipe`, `OnTopSwipe`, `OnItemChange`, each with `CurrentPosition` (Integer).

## Animate

Wraps content in an entrance animation.

| Parameter | Type | Purpose |
|---|---|---|
| `Animate.AnimationType` | `Entities.AnimationType` | `FadeIn`, `Scale`, `LeftToRight`, `Bounce`, `Spinner`, … |
| `Animate.Speed` | `Entities.Speed` | `Slow` · `Normal` · `Fast`. |

| Placeholder | Contents |
|---|---|
| `Animate.Content` | The content to animate. |

## Video

HTML5 video player.

| Parameter | Type | Purpose |
|---|---|---|
| `Video.URL` | Text | Video URL. |
| `Video.Height` | Text (CSS) | Player height. |
| `Video.Width` | Text (CSS) | Player width. |
| `Video.Controls` | Boolean | Show native controls. |
| `Video.Captions` | Text | Captions file URL. |
| `Video.OptionalConfigs` | Record | Extra player options. There are no `Autoplay` / `Loop` / `Mute` inputs. |
| `Video.ExtendedClass` | Text | Extra CSS. |

Event `Video.StateChanged` — fires on play / pause / end.

**Programmatic control** via the OutSystemsUI client actions `VideoPlay` / `VideoPause` — a Button's `OnClick` calls the client action.

## Cross-cutting rules

1. **Overlays follow one open/close pattern** — see [Opening and closing overlays](#opening-and-closing-overlays). Don't reach into the block's internal DOM.
2. **Pickers wrap a bound `Input`.** `DatePicker` / `DatePickerRange` (`Datepicker` placeholder), `MonthPicker` (`MonthPicker`), `TimePicker` (`Timepicker`) hold the `Input` bound to your variable; read the chosen value in `OnSelected`. `RangeSlider` and `DropdownSearch` are argument-only (`OnValueChange` / `OnChanged`).
3. **`Tooltip.Content` is the anchor, `Tooltip.Tooltip` is the popup body** — see [`content.md#tooltip`](./content.md#tooltip).
4. **`DropdownSearch` / `DropdownTags` need an `OptionsList` shaped as a `<Structure> List`** with `Value`/`Label` attributes. Use a Structure or `ConvertList(...)` to transform entity records. `DropdownServerSide` has no `OptionsList` — its options are `DropdownServerSideItem` blocks.
5. **`DropdownSearch.OnChanged` is mandatory.** Without a handler the selection isn't propagated.
6. **`RangeSlider.OnValueChange` is mandatory.** Without a handler the new value isn't propagated.
7. **`Carousel.CarouselItems` accepts a flat list or a `List`.** For dynamic data, use a `List`.

## Accessibility notes

- All overlays trap focus while open and restore it on close. Don't break this by manually moving focus.
- Pickers expose date/time as standard `<input>` elements via the placeholder. Keyboard users can type the value directly.
- `Carousel` advances on Arrow keys when focused. Ensure each slide has a meaningful `aria-label`.
- `Notification` uses `aria-live="polite"` (assertive for `Error` types). Don't change `aria-live` manually.
- `Sidebar`/`BottomSheet`/`Popup` close on Esc by default. Don't override the close handler unless you handle Esc yourself.
- `RangeSlider` exposes `aria-valuenow`/`aria-valuemin`/`aria-valuemax`. Don't use a non-standard slider implementation.
