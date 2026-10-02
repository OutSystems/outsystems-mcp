---
name: outsystems-app-architecture
description: "[Beta] Generate an interactive HTML graph of a single OutSystems app's architecture — UI flows + screens, server/client/service actions with signatures, entities with attributes and relationships, static enums, structures, roles, AI model connections, library dependencies and where the app is deployed — with OutSystems-themed dark mode styling. ONE app per invocation — do NOT iterate over multiple apps in a single call (run the skill explicitly per-app; for more than 3 named apps, ask the user and wait for an explicit answer first). For 'every app' / 'all apps' requests and tenant-wide views, use outsystems-tenant-architecture instead: its scope guard asks before any per-app run, without listing the apps first. Use when the user asks for the architecture of a specific app, 'show me the architecture of [app]', 'explore [app]', 'what's inside [app]', 'give me an overview of [app]', or similar."
license: MIT
compatibility: Needs an agent that can run shell commands and Python 3.8+ (standard library only), with the OutSystems MCP server connected and signed in. Validated on Claude Code. Claude Desktop's Chat tab has no shell and cannot run it. The generated HTML loads its graph library from a CDN; offline it shows a plain listing instead.
allowed-tools: Bash(python3 ${CLAUDE_PLUGIN_ROOT}/skills/outsystems-app-architecture/scripts/build.py *) Bash(python3 "${CLAUDE_PLUGIN_ROOT}/skills/outsystems-app-architecture/scripts/build.py" *) Write mcp__plugin_outsystems_outsystems__app_list mcp__plugin_outsystems_outsystems__app_info mcp__plugin_outsystems_outsystems__app_refs mcp__plugin_outsystems_outsystems__app_revisions mcp__plugin_outsystems_outsystems__env_list mcp__plugin_outsystems_outsystems__env_apps mcp__plugin_outsystems_outsystems__context_screens mcp__plugin_outsystems_outsystems__context_actions mcp__plugin_outsystems_outsystems__context_entities mcp__plugin_outsystems_outsystems__context_structures mcp__plugin_outsystems_outsystems__context_roles mcp__plugin_outsystems_outsystems__context_connections mcp__outsystems__app_list mcp__outsystems__app_info mcp__outsystems__app_refs mcp__outsystems__app_revisions mcp__outsystems__env_list mcp__outsystems__env_apps mcp__outsystems__context_screens mcp__outsystems__context_actions mcp__outsystems__context_entities mcp__outsystems__context_structures mcp__outsystems__context_roles mcp__outsystems__context_connections
metadata:
  version: "1.7.0"
  maturity: beta
  author: OutSystems
---

**Beta Feature.** This skill is a Beta Feature: a non-final OutSystems capability provided to collect customer feedback. It can change significantly, including through breaking changes, or be discontinued. The first time you use this skill in a conversation, tell the user it's a Beta Feature and share https://www.outsystems.com/legal/beta-features-agreement.

# OutSystems App Architecture

Produces a single HTML file with a force-directed graph of one app's
internal structure: UI flows → screens, action groups → server, client
and service actions, data layer (entities / enums / structures, with
entity → entity reference edges), security (roles), and
**dependencies** — AI model connections and referenced libraries.
OutSystems dark theme, filter-by-category sidebar, click a node for its
attributes, signature or input parameters. The sidebar also shows where
the app is deployed and its recent revisions.

The app data is inlined in the file. The graph library (vis-network
9.1.9, pinned with a Subresource Integrity hash) and the fonts load from
CDNs: without network access, or if the CDN serves anything but the
pinned file, the page shows a plain HTML listing of the same data
instead of the graph.

## Prerequisites

- The OutSystems MCP server is connected and signed in. This skill reads
  the tools named below; tool names here are the server's own, and your
  harness may show them with a prefix (in Claude Code,
  `mcp__plugin_outsystems_outsystems__app_info` for `app_info`).
- A shell with `python3` (3.8 or later, standard library only). The
  script reads the saved tool results from disk and writes the HTML; it
  never calls the server and holds no sign-in of its own.
