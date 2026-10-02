# TableRecords with an empty List — "no records" despite a structurally-correct table

**The trap:** Source HTML has a `<table>` with real `<tr>` data rows (e.g., 5 client records, 12 transactions). The spec creates a TableRecords widget with the right columns, the right styling, the right header — but its `Source` / `List` is never populated. Published table renders ZERO rows. User sees the empty-state ("No records to display") even though the structure looks correct.

**Why it happens at the runtime level:** TableRecords doesn't auto-populate from the source HTML. It needs a real data source — an aggregate over a seeded entity, or (only for a truly static table with no entity) a Local Variable list. Without that, the source is empty and the widget renders the empty-state.

> **Field-tested update (2026-08-24):** seed the ENTITY so it persists at deploy and bind the table to an aggregate, and **seed with the platform-generated `Create<Entity>` actions** — the reliable, dialect-safe path proven across live builds. The pattern is: Count/aggregate guard (idempotency) → **If** empty → one `Create<Entity>` call per row, wired to a When-Published timer. The older "Local Variable + `ListAppend` in OnInitialize" path is a distant fallback (in-memory only, doesn't persist, brittle to author). This catalog guards against two failures: seeding that **never runs** at deploy (ships empty) and seeding that **runs twice** (duplicate rows) — always verify post-publish via `app_logs` that the seed timer finished successfully.

## The fix

### Primary case — entity-backed table (the normal design-to-app case)
1. Create an `add_aggregate` over the entity and bind the TableRecords' `Source` to it.
2. **Seed the entity so it persists at deploy:** an **idempotent** seed action (Count/aggregate guard → **If** empty → one **generated `Create<Entity>`** call per row), wired to a **Timer scheduled When-Published**. Static entities seed automatically. Transcribe the source's real values verbatim.
3. Use the generated `Create<Entity>` actions (reliable, dialect-safe). Avoid deep branchy node-per-record chains — pathological for Mentor's connector wiring.
4. Verify post-publish via `app_logs` (search "Seed"): each seed timer should log "finished successfully" (not an error).

### Fallback — truly static table with NO entity behind it
- Create a Local Variable of `List<Structure>`, populate it (append per source row), bind `Source` to it. Accept that this is display-only/in-memory and that `ListAppend` authoring can be brittle on the legacy backend — prefer promoting to a real entity if the data matters.

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

Mentor's instructions then say: "for each entity in `sample_data`, add an idempotent seed action (Count guard → If empty → one generated `Create<Entity>` per row) wired to a When-Published timer, and bind the TableRecords.Source to an aggregate over the entity."

## How to prevent (Mentor instructions)

Spec preamble:

> *"Every TableRecords MUST have a non-empty Source. For entity-backed tables (the normal case) bind to an aggregate AND seed the entity so it persists at deploy: an idempotent seed action (Count guard → If empty → one generated Create<Entity> per row) wired to a Timer scheduled When-Published. Do NOT use a per-session Local Variable + ListAppend for real data, and do NOT let seeding run twice. A Local-Variable list is only for a truly static table with no entity. NEVER ship a TableRecords with an unset Source — the published table renders 'no records'."*

In the design-to-app's Step 3d (polish-checklist acceptance items), add:

- *"Every TableRecords' Source is bound to a non-empty List or aggregate. Verify post-publish by checking the published table has the expected row count."*

## One append per source `<tr>`

Not an invented count. If the source has 7 rows, append 7 records. If the source has 23 rows, append 23. Don't truncate to "5 for the demo" — the source is the spec.

## Field-test evidence

APP1387 / APP1388 / APP1420 (2026-06-02): three different "admin iterates" all had the same complaint — *"no records in the table."* In each case, the source HTML had a populated `<table>` but the spec created a TableRecords with no seeded data. Adding the `add_list_append_node` ops per row fixed it on all three.

## Attribution

- [`claude-oml-tool/oml-tool/skills/odc/validated/tablerecords-non-empty-source.md`](https://github.com/OutSystems/claude-oml-tool/blob/main/oml-tool/skills/odc/validated/tablerecords-non-empty-source.md) — validated 2026-06-02 (APP1387 / APP1388 / APP1420)
- See also: [`claude-oml-tool/oml-tool/skills/odc/validated/static-demo-table-records-v2.md`](https://github.com/OutSystems/claude-oml-tool/blob/main/oml-tool/skills/odc/validated/static-demo-table-records-v2.md) — canonical static-demo recipe, validated 2026-05-18 via `Probe_TableRecordsV2`
