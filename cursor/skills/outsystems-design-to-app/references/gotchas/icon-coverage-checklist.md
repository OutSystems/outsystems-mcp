# Icon coverage — enumerate every location

**The trap:** Agents given a Figma routinely hit only the most obvious icons (sidebar nav) and skip the dozens of smaller ones (KPI badge corners, agenda call-type markers, action button glyphs, search shortcut hints). The published surface ends up feeling unfinished even when the chrome looks right — empty card corners, action links without arrows, badges without their tiny dot indicator.

**Why it matters:** icons are visual content. Half-rendering them is the difference between *"this looks like a mockup"* and *"this looks like a real app."* The Figma source contains many more icons than the agent's first pass picks up.

## Locations checklist — go through this for EVERY design-to-app build

For each location, look at the source screenshot. If the location has an icon, enumerate it. If not, skip.

- [ ] **Sidebar nav** — leading icon for each nav item (home / users / chart / calendar / chat / gear / settings / etc.).
- [ ] **Sidebar bottom utility** — bell-with-badge for notifications, logout/sign-out arrow, DEV / settings shortcuts.
- [ ] **Top header / search** — magnifying-glass inside the search box; **keyboard-shortcut hint** (⌘K, Ctrl+K) on the right side as a kbd-styled chip.
- [ ] **KPI / stat cards** — small icon in the **top-right corner of EACH card** (briefcase for monetary, users for headcount, bell for alerts, calendar for time-based, etc.). Even if the Figma renders them subtly — render them.
- [ ] **List / table rows** — leading icon per row if the source has them (status indicator, entity-type icon, avatar placeholder).
- [ ] **Action chips and links** — **trailing arrow (`→`)** on every "Ver detalhes →" / "View all →" / "Schedule →" action link. The arrow is part of the visual identity.
- [ ] **Agenda / appointment cards** — call-type marker (video-camera / phone / in-person) next to the time.
- [ ] **Status badges / pills** — many designs use a tiny dot or shape inside category badges.
- [ ] **Buttons** — leading icon on primary buttons (`+ Novo Cliente`, `+ New Item` — render the `+`).
- [ ] **Card / table headers** — sort indicators, info-tooltip icons.
- [ ] **Empty states** — illustrative icon when a list is empty.

## Enumerate during source inspection

In the design extraction phase (Step 2 of the design-to-app procedure), after running the Figma / Playwright recipe and inspecting `/tmp/oml-source/source.png`, write a CONCRETE list — not *"there are some icons"*:

```
sidebar nav (8): home, users, person-add, trend-up, calendar, chat-bubble, chart-bar, gear
sidebar bottom (2): bell-with-red-badge-3 (Notifications), arrow-right (Sign out)
KPI #1 AuM: briefcase top-right
KPI #2 Clients: users top-right
KPI #3 Alerts (highlighted): bell top-right
KPI #4 today: calendar top-right
agenda card #1 (10:30): video-camera marker
agenda card #2 (14:00): phone marker
search: magnifying-glass left, ⌘K kbd chip right
action links (×8): trailing right-arrow
```

This enumerated list feeds the `spec.json` anatomy nodes — every icon location gets a `<svg>` with explicit `fill` (per [`svg-icon-baking.md`](svg-icon-baking.md)).

## Cross-check with the rendered HTML

```bash
grep -oE '<svg[^>]*aria-label="[^"]*"' /tmp/oml-source/rendered.html | sort -u
grep -oE 'lucide lucide-[a-z-]+' /tmp/oml-source/rendered.html | sort -u
grep -oE '<i class="ph ph-[a-z-]+"' /tmp/oml-source/rendered.html | sort -u
```

If the rendered HTML has Lucide classes, also see [`icon-translation-figma.md`](icon-translation-figma.md) for the Lucide → Phosphor translation table.

## Pre-publish self-check

Before firing Mentor, count icons in the enumerated list vs icons in the spec.json. If the count doesn't match, you missed some.

## Verify after publish

Open the published app in a browser. Walk the visual checklist above against the live screen. Any location that was supposed to have an icon and doesn't → patch in a follow-up Mentor turn.

## Attribution

- [`claude-oml-tool/oml-tool/skills/odc/validated/icons-render-verify.md`](https://github.com/OutSystems/claude-oml-tool/blob/main/oml-tool/skills/odc/validated/icons-render-verify.md) — migrated from instruction #14 on 2026-05-09