- `<skill-folder>` below is this skill's own folder: the one holding this
  file (in the OutSystems plugin, `skills/outsystems-app-architecture/`), so
  `<skill-folder>/scripts/build.py` is the script next to it. Values in
  angle brackets are placeholders you substitute; quote every path, since
  a home folder can contain spaces.
- Run every `build.py` command on its own and exactly as this file writes
  it: the skill's permissions match `python3 "<skill-folder>/scripts/build.py" ...`
  and nothing else, so an added redirect (`2>&1`), pipe or chained command
  (`;`, `&&`) makes the harness stop and ask the user.
- No shell available? Stop and tell the user this skill needs one (for
  example Claude Code, not Claude Desktop's Chat tab); don't try to build
  the page by hand.

**The core rule: keep large data off the model's context.** Tool results
go to disk, `build.py` reads them from there, and the HTML comes out the
other side. Never read a saved result back into the conversation.

## Procedure

### Step 0 — Scope guard

This skill produces **one app's architecture** per invocation. Read
the user's request and route:

**Branch A — One specific app** ("architecture of Banking Portal",
"show me TaskTracker")
→ Continue.

**Branch B — Multiple specific apps** ("architecture of Banking
Portal AND TaskTracker AND ...")
→ For N ≤ 3, run this skill once per app sequentially. For N > 3,
**ask the user** — it's ~10K tokens each, ~50K + ~5 min
for 5 apps. Confirm before chaining.

**Branch C — Whole tenant** ("architecture of everything", "all my
apps")
→ **Stop and route to `outsystems-tenant-architecture`.** That skill
is a single tenant-level pass at ~3-10K tokens, not 100× per-app calls.
Tell the user: *"For the tenant view, use `outsystems-tenant-architecture`
— it's one pass instead of N. After you have that, come back here for
specific apps you want to drill into."*

Chaining this skill over every app by accident ("show me all apps"
fanning out into 100+ per-app runs) is what turns minutes into an hour.

### Step 1 — Identify the app (and list environments)

There is no sign-in pre-flight: the first real call surfaces an expired
or missing sign-in. If any call fails with an authentication error, stop
and ask the user to sign in to the OutSystems MCP server again, then
start over.

Resolve the app from the user's prompt, and in the same message call
`env_list` (no arguments; Step 3 needs the environment keys):

- If the user gave an asset key (UUID), call `app_info` with
  `key: <APP_KEY>` for its name (Step 3's `env_apps` searches by name).
- Otherwise call `app_list` with `search: "<name from prompt>"`. If
  exactly one match → use it. If multiple → list the candidates and ask
  the user to pick. If zero → ask for a more specific name.

```
APP_KEY  = <asset key>
APP_NAME = <human-readable name, exactly as app_list / app_info report it>
ENV_KEYS = <key of every env_list result>
```

Create this skill's cache folder for the app. The script prints the
folder's path; the steps below call it `<cache-folder>`:

```bash
python3 "<skill-folder>/scripts/build.py" --cache-dir <APP_KEY>
```

Save the `env_list` response to `<cache-folder>/env-list.json` (it is small;
write it as returned).

### Step 2 — Cache freshness (only if cache exists)

If `<cache-folder>/meta.json` is present:

1. Call `app_info` with `key: <APP_KEY>` (cheap, ~500 tokens; skip if
   Step 1 already called it).
2. Compute `AGE = now - meta.fetched_at`:
   `python3 "<skill-folder>/scripts/build.py" --cache-age "<cache-folder>"`
   prints `meta.json` and its `age_s` in one call (no `cat`, no `date`).
3. If `AGE < 3600` AND `app_info.revision == meta.revision` AND
   `meta.schema == 3` → **cache valid, jump to Step 4** (cached re-render).
   A `meta.json` with `schema` 2 or none was written by an older version
   and lacks attributes, signatures and deployments: treat it as stale
   and go to Step 3 (`build.py` refuses to re-render it anyway, exit `3`).

Deployment state can change without a new revision (a deploy of an
existing revision to Production), so a valid cache can carry an old
deployment view. The HTML and the Step 5 report show it "as of"
`meta.deployments_fetched_at`. If the user asks where the app is
deployed "now", or says "refresh" / "fresh data" / "rebuild", skip
this step.

### Step 3 — Fetch (parallel)

Make **all** of these calls in a single message so they run
concurrently. `limit: 100` is the API maximum for `context_*` (on a
harness that truncates large tool results use `limit: 25`, see Harness
notes).

| # | Tool | Arguments | Save as |
|---|---|---|---|
| 1 | `app_info` | `key: <APP_KEY>` | `app-info-raw.json` |
| 2 | `context_screens` | `app: <APP_KEY>`, `limit: 100`, `owned_only: true` | `screens-raw.json` |
| 3 | `context_actions` | `app: <APP_KEY>`, `limit: 100`, `owned_only: true` | `actions-raw.json` |
| 4 | `context_entities` | `app: <APP_KEY>`, `limit: 100`, `owned_only: false` | `entities-raw.json` |
| 5 | `context_structures` | `app: <APP_KEY>`, `limit: 100`, `owned_only: true` | `structures-raw.json` |
| 6 | `context_roles` | `app: <APP_KEY>`, `limit: 100`, `owned_only: true` | `roles-raw.json` |
| 7 | `context_connections` | `app: <APP_KEY>`, `limit: 100`, `owned_only: false` | `connections-raw.json` |
| 8 | `app_refs` | `key: <APP_KEY>` | `refs-raw.json` |
| 9 | `app_revisions` | `key: <APP_KEY>`, `limit: 10` | `revisions-raw.json` |
| 10+ | `env_apps` | `env_key: <ENV_KEY>`, `search: "<APP_NAME>"` — one call per environment | `env-apps-<ENV_KEY>.json` |

Why the two `owned_only: false` calls:

- **Entities (#4).** Many apps (especially "thin UI" patterns) define
  their data model in a separate library module. With `owned_only: true`
  those apps return no entities and the skill would report "no
  entities" — materially misleading. `build.py` partitions the rows into
  `entities` (owned), `inheritedEntities` (user libraries, listed with
  their module) and a count of platform-module rows, and resolves foreign
  keys against all of them.
- **Connections (#7).** An AI model connection is its own asset. On a
  query scoped to the app, a connection the app uses comes back as a
  *referenced* row (`isReferenced: true`), identified by its own `key`
  and `name` (`producerAssetKey` / `producerAssetName` are not set on
  connection rows), and `owned_only: true` — the default whenever `app`
  is set — filters every such row out. An app that uses no connection
  returns an empty page, which is normal.

`app_refs` (#8) is called on every run, whatever the app's size: it
reads the context index first (the model download is only a fallback
for an app that is not indexed), so a revision number says nothing about
its cost. `env_apps` (#10+) takes no `offset` and caps its page, which
is why it is narrowed with `search`; `build.py` keeps only the row whose
`applicationKey` equals `APP_KEY` (the search is a name substring, so
other apps can match too).

For **each** response, follow this rule:

- **If the response is the "Output has been saved to <path>" notice**
  (Claude Code's harness auto-save kicked in, typical for large apps):
  extract the path and copy it into the cache with
  `python3 "<skill-folder>/scripts/build.py" --copy "<path>" "<cache-folder>/<file>"`
  (it writes only inside this skill's cache), so its content
  never enters the conversation. **This is the cheapest path.**
- **If the response is inline JSON** (under Claude Code's auto-save
  line, measured between 45 and 65 KB, and every response on harnesses without
  auto-save): write the
  `context_*` responses in the **compact form** below to
  `<cache-folder>/<file>`, keeping the top-level envelope keys. Write the small
  responses (#1, #8, #9, #10+) as returned. Use the Write tool, one call
  per file: this skill's allowed tools grant Write and its own `build.py`,
  nothing else, so a shell redirect (`cat > file`) makes the harness ask
  the user.
- **If a call errors**: for `app_refs`, save
  `{"assetKey": "<APP_KEY>", "failed": true}` as `refs-raw.json` and
  continue (the graph then renders without libraries; connections still
  show). For `context_connections`, `app_revisions` or an `env_apps`
  call, write `{"error": "<the error message>"}` to that file (see
  Step 4): the section degrades, and an environment renders as
  "unknown". An `app_info` error or an error on
  any other `context_*` call stops the run — report it.

Every `context_*` response is one server page and carries `total`,
`truncated` and `next_offset`. You do not check them; `build.py` does
(Step 4) and exits `3` naming the section and the `offset` to fetch
when a page is truncated.

### Compact-write field whitelist (mandatory for inline responses)

When writing an inline `context_*` response, emit ONLY these fields
(nested lists keep only the fields in braces). Compact JSON, no
whitespace inside objects.

| File | Fields to keep |
|---|---|
| `screens-raw.json`     | `data[].(key, name, description, isPublic, timestamp, ownerAppKey, isReferenced, additionalData.{uiFlowKey, uiFlowName, title, inputParameters[].{name, dataType, isRequired}})` — drop `additionalData.roles` (see Anti-patterns) |
| `actions-raw.json`     | `data[].(key, name, description, isPublic, ownerAppKey, isReferenced, additionalData.{actionType, actionTypeStr, parameters[].{name, dataType, parameterTypeStr, isMandatory, description}})` |
| `entities-raw.json`    | `data[].(key, name, description, isStatic, ownerAppKey, isReferenced, producerAssetKey, producerAssetName, additionalData.{records, attributes[].{name, dataType, isPrimaryKey, isMandatory, length, description}})` — on rows whose `producerAssetName` is a platform module (`(System)`, `OutSystemsUI`, `OutSystemsCharts`, `OutSystemsMaps`, `OutSystemsSampleData`, `OutSystemsSecurity`, `OutSystemsPipelines`, `OutSystemsServerlessAddon`) drop `additionalData` entirely: those rows are only counted, and foreign keys resolve against their names |
| `structures-raw.json`  | `data[].(key, name, description, ownerAppKey, isReferenced, additionalData.{attributes[].{name, dataType, isMandatory, length, description}})` |
| `roles-raw.json`       | `data[].(key, name, description, isPublic, ownerAppKey, isReferenced)` |
| `connections-raw.json` | `data[].(key, name, isReferenced, providerName)` |

Keep `additionalData.records` exactly as received: it is a JSON
*string* (`"[\"InStock\",\"Assigned\"]"`), and `build.py` parses it.

**Token trade-off:** keeping attributes, parameters and screen inputs
costs more on the inline path. On a recorded mid-sized app (11 screens,
10 actions, 73 entity rows of which 62 from platform modules) the five
`context_*` compact writes are ~45 KB. The platform rows are 67 KB of
the 90 KB raw entities response, so keeping their `additionalData` would
more than double the write — hence the rule to drop it. Claude Code's
auto-save path is unaffected: saved files never enter the context.

**Ownership is `isReferenced`, not `ownerAppKey`.** On an app-scoped
query the server puts the visiting app's key in `ownerAppKey` (and
`assetKey`) on every row, inherited ones included, so that field cannot
tell owned from inherited. `isReferenced: false` means defined in this
app; `true` means it comes from a referenced library, named by
`producerAssetName`. `build.py` partitions on `isReferenced`; when a row
has no `isReferenced` value it uses `producerAssetKey` (a producer other
than the app means inherited) and only then `ownerAppKey`. Keep all three
in the whitelist.

Wrap each file in
`{"data": [...], "total": <total>, "truncated": <truncated>, "next_offset": <next_offset>, "pagination": <pagination>}`,
copying those four top-level values from the response unchanged. `build.py`
judges completeness from `pagination.offset` / `nextPageOffset` (the page
chain), because on the `owned_only: false` calls the server's `total` is
only a lower bound while more pages exist. With those keys kept, it reads
inline-written files and harness-saved files interchangeably.

### Step 4 — Build (fresh or cached)

One Python invocation does everything: transforms the raw responses into
the compact bundle, then injects it into the template. Pass one
`ENV_KEY=PATH` pair per saved `env_apps` response. `<output-file>` is
`app-architecture.html` in the user's working folder (absolute path) unless they asked
for another one.

```bash
python3 "<skill-folder>/scripts/build.py" "<cache-folder>" "<output-file>" \
  --app-info     "<cache-folder>/app-info-raw.json"     \
  --screens      "<cache-folder>/screens-raw.json"      \
  --actions      "<cache-folder>/actions-raw.json"      \
  --entities     "<cache-folder>/entities-raw.json"     \
  --structures   "<cache-folder>/structures-raw.json"   \
  --roles        "<cache-folder>/roles-raw.json"        \
  --connections  "<cache-folder>/connections-raw.json"  \
  --refs         "<cache-folder>/refs-raw.json"         \
  --revisions    "<cache-folder>/revisions-raw.json"    \
  --env-list     "<cache-folder>/env-list.json"         \
  --env-apps     "<ENV_KEY_1>=<cache-folder>/env-apps-<ENV_KEY_1>.json" "<ENV_KEY_2>=<cache-folder>/env-apps-<ENV_KEY_2>.json"
```

The six flags from `--app-info` to `--roles` are required; the others
are optional and each only adds its part (an omitted `--env-apps`
and `--env-list` mean no deployment section).

**When an optional call (#7–#10, `env_list`) fails, still pass its path.**
Write `{"error": "<the error message>"}` to it (JSON, never the raw error
text, which fails as `BAD INPUT`). Always write it, even on a first run:
on a refresh the file from the previous run is still there, and leaving
it would render that run's data as current. `build.py` treats an error
object (or a missing file) as "unavailable" and
degrades only that section — AI model connections or libraries are left
out of Dependencies (it prints a `warning:`), the revisions table is left
out, and an environment whose `env_apps` call failed renders as
**unknown (not fetched)**, never "not deployed". Do not drop the flag and
do not invent an empty response: an empty `results` list would read as
"not deployed".

Deployment status also depends on the asset type: `env_apps` never lists
**Workflow** assets (every environment renders "unknown: env_apps does
not list workflows") and **libraries** are not deployed on their own
("n/a"). A deployed row whose `revision` is null renders "revision
unknown" with no drift claim.

Exit codes and what to do:

- **`3` with `INCOMPLETE: <section> page(s) hold N rows ... offset: M`**
  → call that section's `context_*` tool again with the same arguments
  plus `offset: M`, save the response as `<section>-raw.2.json`
  (auto-saved path or compact write, as in Step 3), and re-run passing
  every page after that flag in order, e.g.
  `--entities "<cache-folder>/entities-raw.json" "<cache-folder>/entities-raw.2.json"`.
  Repeat while it exits `3`. Do not compute the number of pages from
  `total`: on the `owned_only: false` calls it is a lower bound ("at
  least N" in the message), so only exit `0` tells you the section is
  complete. For the "do not form a contiguous chain from offset 0"
  variant, re-fetch that section once from `offset: 0` (same limit)
  with fresh file names and rebuild; if the same message comes back,
  stop and report the message and the files you passed rather than
  fetching again. Stop and report instead of re-fetching if `build.py`
  prints the same `offset` twice.
- **`1` with `BAD PAGE`** → the re-fetch was made without `offset`, so
  the page repeated: fix the call, do not re-run the same files.
- **`1` with `BAD INPUT`** → a saved file is not JSON, or carries a
  harness truncation marker ("Warning: truncated output",
  "…N tokens truncated…"): the response was cut before it reached you
  and rows are missing. Re-fetch that call with `limit: 25` and page
  with `offset` (one file per page). Never hand-repair the file.
- **`3` with `STALE`** (cached mode) → the cache predates schema 3: run
  fresh mode.

For cached mode, omit every flag — `build.py` re-renders the existing
compact bundle (including the dependencies and deployments of the run
that wrote it).

### Step 5 — Report (3–6 lines)

- Output file path
- App name + revision + asset type
- Counts: UI flows, screens, server / client / service actions, entities
  (owned and inherited), enums, structures, roles, entity references,
  AI model connections, libraries (the second line `build.py` prints)
- Deployment line `build.py` prints, with its "as of" time
- The `library coverage:` and `dependencies not fetched:` lines when
  `build.py` prints them: never present the library list as complete
- Cache state — "used (Xs old)" or "refreshed"; mention any
  `note:`/`warning:` lines `build.py` printed (for example about records)

## Data shape contract

`build.py` writes a single compact bundle to `<cache-folder>/app-data.json`
that the template reads. Fields marked `?` are omitted when empty or
false.

```js
APP_DATA = {
  schema: 3,                                         // consumers refuse < 3 (exit 3 → refetch)
  app: { key, name, type, revision, description, date },
  uiFlows: [{ key, name }],
  screens: [{ k, n, flow, desc, pub, date, title?,
              inputs: [{ n, t, req? }] }],
  actions: [{ k, n, kind: "action"|"client"|"service", desc, pub,
              in: [{ n, t, req?, d? }], out: [{ n, t, req?, d? }] }],
  entities: [{ k, n, desc, attrs: [Attr] }],                        // owned
  inheritedEntities: [{ k, n, desc, fromModule, attrs: [Attr] }],   // user libraries
  enums: [{ k, n, desc, attrs: [Attr], records: [string], recordCount }],   // owned static entities
  inheritedEnums: [{ k, n, desc, fromModule, attrs, records, recordCount }],
  structures: [{ k, n, desc, attrs: [Attr] }],
  roles: [{ k, n, desc, pub }],
  deps: [{ k, n, kind, cat: "AIModel"|"Library", rev }],   // connections first, deduped with app_refs
  depsSource: "app_refs"|null,                            // where the libraries came from
  depsUnavailable: ["libraries"?, "AI model connections"?], // parts not fetched: the page says so
  refsCoverage: { source, indexedKinds: [string] | null } | null,  // what app_refs covers: the page says so
  deployments: { fetchedAt, latestRevision,
                 envs: [{ k, n, purpose, status: "deployed"|"not-deployed"|"unknown"|"n/a",
                          rev?, at?, behind?, reason? }] } | null,
  revisions: { rows: [{ rev, at, digest, tag? }], total } | null,   // newest first, at most 10
  inheritedCount: number,              // every inherited entity row, platform modules included
  inheritedBuiltinCount: number        // inherited rows from platform modules: counted, not listed
}
Attr = { n, t, pk?, req?, len?, d?,
         fk?: { n, in: "owned"|"inherited"|"platform"|"external", k?, from? } }
```

- `fk` is set on attributes whose type is `"<Entity> Identifier"`. The
  target resolves by name: owned first, then user-library, then
  platform entity rows; `external` means no row of that name was in the
  payload. The graph draws owned → owned and owned → inherited edges.
- `records` holds at most 50 labels; `recordCount` is the full count.
  `"[]"` on an inherited static entity means "none recorded", not "none
  exist". A records string that is not a JSON list is reported on stderr
  and treated as empty.
- Screens carry no `roles`: the payload's `additionalData.roles` lacks
  the screen's access mode, so it is not copied into the bundle (see
  Anti-patterns). Consumers must not derive per-screen access from
  anything in this bundle.
- `deployments.envs[].status` is `unknown` when the environment's
  `env_apps` response was not fetched, or was truncated without a row
  for this app key.
- `refsCoverage`: a `context-service` answer lists only the element kinds
  in `indexedKinds` (often just `entities`), so a library the app uses
  only through actions, structures, blocks or themes can be missing, and
  even a listed kind is not proven complete; the page and your report
  must say which kinds were covered (unknown when `indexedKinds` is null)
  and never present the list as complete. It does not apply to an `oml-fallback` answer.
- Built-in OutSystems modules are filtered out of `deps`. `deps` is
  empty when neither connections nor refs were available; the template
  hides the Dependencies layer then.

## Cache rules

- Location: the folder `build.py --cache-dir <APP_KEY>` prints (one per
  app, under the shared `outsystems-skills` cache root).
- TTL: 1 hour
- Freshness check: compare `app_info.revision` against `meta.revision`,
  and `meta.schema` against 3. A single revision number is the canonical
  "did the app change?" signal.
- Deployments are not covered by that check (they change without a new
  revision): `meta.deployments_fetched_at` dates them and the outputs
  say "as of".

## Token budget (estimate)

| Scenario | Mechanism | Total |
|---|---|---|
| Typical app, first run, Claude Code | 10+ calls, context_* auto-saved + build.py | ~12-14K |
| Typical app, first run, inline (no auto-save) | 10+ calls, compact writes incl. attributes | ~15-20K, plus paging calls at `limit: 25` on a truncating harness |
| Cached run | `app_info` probe + build.py | ~2K |
| Re-render only | build.py | ~1K |

Measured on an app with 18 screens / 42 actions / 30 entities / 6
structures / 19 enums / 1 role: ~12-13K with compact-write. `app_refs`,
`context_connections`, `app_revisions` and each `env_apps` response are
small (a few hundred bytes to ~2 KB each); the attribute-carrying compact
writes are the main cost (see the whitelist's token trade-off).

## Harness notes

- **Claude Code**: `context_*` MCP results above its size limit
  (measured between 45 and 65 KB) are auto-saved
  to disk by the harness ("Output has been saved to <path>") and never
  enter model context. On a large app this is what keeps the first-run
  cost down, and it's why the first anti-pattern below exists — don't
  undo the saving by reading the file back in.
- **Harnesses without auto-save** (Cursor, Kiro and others): every
  response arrives inline; compact-write the `context_*` ones as in
  Step 3 and write the rest as returned.
- **Harnesses that truncate large tool results** (for example Codex,
  which keeps the head and the tail, prefixes "Warning: truncated output
  (original token count: N)" and replaces the middle with "…N tokens
  truncated…"): use `limit: 25` on every `context_*` call and let
  `build.py`'s exit-`3` loop drive `offset` paging; write each page to
  its own file. If a response still shows the marker, do not compact it
  — re-fetch with a smaller `limit`. `build.py` refuses a file carrying
  the marker (exit `1`, `BAD INPUT`) so a cut page can never be rendered
  as complete.
- Cached runs and re-renders (Step 4 cached mode) cost the same on every
  harness — that path never touches `context_*`.

## Troubleshooting

- **An MCP call fails with an authentication error** → the sign-in
  expired: ask the user to sign in to the OutSystems MCP server again,
  then start over. Don't loop.
- **The OutSystems tools are missing** → the MCP server is not connected;
  ask the user to connect it (see the main OutSystems skill's setup).
- **`python3: command not found`** → ask the user to install Python 3.8
  or later; nothing else is needed.
- **`build.py` exits 1 with `could not write the output file`** → the
  output path is not writable (no space left, no permission, or a folder
  of that name). Only the HTML failed: ask the user for another output
  path and re-run the same command with it.
- **A description or static-entity record list shows "truncated by the
  server (N bytes)"** → the server replaces any `additionalData` string
  over 2048 bytes with `{"_truncated": true, "_originalBytes": N}` (a
  large static entity's records, a long description). The bundle keeps
  the marker's size, never an empty value. To read the full field, use
  `context_search` with `full_fields: true` for that element.
- **App name matches multiple apps** → return the candidate list, ask
  the user to pick. Show `assetKey, name, revision, isExternal`.
- **`app_info` returns 404** → the app may have been deleted. Tell the
  user.
- **`context_*` returns `{"data":[], "pagination":...}`** with empty
  data despite `owned_only: true` → try `owned_only: false`. `build.py`
  keeps only rows with `isReferenced: false` for the owned sections, so
  widening the query never leaks inherited items into them.
- **`context_connections` returns no rows** → the app uses no AI model
  connection (or the call was made with `owned_only: true`, which hides
  them — it must be `false`).
- **`app_refs` errors or times out** → save
  `{"assetKey": "<key>", "failed": true}` to `<cache-folder>/refs-raw.json`.
  `build.py` renders without libraries (connections still show).
- **An environment shows "unknown"** → its `env_apps` response was not
  saved, or was truncated without a row for this app (the tool has no
  `offset`). Re-run that call with the exact app name; it is never
  reported as "not deployed" without evidence.
- **`BAD INPUT: ... truncation marker`** → see Harness notes.

## Anti-patterns — do NOT do these

- 🔴 **Do NOT read any `context_*` harness-saved file (Claude Code).**
  When a context call returns *"Output has been saved to <path>"*, copy
  that file into the cache with `build.py --copy` (Step 3) and pass the
  path to `build.py`.
  **Never** read it into context. A large app's `context_screens`
  payload alone can be 20-40 KB ≈ 5-10K tokens; across all context calls
  a large app pulls 50-150 KB = 12-35K tokens into context, and every
  later turn pays for it again. If you need to check content for
  debugging, run `python3 "<skill-folder>/scripts/build.py" --peek "<path>"`.
- 🔴 **Don't dump an inline `context_*` payload back into the
  conversation or re-read the compact cache file (harnesses without
  auto-save).** Each response arrives inline (see Step 3) and is
  compacted straight to `<cache-folder>/<section>-raw.json`. Pass that file path
  to `build.py` — never re-print or re-load the raw payload into context
  on a later turn.
- **Don't parse the payloads yourself** (no `jq`, no hand-written
  scripts over the saved files), and don't pre-paginate: `build.py` asks
  for the next page when one exists.
- **Don't iterate this skill over many apps in one go** without
  Step 0's user-confirmation gate. A "give me all my apps" request
  scaled to 100 apps = ~1M tokens / 30-60 min wall time. Always
  prefer `outsystems-tenant-architecture` for tenant-wide views; this
  skill is per-app only.
- **Never cross-product roles with screens — don't invent per-screen
  authorization.** Screen rows carry `additionalData.roles`, but it is
  filled from the model's screen roles list and does not include the
  screen's access mode (Everyone / Authenticated / selected roles). A
  screen set to "Accessible by: Everyone" can still list the app role:
  on a recorded app every screen, the template Login screen included,
  lists it. A summary built from that field once stated that every
  common-flow screen required the app's role, when in ODC Studio those
  screens were `Accessible by: Everyone`. So `build.py` does not put
  screen roles in the bundle and the graph draws no screen → role edges.
  Render the app's roles as a flat list once (from `D.roles`); never
  assign roles to screens, never infer them from the app's primary role,
  and never call a screen public or anonymous (`isPublic` is the
  element's Public property, not anonymous access). For who can open a
  screen, point the user to ODC Studio.
- **Don't fetch `context_themes`** — the response can be >150 KB on a
  real app. Out of scope; high cost, low signal.
- **Don't skip `app_refs` because the app is large or has many
  revisions.** Its cost does not depend on the revision number.
- **Don't report an environment as "not deployed" from a truncated or
  missing `env_apps` response** — `build.py` says "unknown" there; keep
  that wording.

## When NOT to use

- User wants the whole tenant (use `outsystems-tenant-architecture`).
- User asks who depends on a library, agent or connection (reverse
  dependencies) → use `outsystems-dependency-impact`.
- User wants raw data only — return JSON.
- App is huge and the user wants a specific subsystem only — they're
  better served by a `context_search` follow-up.
