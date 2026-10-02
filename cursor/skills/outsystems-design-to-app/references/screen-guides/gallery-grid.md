# Gallery / Card Grid Screen

## Anatomy

A responsive grid of cards for browsing visual or summary content. Ideal for product catalogs, file managers, team directories, image galleries, and any collection where visual preview matters.

1. **Page header**: Title (heading3) + item count + view toggle (grid/list icons) + "Add New" button
2. **Filter bar**: Search input + category/type filter + sort dropdown (newest, name A-Z, price, etc.)
3. **Card grid** (Gallery block or responsive grid):
   - **Card anatomy** (each item):
     - Image/thumbnail (top, consistent aspect ratio — 16:9 for landscape, 1:1 for square)
     - Title (font-semi-bold, 1-2 lines, truncated with ellipsis)
     - Metadata line: category tag, date, author, or secondary info (text-neutral-7, font-size-xs)
     - Optional: price display, rating stars, progress bar, description snippet
     - Action area: primary CTA button or icon buttons (favorite, edit, delete, share)
4. **Pagination or load more**: Below the grid
5. **Empty state**: Illustrated empty state with "No items found" + filter clear or "Add first item" action

## Variants

- **Product catalog**: Image + title + price (font-bold, heading5) + "Add to Cart" CTA. Hover: quick-view overlay
- **File manager**: Thumbnail (file type icon for non-image files) + filename + size + modified date. Checkbox for multi-select
- **Team directory**: Avatar (circle, large) + name + role/title + department. Click to view profile
- **Image gallery**: Full-bleed images with overlay title on hover. Lightbox on click
- **Bento grid**: Mixed-size cards (hero card spanning 2 columns + 2 rows, regular cards 1x1). Communicates hierarchy through card size

## Layout

- Grid: responsive columns — 3-4 columns desktop, 2 columns tablet, 1 column phone
- Cards: equal width, consistent height per row (or masonry layout for varied content heights)
- Gutter: gutter-m or gutter-base between cards
- Card image: fixed aspect ratio, object-fit cover to prevent stretching
- Responsive: add phone-break-all on the grid container

## Styling

- Cards: background-neutral-0, border-radius-soft, shadow-s. Hover: shadow-m and subtle scale transform (1.01-1.02)
- Image: border-radius on top corners only (border-radius-soft on top-left and top-right)
- Title: text-neutral-9, truncated with text-ellipsis for overflow
- Price (e-commerce): font-bold, heading5 size. Original price with line-through in text-neutral-6
- Tags: small tag pattern with category-appropriate color
- Action buttons: positioned bottom-right of card, or as icon overlay on image hover

## Data Patterns

- Data source: aggregate with search/filter/sort, paginated (MaxRecords + StartIndex)
- Image handling: URL-based images (ImageUrl field) or binary data (converted to base64 inline — consider lazy loading)
- Card click: navigate to detail view. Action buttons trigger specific operations (add to cart, favorite, delete)

## Responsive Behavior

- Desktop: 3-4 column grid with hover effects
- Tablet: 2-column grid
- Phone: 1-column grid (cards full-width) or 2-column compact grid with smaller cards
