---
name: outsystems-maps
description: Catalog of OutSystems Maps blocks (Map, Marker, Map_StaticMap, Marker_AdvancedFormat). Use to pick the right map block when the design contains an interactive map.
---

# OutSystems Maps

Separate Forge component (install per-app, not built into OutSystems UI). Backed by Google Maps / Bing / AWS providers. **Live sample:** [outsystemsui.outsystems.com/OutSystemsMapsSample](https://outsystemsui.outsystems.com/OutSystemsMapsSample/Map).

## Available blocks

| Block | Use when |
|---|---|
| `Map` | Interactive map container — primary block |
| `Marker` | Single pin placed inside a `Map` |
| `Marker_AdvancedFormat` | Custom marker icons (replaces the default pin) |
| `Map_StaticMap` | Static (non-interactive) map thumbnail |

## Requirement → composition

| Requirement | Approach |
|---|---|
| Show a single location | `Map` with one `Marker` |
| Show many locations from data | `Map` with `Marker` inside an `IList` over an aggregate |
| Pick a location | `Map` with `OnMapClick` event → append a `Marker` at clicked coordinates |
| Static thumbnail map (no interaction) | `Map_StaticMap` |
| Route between two points | `Map` + `Marker`s + `Polyline` |

## Block surfaces

| Block | Args | Placeholders | Events |
|---|---|---|---|
| `Map` | `Provider` (enum: `Google`/`Bing`/etc.), `APIKey` (Site Property — never hardcoded), `Width`, `Height`, `Center` (`"lat,lng"` or `Coordinates` record), `InitialZoom`, `MapTypeId` (`Roadmap`/`Satellite`/`Hybrid`/`Terrain`), `Markers` (optional `Marker List`), `OptionalConfigs`, `ExtendedClass` | `Content` (Marker blocks, info overlays) | `OnMapReady`, `OnMapClick` (payload: `Latitude`, `Longitude`), `OnError` |
| `Marker` | `Position` (`"lat,lng"` or `Coordinates` record), `Title`, `IconUrl`, `Label`, `Draggable`, `Animation` (`Drop`/`Bounce`/`None`), `OptionalConfigs` | `Content` (optional info window content shown on click) | `OnMarkerClick` (payload: `MarkerInfo`), `OnMarkerDragEnd` (payload: `Latitude`, `Longitude`) |
| `Map_StaticMap` | `APIKey`, `Width`, `Height`, `Center`, `InitialZoom`, `MapTypeId` | — | — |
| `Marker_AdvancedFormat` | Same as `Marker` plus `IconHTML` (custom HTML for the marker visual) | `Content` | `OnMarkerClick` |

## Composition rules

- **API key in a Site Property** (e.g. `Site.GoogleMapsAPIKey`) — never hardcoded.
- **Many markers** → wrap `Marker` in `IList` bound to the aggregate; bind `Position` to `<list>.Current.<Entity>.Latitude + "," + .Longitude`.
- **Add marker on click** → `OnMapClick` handler appends a `Marker` record to a List LocalVariable + `RefreshDataNode`.
- **Cluster markers** when showing many (enable via `OptionalConfigs` — provider-specific). Don't render 1000 raw `Marker`s.

## Common compositions

- **Map + sidebar list** → `ColumnsSmallRight` with `Column1` = Map, `Column2` = location list. Clicking a list item updates `Map.Center`.
- **Map inside a Card** → `Card` wrapping a Map for shadow + padding.
- **Filter bar above the map** → `Container` row with search/dropdown filters that update the aggregate driving markers + `RefreshDataNode`.

## Anti-patterns

- ❌ Hardcoded API key — always Site Property.
- ❌ Single `Map` with thousands of raw `Marker`s — cluster them.
- ❌ Map inside a heavy parent loop (one Map per list row) — render one map at a time.
- ❌ Custom map widgets built from raw HTML — use the Maps component.
- ❌ Mixing OutSystems Maps and the legacy "Google Maps Markers" Forge component.
- ❌ Disabling provider-default keyboard pan/zoom — breaks keyboard navigation.

## References

- [Live sample](https://outsystemsui.outsystems.com/OutSystemsMapsSample/Map)
- [How to use the Map component](https://success.outsystems.com/Documentation/11/Developing_an_Application/Design_UI/Patterns/Using_Mobile_and_Reactive_Patterns/Interaction/Map/How_to_use_the_Map_component)
- [Forge: OutSystems Maps (ODC)](https://www.outsystems.com/forge/component-overview/15930/outsystems-maps-odc)
