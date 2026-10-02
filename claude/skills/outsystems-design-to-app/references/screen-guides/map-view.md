# Map / Geospatial View Screen

## Anatomy

An interactive map displaying location-based data with markers, clusters, and an associated list. Used for store locators, asset tracking, property listings, delivery tracking, and facility management.

1. **Map header**: Title (heading3) + search/filter bar (address search input, category filter, radius selector)
2. **Map area** (Map block — IMap or LeafletMap):
   - Interactive map filling the main content area
   - Markers/pins at data point locations, color-coded by category or status
   - Marker clusters at low zoom levels (group nearby markers with count badge)
   - User location indicator (if geolocation permitted)
3. **Marker popup**: On marker click, show a popup/info card with:
   - Location name (font-semi-bold)
   - Address or coordinates
   - Key metadata (status, category, rating)
   - "View Details" link to full detail screen
4. **Location list panel** (sidebar or bottom panel):
   - Scrollable list of locations matching current map bounds or search
   - Each item: name + address + distance + key metric
   - Clicking a list item centers the map on that location and opens its popup
5. **Optional controls**: Map type toggle (street/satellite), zoom buttons, full-screen toggle

## Layout

- Desktop: map takes ~65% width (left), location list panel takes ~35% (right). Or full-width map with collapsible bottom drawer for the list
- Tablet: full-width map with bottom sheet list (swipe up to expand)
- Phone: full-width map with bottom sheet list or toggle between map and list views

## Styling

- Map area: no border-radius (fill the content area edge-to-edge). Minimum height 400px desktop, 300px phone
- Markers: custom icons or colored circles by category. Active/selected marker visually distinct (larger, different color, or bounce animation)
- Popup cards: background-neutral-0, border-radius-soft, shadow-m, padding-s. Max-width ~250px
- Location list items: padding-s, border-bottom divider, hover background-neutral-1. Selected item: left border in primary color
- Search bar: positioned above or overlaid on the map (floating with shadow)

## Data Patterns

- Data source: locations/points with latitude, longitude, name, address, category, and status
- Map bounds filter: update the list when the map viewport changes (show only visible locations)
- Search: geocode the search text to coordinates, center map, filter nearby results
- Marker click: highlight in both map and list, show popup
- List item click: pan map to location, open marker popup

## Responsive Behavior

- Desktop: side-by-side map + list panel
- Tablet: full-width map with bottom drawer (collapsed: shows 2-3 items, expanded: full scrollable list)
- Phone: toggle between map view and list view, or map with minimal bottom sheet showing nearest location
