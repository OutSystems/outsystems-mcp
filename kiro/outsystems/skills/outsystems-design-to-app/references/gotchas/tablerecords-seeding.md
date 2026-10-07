# TableRecords with an empty source — "no records" despite a structurally-correct table

**The trap:** Source HTML has a `<table>` with real `<tr>` data rows (e.g., 5 client records, 12 transactions). The spec creates a TableRecords widget with the right columns, the right styling, the right header — but its `Source` is never populated. Published table renders ZERO rows. User sees the empty-state ("No records to display") even though the structure looks correct.

**Why it happens at the runtime level:** TableRecords doesn't auto-populate from the source HTML. It needs a real data source — an aggregate over a seeded entity. Without that, the source is empty and the widget renders the empty-state.

> **The reliable path:** seed the ENTITY so it persists at deploy and bind the table to an aggregate, and **seed with the platform-generated `Create<Entity>` actions**. The pattern is: Count/aggregate guard (idempotency) → **If** empty → one `Create<Entity>` call per row, wired to a When-Published timer. Never seed with SQL / Advanced SQL INSERT statements. Seeding fails in two ways: it **never runs** at deploy (ships empty) or it **runs twice** (duplicate rows). After each publish, check via `app_logs` that the seed timer finished successfully.

## The fix

1. Bind the table to an aggregate over the entity.
2. **Seed the entity so it persists at deploy:** an **idempotent** seed action named `Seed<Entity>` (Count/aggregate guard → **If** empty → one **generated `Create<Entity>`** call per row), called by a **Timer scheduled When-Published** named `SeedData`. Seed only non-static entities (a static entity carries its records in the entity itself and has no Create action), parents before children. Transcribe the source's real values verbatim, dates as literal dates.
3. Avoid deep branchy node-per-record chains — pathological for Mentor's connector wiring.
4. After each publish, check via `app_logs` (search "Seed") that `SeedData` logged "finished successfully" (not an error). This is the agent's own check, listed in the spec's `post_publish_checks`, never sent to Mentor.

In all cases: **no rows = no render**, seeding must actually RUN at deploy, and it must run only ONCE (idempotent). The widget's structure is irrelevant if Source is empty or doubled.

## How to detect during source inspection

For each `<table>` in the source HTML:

```bash
grep -nE '<tbody>|<tr>' source.html
```

Count the `<tbody><tr>` rows. If > 0, you have demo data. Put one row per source `<tr>` into the entity's `sample_data` array (verbatim values), and bind the table's anatomy node to an aggregate over that entity.

In `spec.json`, add the rows under `sample_data` (keyed by entity):

```json
{
  "sample_data": {
    "Account": [
      { "Name": "Maria Garcia", "Status": "Active", "Balance": 4287.42, "OpenedAt": "2025-12-14" },
      { "Name": "John Smith", "Status": "Pending", "Balance": 12500.00, "OpenedAt": "2026-01-08" }
    ]
  }
}
```

## How to prevent

Enforced by R3 (SKILL.md Step 5).

In the design-to-app's Step 3d acceptance items (each one checkable by Mentor before any publish), add:

- *"[data] Each non-static entity in sample_data has a Seed<Entity> action (Count guard, If empty, one Create<Entity> call per row) called by the When-Published timer SeedData."*
- *"[screen] Every TableRecords' Source is bound to an aggregate over a seeded entity, never an empty or unset list."*

And in `post_publish_checks` (the agent's own checks after the publish): each entity's row count equals its `sample_data` rows, and `app_logs` (search "Seed") shows `SeedData` finished.

## One seeded row per source `<tr>`

Not an invented count. If the source has 7 rows, seed 7 records. If the source has 23 rows, seed 23. Don't truncate to "5 for the demo" — the source is the spec.
