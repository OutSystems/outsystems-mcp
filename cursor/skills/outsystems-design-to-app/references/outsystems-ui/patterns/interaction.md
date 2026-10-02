---
name: osui-interaction-patterns
description: OutSystems UI interaction patterns — DatePicker, DropdownSearch, Carousel, Sidebar, BottomSheet, Notification, RangeSlider, StackedCards, etc. Use when adding overlays, pickers, dropdowns, gestures, or animated/live controls to a screen.
---

# Interaction Patterns

> **Category:** Interaction — overlays, inputs, gestures, and live controls.
> **Module:** OutSystemsUI

Patterns covered: `ActionSheet`, `Animate`, `AnimatedLabel`, `BottomSheet`, `Carousel`, `DatePicker`, `DatePickerRange`, `DropdownSearch`, `DropdownTags`, `DropdownServerSide` (5 variants), `FloatingActions`, `InputWithIcon`, `LightBoxImage`, `MonthPicker`, `Notification`, `RangeSlider`, `RangeSliderInterval`, `ScrollableArea`, `Search`, `Sidebar`, `StackedCards`, `TimePicker`, `Video`.

For format conventions and reference entity values, see `../ui-reference.md`.

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
| Server-paginated dropdown | `DropdownServerSide_*` |
| Single-value slider | `RangeSlider` |
| Two-handle interval slider | `RangeSliderInterval` |
| Carousel / image slideshow | `Carousel` |
| Tinder-style swipe cards | `StackedCards` |
| Scrollable region with custom scrollbar | `ScrollableArea` |
| Click-thumbnail-to-zoom | `LightBoxImage` |
| Input with leading/trailing icon | `InputWithIcon` |
| Search input | use `Input` with a search icon (the `Search` pattern is deprecated) |
| Input with floating animated label | `AnimatedLabel` |
| Entrance/exit animation wrapper | `Animate` |
| HTML5 video player | `Video` |

## The toggle pattern (used by ActionSheet / BottomSheet / Notification / Sidebar / Popup)

These overlays share one shape:

1. **LocalVariable** `IsOpen` (Boolean, default `False`).
2. **ScreenAction** `ToggleX` with one `AssignNode`: `IsOpen = not IsOpen`.
3. **The block** binds its visibility argument (`IsOpen` or `StartsOpen`) to the variable.
4. **Triggers** (buttons elsewhere on the screen) call `ToggleX` via `OnClick`.

This pattern is repeated for every overlay below — assume it unless noted otherwise.

## Sidebar

Slide-out side panel.

| Parameter | Type | Purpose |
|---|---|---|
| `Sidebar.StartsOpen` | Boolean | Bind to `IsOpen` LocalVariable. |
| `Sidebar.Direction` | `Entities.Direction` | `Left` or `Right`. |
| `Sidebar.Width` | Text (CSS) | e.g. `"\"320px\""`. |
| `Sidebar.HasOverlay` | Boolean | Show backdrop. |
| `Sidebar.ExtendedClass` | Text | Extra CSS. |

| Placeholder | Contents |
|---|---|
| `Sidebar.Header` | Title + close icon (wired to `ToggleSidebar`). |
| `Sidebar.Content` | Body — typically a list, menu, or form. |

**Event** `Sidebar.OnToggle` — payload `IsOpen` (Boolean), `SidebarId` (Text). Fires when the sidebar opens or closes (button click, overlay tap, swipe). Handler typically assigns the `IsOpen` payload to the bound LocalVariable. Pass with FULL PATH: `Parameter: "Sidebar.OnToggle.IsOpen"`.

## BottomSheet

Slide-up panel from the bottom of the screen.

| Parameter | Type | Purpose |
|---|---|---|
| `BottomSheet.IsOpen` | Boolean | Visibility — bind to LocalVariable. |
| `BottomSheet.ExtendedClass` | Text | Extra CSS. |

| Placeholder | Contents |
|---|---|
| `BottomSheet.Content` | Body. |

