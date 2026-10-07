---
name: outsystems-maps
description: Catalog of OutSystems Maps blocks (Map, LeafletMap, Marker, MarkerPopup, StaticMap, Polyline, MapEvent, MarkerEvent). Use to pick the right map block when the design contains a map.
---

# OutSystems Maps

A separate library (OutSystems Maps), not part of OutSystems UI: the app must reference it. Google Maps uses the `Map` block; Leaflet uses its own `LeafletMap` block. **Live sample:** [outsystemsui.outsystems.com/OutSystemsMapsSample](https://outsystemsui.outsystems.com/OutSystemsMapsSample/Map).

## Available blocks

| Block | Use when |
|---|---|
| `Map` | Interactive Google map, the primary block |
| `LeafletMap` | Interactive map with the Leaflet provider (no Google API key) |
| `Marker` | A pin, placed in the map's `AddOns_Placeholder` |
| `MarkerPopup` | A pin with a pop-up card (content goes in its `Popup` placeholder) |
| `StaticMap` | Static (non-interactive) map image |
| `Polyline` | A line through a list of locations (a route) |
| `MapEvent` / `MarkerEvent` | Handle map or marker events beyond the built-in ones (click, double-click, drag end, zoom change, …) |

## Requirement → composition

| Requirement | Approach |
|---|---|
| Show a single location | `Map` with one `Marker` in `AddOns_Placeholder` |
| Show many locations from data | `Map` with a `List` of `Marker` (or `MarkerPopup`) blocks in `AddOns_Placeholder`, over an aggregate |
| Pin with an info card | `MarkerPopup`, card content in its `Popup` placeholder |
| Pick a location | A `MapEvent` with `EventName` = `click` in the map's `Events_Placeholder`; its `Action` event gives `LatLng` |
| Static thumbnail map | `StaticMap` |
| Route between points | `Map` + `Marker`s + `Polyline` |

## Block surfaces

| Block | Inputs | Placeholders | Events |
|---|---|---|---|
| `Map` | `Height`, `Center`, `APIKey`, `OptionalConfigs` (`OptionalMapConfigs`: zoom, map type, clustering, …) | `AddOns_Placeholder` (markers, shapes), `Events_Placeholder` (`MapEvent` blocks), `LicenseWarning` | `Map_Initialized` (`MapId`), `OnError` (`ErrorMessage`, `ErrorCode`, `MapId`) |
| `Marker` | `Position` (Text, required: an address or `"lat,lng"`), `OptionalConfigs` (icon, title, draggable, …) | `MarkerEvents` (`MarkerEvent` blocks) | `OnClick` (`LatLng`, `MapWidgetId`, `MarkerWidgetId`) |
| `MarkerPopup` | as `Marker` | `Popup` (the card content) | as `Marker` |
| `StaticMap` | `Center`, `Height`, `APIKey`, `StaticMarkers`, `OptionalStaticMapConfigs` | `LicenseInformation` | `OnError` |
| `Polyline` | `Locations` (Text List, required), `OptionalConfigs` | `ShapeEvents` | `OnClick` |
| `MapEvent` | `EventName` (`click`, `doubleClick`, `dragEnd`, `rightClick`, `zoomChanged`, …) | — | `Action` (`LatLng` Coordinates, `MapWidgetId`, `MapObj`, `EventName`) |

## Composition rules

- **API key in an ODC Setting** (e.g. a `GoogleMapsAPIKey` setting), passed to `APIKey`; never hardcoded. `LeafletMap` needs no key.
- **Many markers** → a `List` of `Marker` blocks in `AddOns_Placeholder`, bound to the aggregate; bind `Position` to the record's `Latitude + "," + Longitude` (or its address).
- **Zoom, map type, marker icons and titles** are set through `OptionalConfigs`, not as direct inputs.
- **Cluster markers** when showing many: enable clustering in `Map.OptionalConfigs` (its `MarkerClusterer` settings). Don't render 1000 raw markers.

## Common compositions

- **Map + side list** → `ColumnsSmallRight` with the map in one column and the location list in the other. Clicking a list item updates `Map.Center`.
- **Map inside a Card** → a `Card` wrapping the map for shadow and padding.
- **Filter bar above the map** → search / dropdown filters whose changes refresh the aggregate that drives the markers.

## Anti-patterns

- ❌ Hardcoded API key: always an ODC Setting.
- ❌ One `Map` with thousands of raw markers: cluster them.
- ❌ One map per list row: render one map at a time.
- ❌ Custom map widgets built from raw HTML: use the Maps blocks.
- ❌ Disabling the provider's default keyboard pan/zoom: it breaks keyboard navigation.

## References

- [Live sample](https://outsystemsui.outsystems.com/OutSystemsMapsSample/Map)
- [Forge: OutSystems Maps (ODC)](https://www.outsystems.com/forge/component-overview/15930/outsystems-maps-odc)
