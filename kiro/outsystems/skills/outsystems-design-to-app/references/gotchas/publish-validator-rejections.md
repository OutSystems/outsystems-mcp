# ODC publish validator rejects what passes the model-API Save

> ODC error codes: see `projects/portable-agent-skills/skills/shared/reference/odc-error-registry.md` (workspace path — cross-repo, this repo has no relative route into `portable-agent-skills`) for the canonical index of every code named below.

**The trap:** An OML round-trips cleanly through the local Model API's `LoadESpace` / `SaveESpace` cycle, looks valid, builds in Studio — but the upload to ODC rejects it with **OS-APPS-40028 "Input binary does not contain a valid OML"**. The local quality bar isn't sufficient for server-side publish.

**Why it matters for us:** even though our flow drives Mentor (which uses the Model API server-side), the same OS-APPS-40028 family of errors can surface when Mentor's output hits the publish validator. Knowing what specifically triggers them lets `outsystems-deploy-preview` and `outsystems-spec-driven-build`'s "build failed" reporting be more precise than *"validator rejected — try again."*

## Constructs that publish cleanly

These are confirmed safe with the publish validator:

- Entities (with Long Integer Id, indexed attributes, foreign keys).
- Static Entities with record literals.
- Screens, Local Variables, Aggregates, Local Aggregates.
- WebBlocks with proper input/output parameters.
- OutSystemsUI widgets (TableRecords, Counter, Tabs, Carousel, Wizard, etc.) with correct argument shapes.
- Server Actions, Functions, Action Flow with control nodes.
- REST consume modules, External Library references.
- Theme modules with CSS, JS, font-files chunks.

## Constructs that PASS save but FAIL publish

These pattern-categories cause OS-APPS-40028 even when the local Model API accepts them:

1. **Missing Entities chunk** — every OML must include an Entities chunk, even if no entities are user-defined. A `PlaceholderEntity` (Long Integer `Id` only) suffices.
2. **Stale `ReferersData.xml` / `ReferersForCompilerData.xml`** — caches go stale after manual XML edits outside the model API. Server build then trips `OS-DPL-50205`, `OS-BEW-RDM-50001`, or similar. Strip these before publish; the server will rebuild them.
3. **Stale `VerifyCaches.xml` / `RebindData.xml`** — carry validation errors from earlier states that Studio reads without re-checking against the current XML. Strip on publish.
4. **OML header field 5 ("compiles cleanly" boolean)** — automatically `False` when Save detects unresolved validation errors. Don't try to flip it manually; fix the underlying validation error.
5. **RadioGroup / ButtonGroup auto-create children** — both widgets auto-create 3 RadioButtons / 3 ButtonGroupItems on construction. Walking the existing `Children` collection and adding MORE causes a duplicate-child OS-APPS-40028. Walk existing; don't append.
6. **`IStructure.Public = true` mutations not in the publish digest** — Setting Public on a Structure via the Model API can pass `Save()` but the resulting OML won't actually expose the Structure unless it's also in the publish manifest digest. Filed upstream as M12 (silent publish).
7. **`eSpace.AddDependency(globalKey)` from `applyModelApiCode`** — known broken with NRE. If a referenced library is needed, surface manually for the user to add via Studio.

## Diagnostic process — when a publish fails with OS-APPS-40028

1. Confirm the build round-trips cleanly: re-Load and re-Save the OML locally. If Save fails too, the error is local.
2. If Save succeeds but publish fails, check the rejection reason in `publish_logs` (the OutSystems MCP `publish_logs` tool returns the validator's detailed reason).
3. Walk the construct list above; match against the reason text.
4. If it's a cache-related rejection (`ReferersData`, `VerifyCaches`), strip those XMLs and re-attempt publish.
5. If it's a widget-children rejection (RadioGroup / ButtonGroup), inspect the OML for duplicate children and remove them.

## How this enriches our catalog

- **`outsystems-deploy-preview`** — its risk-level classification should call out OS-APPS-40028 specifically with its likely cause (rather than "validator rejected, unknown").
- **`outsystems-spec-driven-build`** — its Step 8 "summary" should categorize Mentor publish failures using this taxonomy.
- **Cross-skill knowledge** — future Mentor build failures that report OS-APPS-40028 should reference this doc.

## Required server-side fixes baked into `GapFill.SaveAs`

Their build pipeline strips stale caches and ensures Entities-chunk presence automatically via a `GapFill.SaveAs` helper. We don't have a direct equivalent because we don't mutate OML directly — but knowing what `GapFill.SaveAs` enforces tells us what Mentor's output should also be enforcing.

## Crucial baseline note

Round-trip through `LoadESpace` / `SaveESpace` is **NOT** a sufficient quality bar. The local model API is more permissive than the server-side publish validator. Always treat publish-validation failures as separate from local-validation failures.

## Attribution

- [`claude-oml-tool/oml-tool/skills/odc/validated/publish-validator-rejections.md`](https://github.com/OutSystems/claude-oml-tool/blob/main/oml-tool/skills/odc/validated/publish-validator-rejections.md) — validated 2026-05-03 / refreshed 2026-05-06