## ActionSheet

Bottom-anchored action menu with up to 5 button slots.

| Parameter | Type | Purpose |
|---|---|---|
| `ActionSheet.IsOpen` | Boolean | Visibility. |

| Placeholder | Contents |
|---|---|
| `ActionSheet.Button1`–`Button5` | One Button per slot. |

Event `ActionSheet.OnClose`.

## FloatingActions

Speed-dial floating action button group. Shows/hides sub-actions on hover/click of the main FAB.

| Parameter | Type | Purpose |
|---|---|---|
| `FloatingActions.IsHover` | Boolean | Open sub-actions on hover (vs click). |
| `FloatingActions.ExtendedClass` | Text | Extra CSS. |

| Placeholder | Contents |
|---|---|
| `FloatingActions.Content` | Sub-action buttons. |

## Notification

Toast-style notification.

| Parameter | Type | Purpose |
|---|---|---|
| `Notification.StartsOpen` | Boolean | Initial visibility — bind to LocalVariable. |
| `Notification.Position` | `Entities.Position` | Where the toast anchors. Common values: `Entities.Position.TopCenter`, `Entities.Position.BottomCenter`. |
| `Notification.Width` | Text (CSS) | e.g. `"\"400px\""` or `"\"auto\""`. |
| `Notification.OptionalConfigs` | Record | Misc — auto-dismiss delay, animation. |
| `Notification.ExtendedClass` | Text | Extra CSS. |

| Placeholder | Contents |
|---|---|
| `Notification.Content` | Toast body (icon + text + optional close X). |

**Events**

| Event | Payload | Purpose |
|---|---|---|
| `Notification.OnClose` | `NotificationId` (Text) | Toast closed (auto-dismiss or manual). |
| `Notification.Initialized` | `NotificationId` (Text) | Notification finished initializing. |

Compare: **`Alert`** is inline; **`Notification`** is a corner toast; **`Popup`** is a modal.

## Carousel

Horizontal slide gallery.

| Parameter | Type | Purpose |
|---|---|---|
| `Carousel.Navigation` | `Entities.CarouselNavigation` | `Arrows` · `Dots` · `Both` · `None`. |
| `Carousel.Height` | Text (CSS) | Slide height, e.g. `"\"300px\""` or `"\"auto\""`. |
| `Carousel.ItemsPerSlide` | Record `ItemsPerSlide{Desktop, Tablet, Phone}` | Responsive items-per-slide. Literal: `"ItemsPerSlide{Desktop:3, Tablet:2, Phone:1}"`. **Defaults to 1-per-slide if omitted** — set this whenever the design shows multiple cards visible at once (gallery row, peek/overlap of neighboring cards). NOT an integer. |
| `Carousel.OptionalConfigs` | Record `OptionalConfigsCarousel` | `{ AutoPlay: Boolean, Loop: Boolean, … }`. Does NOT contain items-per-slide fields — those live on the dedicated `ItemsPerSlide` input above. |
| `Carousel.ExtendedClass` | Text | Extra CSS. |

| Placeholder | Contents |
|---|---|
| `Carousel.CarouselItems` | Flat list of items, OR an `IList` for data-bound slides. **Your content REPLACES the default**; the slide/navigation behavior remains intact. |

**Events**

| Event | Payload | Purpose |
|---|---|---|
| `Carousel.OnSlideMoved` | `Index` (Integer) | Active slide changed. |
| `Carousel.Initialized` | `CarouselId` (Text) | Carousel finished initializing. |

For slides bound to data, place an `IList` inside `Carousel.CarouselItems` — each list iteration becomes one slide.

## DatePicker

Single-date picker — self-contained calendar with built-in input. No placeholders.

| Parameter | Type | Purpose |
|---|---|---|
| `DatePicker.DateFormat` | Text | e.g. `"\"DD/MM/YYYY\""` or `"\"yyyy-MM-dd\""`. |
| `DatePicker.ShowTodayButton` | Boolean | Show "Today" shortcut. |
| `DatePicker.TimeFormat` | Text | e.g. `"\"HH:mm\""`. |
| `DatePicker.OptionalConfigs` | Record | `{ ShowWeekNumbers, FirstDayOfWeek, MinDate, MaxDate, … }`. |
| `DatePicker.ExtendedClass` | Text | Extra CSS. |

**Required LocalVariable:** a `Date` or `DateTime` LocalVariable to hold the selected value (e.g. `SelectedDate`). Bind via `DatePicker.OnSelected`.

**Event** `DatePicker.OnSelected` — payload `SelectedDateTime` (Date Time). Wire to a ScreenAction that assigns the payload to the LocalVariable.

## DatePickerRange

Date-range picker — self-contained, no placeholders.

| Parameter | Type | Purpose |
|---|---|---|
| `DatePickerRange.DateFormat` | Text | Display format, e.g. `"\"DD/MM/YYYY\""`. |
| `DatePickerRange.ShowTodayButton` | Boolean | "Today" shortcut. |
| `DatePickerRange.OptionalConfigs` | Record | Same as `DatePicker`. |
| `DatePickerRange.ExtendedClass` | Text | Extra CSS. |

**Event** `DatePickerRange.OnSelected` — payload `DatePickerId` (Text), `SelectedStartDate` (Date), `SelectedEndDate` (Date). Pass each as a separate `IArgument` with FULL PATH (e.g. `Parameter: "DatePickerRange.OnSelected.SelectedStartDate"`).

Use `DatePickerRange` (single block) for ranges — never two `DatePicker`s.

## MonthPicker

Month/year selector — self-contained, no placeholders.

| Parameter | Type | Purpose |
|---|---|---|
| `MonthPicker.DateFormat` | Text | Display format, e.g. `"\"MM/YYYY\""`. |
| `MonthPicker.MinDate` | Date expression | Earliest selectable month. |
| `MonthPicker.MaxDate` | Date expression | Latest selectable month. |
| `MonthPicker.ExtendedClass` | Text | Extra CSS. |

Event `MonthPicker.OnSelected` — payload `SelectedMonth`.

## TimePicker

Time selector — self-contained, no placeholders.

| Parameter | Type | Purpose |
|---|---|---|
| `TimePicker.TimeFormat` | Text | Display format, e.g. `"\"HH:mm\""`. |
| `TimePicker.InitialTime` | Time expression | Initial value (`"CurrTime()"`, `"#14:30:00#"`). |
| `TimePicker.Is24Hours` | Boolean | `True` for 24h, `False` for 12h with AM/PM. |
| `TimePicker.OptionalConfigs` | Record | Step interval, min/max time. |
| `TimePicker.ExtendedClass` | Text | Extra CSS. |

Event `TimePicker.OnSelected` — payload `SelectedTime`.

## DropdownSearch

Searchable single-select dropdown bound to an aggregate. No placeholders.

| Parameter | Type | Purpose |
|---|---|---|
| `DropdownSearch.OptionsList` | Record List | Options to display — typed as `<Structure> List` (e.g. a custom `StatusOption` Structure with `Value`/`Label` attributes), or `ConvertList(<Aggregate>.List, { Value: "<Id>", Label: "<DisplayText>" })`. |
| `DropdownSearch.StartingSelection` | Text or Identifier | Initial value (matches an option's `Value`). |
| `DropdownSearch.Prompt` | Text | Placeholder text, e.g. `"\"Select…\""`. |
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

### IDropdown widget vs DropdownSearch block

These are different things — don't confuse them:

| | `IDropdown` (built-in widget) | `DropdownSearch` (OutSystemsUI block) |
|---|---|---|
| Type | `"IDropdown"` | `"IMobileBlockInstanceWidget"` with `SourceBlock: "DropdownSearch"` |
| Data source | `List: "<Aggregate>.List"` | `OptionsList: "<DropdownOption List>"` |
| Variable type | MUST be Identifier (e.g. `ProductId`) | Any matching the option `Value` |
| Use for | Simple entity selection | Searchable, complex dropdown |

If you see error `'OptionsList' requires a value of 'DropdownOption List' data type`, you've mixed the two stacks — pick one.

## DropdownTags

Multi-select dropdown rendering selected values as removable chips.

Same arguments and event shape as `DropdownSearch`. The `OnChanged` payload contains the full list of currently-selected options.

## DropdownServerSide variants

Use when the option list is too big to fetch upfront.

| Block | When |
|---|---|
| `DropdownServerSide_SingleSelectionTextImage` | Single-select with image per option. |
| `DropdownServerSide_MultipleSelection` | Multi-select with server-side search. |
| `DropdownServerSide_MultipleSelectionWithFooter` | Multi-select with Apply/Clear footer buttons. |
| `DropdownServerSide_WithOnScrollEnding` | Infinite-scroll loading more on scroll end. |

All variants take an `OptionsList` and an `IsDisabled` argument. Pagination variants expose:

- `OnScrollEnding` event — fires when user scrolls to the bottom; handler increments offset, refetches, and appends.
- The aggregate's `MaxRecords` must be a LocalVariable (not a literal) so it can be incremented per fetch.

## RangeSlider

Single-value slider. No placeholders.

| Parameter | Type | Purpose |
|---|---|---|
| `RangeSlider.MinValue` | Decimal | Lower bound (`"0"`). |
| `RangeSlider.MaxValue` | Decimal | Upper bound (`"100"`). |
| `RangeSlider.StartingValue` | Decimal expression | Initial value (typically a LocalVariable like `SliderValue`). |
| `RangeSlider.Orientation` | `Entities.Orientation` | `Horizontal` or `Vertical`. |
| `RangeSlider.Size` | Text (CSS) | Track length: `"\"300px\""` or `"\"100%\""`. |
| `RangeSlider.OptionalConfigs` | Record | Step, pips, tooltip configuration. |
| `RangeSlider.ExtendedClass` | Text | Extra CSS. |

**Event** `RangeSlider.OnValueChange` — **MANDATORY**. Wire a handler that assigns the new value to your LocalVariable.

## RangeSliderInterval

Two-handle interval slider — pick a range with `From` and `To` handles.

| Parameter | Type | Purpose |
|---|---|---|
| `RangeSliderInterval.MinValue` | Integer | Lower bound. |
| `RangeSliderInterval.MaxValue` | Integer | Upper bound. |
| `RangeSliderInterval.StartingValueFrom` | Integer | Initial lower handle. |
| `RangeSliderInterval.StartingValueTo` | Integer | Initial upper handle. |
| `RangeSliderInterval.OptionalConfigs` | Record | Step, pips, tooltip. |
| `RangeSliderInterval.ExtendedClass` | Text | Extra CSS. |

Event `RangeSliderInterval.OnChange` — payload includes both handle values (`From`, `To`). Wire a handler that updates the bound `From`/`To` LocalVariables.

Use `RangeSlider` for a single value; `RangeSliderInterval` for a range.

## ScrollableArea

Scrollable container with customizable scrollbar.

| Parameter | Type | Purpose |
|---|---|---|
| `ScrollableArea.ScrollbarStyle` | Identifier | Style of the scrollbar (slim, hidden, default). |
| `ScrollableArea.IsVertical` | Boolean | `True` = vertical scroll. |
| `ScrollableArea.Height` | Text (CSS) | Fixed height (required for vertical scroll). |
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
| `InputWithIcon.Input` | The Input widget bound to your LocalVariable. |

## AnimatedLabel

Input with a floating label that animates on focus.

| Placeholder | Contents |
|---|---|
| `AnimatedLabel.Input` | Input widget; the placeholder text becomes the floating label. |

## Search (deprecated)

Use a regular `Input` with a search icon (`InputWithIcon`) instead. The legacy `Search` pattern still exists but is marked deprecated.

## LightBoxImage

Click-thumbnail-to-zoom.

| Parameter | Type | Purpose |
|---|---|---|
| `LightBoxImage.ExtendedClass` | Text | Extra CSS. |

| Placeholder | Contents |
|---|---|
| `LightBoxImage.Image` | The thumbnail `IImage` widget. |

## StackedCards

Tinder-style swipeable card stack.

| Parameter | Type | Purpose |
|---|---|---|
| `StackedCards.Direction` | `Entities.Direction` | Swipe direction. |
| `StackedCards.StackedOptions` | `Entities.StackedOptions` | `Bottom` / `Top` / `None` — where the stack is anchored. |
| `StackedCards.ExtendedClass` | Text | Extra CSS. |

| Placeholder | Contents |
|---|---|
| `StackedCards.CardItems` | The cards (typically inside an `IList`). |

Events: `OnCardClicked`, `OnEndStack`.

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
| `Video.Controls` | Boolean | Show native controls. |
| `Video.Loop` | Boolean | Loop on end. |
| `Video.Mute` | Boolean | Mute audio. |
| `Video.Autoplay` | Boolean | Start automatically (mobile browsers may block). |
| `Video.ExtendedClass` | Text | Extra CSS. |

**Programmatic control** via the OutSystemsUI client actions `VideoPlay(VideoBlockId)` and `VideoPause(VideoBlockId)`. Wire from a Button's `OnClick` through an `ExecuteClientActionNode`.

## Cross-cutting rules

1. **Overlays follow the toggle pattern.** `IsOpen`/`StartsOpen` LocalVariable + `Toggle` ScreenAction. Don't reach into the block's internal DOM.
2. **Pickers are self-contained — no placeholders.** `DatePicker`, `DatePickerRange`, `MonthPicker`, `TimePicker`, `RangeSlider`, `DropdownSearch` are all argument-only. Bind values via the `OnSelected` / `OnValueChange` / `OnChanged` event handlers.
3. **`Tooltip.Content` is the popup body, `Tooltip.Trigger` is the anchor element.** Don't confuse them — naming is non-obvious.
4. **Dropdowns need an `OptionsList` shaped as a `<Structure> List`** with `Value`/`Label` attributes. Use a Structure or `ConvertList(...)` to transform entity records.
5. **`DropdownSearch.OnChanged` is mandatory.** Without a handler the selection isn't propagated.
6. **`RangeSlider.OnValueChange` is mandatory.** Without a handler the new value isn't propagated.
7. **Server-side dropdowns paginate via LocalVariable `MaxRecords`** — increment on `OnScrollEnding` and re-fetch.
8. **`Carousel.CarouselItems` accepts a flat list or an `IList`.** For dynamic data, use `IList`.
9. **`Search` is deprecated.** Use `InputWithIcon` with a search icon.
10. **Event parameter names use FULL PATH format too** — e.g. `Parameter: "DatePickerRange.OnSelected.SelectedStartDate"`, `Parameter: "Tabs.OnTabChange.ActiveTab"`. See [`../ui-reference.md`](../ui-reference.md).

## Accessibility notes

- All overlays trap focus while open and restore it on close. Don't break this by manually moving focus.
- Pickers expose date/time as standard `<input>` elements via the placeholder. Keyboard users can type the value directly.
- `Carousel` advances on Arrow keys when focused. Ensure each slide has a meaningful `aria-label`.
- `Notification` uses `aria-live="polite"` (assertive for `Error` types). Don't change `aria-live` manually.
- `Sidebar`/`BottomSheet`/`Popup` close on Esc by default. Don't override the close handler unless you handle Esc yourself.
- `RangeSlider` exposes `aria-valuenow`/`aria-valuemin`/`aria-valuemax`. Don't use a non-standard slider implementation.
