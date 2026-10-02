---
name: outsystems-tenant-architecture
description: "[Beta] Generate an interactive HTML graph of an OutSystems Developer Cloud tenant's assets (web/mobile apps, agents and agent definitions, AI model connections, knowledge bases, libraries, integrations) with filter-by-type controls, where each asset is deployed (revision drift per environment), a 7-day Production traffic/error overlay and an AI governance view (model providers, Trial vs Customer entitlement, test/demo-named and stale agents). ONE tenant-level pass per invocation, no per-app deep dives (use outsystems-app-architecture for one app); also the entry point for 'architecture of every app' requests, which it confirms before any per-app run. First run 2-5 min; cached re-runs ~5s. Use when the user asks for a tenant overview, architecture diagram, asset inventory, 'what's in my tenant', 'show me my apps', 'what is deployed where', an AI inventory, 'audit my AI', 'which models are we using', 'show me my agents', AI governance, or similar."
license: MIT
compatibility: Needs an agent that can run shell commands and Python 3.7+ (standard library only), with the OutSystems MCP server connected and signed in. Validated on Claude Code. Claude Desktop's Chat tab has no shell and cannot run it. The output HTML embeds the tenant data but loads its graph library and fonts from public CDNs; offline it falls back to a plain asset table.
allowed-tools: Bash(python3 *) Bash(cp *) Bash(mkdir *) Write mcp__plugin_outsystems_outsystems__auth_status mcp__plugin_outsystems_outsystems__env_list mcp__plugin_outsystems_outsystems__app_list mcp__plugin_outsystems_outsystems__env_apps mcp__plugin_outsystems_outsystems__app_health mcp__plugin_outsystems_outsystems__context_agents mcp__plugin_outsystems_outsystems__context_connections mcp__outsystems__auth_status mcp__outsystems__env_list mcp__outsystems__app_list mcp__outsystems__env_apps mcp__outsystems__app_health mcp__outsystems__context_agents mcp__outsystems__context_connections
metadata:
  version: "1.9.0"
  maturity: beta
  author: OutSystems
---

**Beta Feature.** This skill is a Beta Feature: a non-final OutSystems capability provided to collect customer feedback. It can change significantly, including through breaking changes, or be discontinued. The first time you use this skill in a conversation, tell the user it's a Beta Feature and share https://www.outsystems.com/legal/beta-features-agreement.

# OutSystems Tenant Architecture

Produces a single HTML file with a force-directed graph of every asset in
the user's ODC tenant, where each one is deployed, and a 7-day Production
traffic/error overlay. OutSystems dark theme, filter-by-type,
by-environment and by-health sidebar, click for asset details, and a
Table view. Caches results across sessions, so a re-run within the hour
takes seconds.

The tenant data is embedded in the file, so it can be mailed or archived
as-is. It is **not** fully self-contained: the graph library
(vis-network 9.1.9, pinned with Subresource Integrity, from unpkg with a
jsDelivr fallback) and the web fonts load from public CDNs. With both CDNs
unreachable (offline, or blocked by a proxy) the page says so and shows
the asset table with every filter and the detail panel; fonts fall back
to system fonts.

## Prerequisites

- The OutSystems MCP server is connected and signed in. This skill reads
  the tools named below; tool names here are the server's own, and your
  harness may show them with a prefix (in Claude Code,
  `mcp__plugin_outsystems_outsystems__app_list` for `app_list`).
- A shell with `python3` (3.7 or later, standard library only). The
  scripts read the saved tool results from disk and write the HTML; they
  never call the server and hold no sign-in of their own.
- `<skill-folder>` below is this skill's own folder: the one holding this
  file (in the OutSystems plugin, `skills/outsystems-tenant-architecture/`), so
  `<skill-folder>/scripts/build.py` is the script next to it. Values in
  angle brackets are placeholders you substitute; quote every path, since
  a home folder can contain spaces.
- No shell available? Stop and tell the user this skill needs one (for
  example Claude Code, not Claude Desktop's Chat tab); don't try to build
  the page by hand.

**The core rule: keep large data off the model's context.** Tool results
go to disk, `build.py` reads them from there, and the HTML comes out the
other side. Never read a saved result back into the conversation.

## Procedure

### Step 0 — Scope guard

This skill produces **one tenant-level visualization** per invocation,
**not per-app deep dives**. Read the user's request and pick the
matching branch:

**Branch A — Tenant-only view** ("show me my tenant", "what's in my
tenant", "tenant architecture", "show me my apps")
→ Continue the procedure as normal.

**Branch B — Tenant + per-app deep dives** ("show me everything in
detail", "architecture of every app", "deep dive on each app")
→ **Stop and ask the user for confirmation, before any MCP call.** Don't
list the apps to count them first: the question needs no count. Chaining
`outsystems-app-architecture` over every app costs ~10K tokens and
~0.5-1 min per app (100 apps = ~1M tokens and 30-60 min). Offer three
choices:

- **Tenant only (recommended):** produces the tenant graph in 2-5 min.
  Run `outsystems-app-architecture` afterwards only for the apps the user
  wants to drill into.
- **Tenant + per-app for ALL apps:** runs `outsystems-app-architecture`
  for each app, at the per-app cost above.
- **Cancel.**

If the user picks the per-app option, the tenant graph (Branch A) gives
the app count; don't fetch `app_list` just to put a number in the
question.

Default to Branch A on ambiguity. A request for "everything" usually
means the tenant view, and chaining every app by accident is what turns a
3-minute run into a 20-minute one.

### Step 0.5 — Demo prep tip

If the user is **prepping for a demo**: run this skill once **before
the demo** to warm the cache. During the demo, the same invocation
hits Step 5 (cached re-render) in ~5 seconds. Don't run the first-time
path live in a demo: the 2-5 min wait is long on screen.

### Step 1 — Resolve the tenant

Call `auth_status` and read two top-level fields: `tenant_id` →
`TENANT_ID`, and `tenant_hostname` → `TENANT_HOSTNAME` (e.g.
`acme.outsystems.dev`; the graph's root node and header use its first
label). Do not read anything under `claims`: those are raw sign-in
claims, not a contract.

On the remote (HTTP) server this call only runs while the sign-in is
valid, so it always reports `logged_in: true`. An expired or missing
sign-in surfaces as an authentication error on the first MCP call (this
one or the probe in Step 2): stop and ask the user to sign in to the
OutSystems MCP server again, then start over. Don't retry in a loop.

Create this skill's cache folder for the tenant. The script prints the
folder's path; the steps below call it `<cache-folder>`:

```bash
python3 "<skill-folder>/scripts/build.py" --cache-dir <TENANT_ID>
```

### Step 2 — Cache freshness (only if cache exists)

If `<cache-folder>/meta.json` is present:

1. Call `app_list` with `limit: 1` (tiny — ~300 tokens).
2. Compute `AGE = now - meta.fetched_at`.
3. If `AGE < 3600` **and** `probe.total == meta.total` **and**
   `meta.overlays_fetched_at` is a number **and** `meta.schema` is `1`
   → **cache valid, jump to Step 5** (cached re-render). `meta.total` is the server-reported
   tenant-wide `total` from the fetch, so the two figures are comparable
   even when the fetch needed more than one page. A `meta.json` without
   `overlays_fetched_at` (written by an older version, or a build without
   the overlays) is stale: deployments and health change without the
   asset total changing, so refetch.

If the user said "refresh" / "fresh data" / "rebuild", skip this step.

### Step 3 — Fetch (two parallel rounds)

**Round 1** — call **both** in a single message so they run concurrently:

- `env_list` — small response, ~1 KB
- `app_list` with `limit: 500` (the server's maximum page size; larger
  values are clamped to 500), or `limit: 50` on a harness that truncates
  large tool results (see Harness notes). The response is an envelope
  `{results, total, displayed, truncated, next_offset, ...}`; `build.py`
  reads it, you never do.

Save the env response verbatim to `<cache-folder>/envs-raw.json`. Its rows give
you each environment's `key`, `name` and `purpose` (`Development`,
`NonProduction`, `Production`) for round 2.

**Round 2** — in a single message, call:

- `env_apps` with `env_key: <key>` for **every** environment (no `offset`
  on this first call: older servers reject unknown arguments). Deployed
  apps and agents per environment, 100 rows per response by default.
  **If the tool's input schema lists a `limit` argument**, also pass
  `limit: 500` (`limit: 50` on a harness that truncates large tool
  results): on Claude Code one 500-row page is auto-saved to disk, so a
  large environment costs no writing at all. If the schema has no
  `limit`, don't pass one; the call would be rejected.
- `app_health` for **every `Production`-purpose environment** with
  `env_key: <key>`, `apps: ""` (every app in the stage), `hours: 168`, and
  `limit: 1000` (`limit: 50` on a truncating harness). Don't pass
  `metrics` (the default set is what the overlay shows). If the tenant
  has no Production environment, skip this call; `build.py` records why.
- `context_agents` and `context_connections` (the **AI governance**
  view), each with `owned_only: false`, `limit: 100` (`25` on a
  truncating harness) and `offset: 0`. Tenant-wide, so no `app`. They
  report provider, entitlement (Trial / Customer) and dates for **Agent
  apps** and **AI model connections only**: agent definitions, knowledge
  bases and MCP / search-service / A2A / AI-native connections are not
  covered by these tools and show as "not reported" in the view.

Why a 168-hour window: this is an inventory view, so the questions are
"which apps had no traffic this week" and "which had errors this week".
`app_health`'s own description warns that wide windows average away an
incident, so the overlay is **not** an incident view and the report must
not present it as one (for a live incident, use `app_health` with its
default 24 h, or the app's logs and traces).

**Saving every response** (app_list, env_apps, app_health, context_agents,
context_connections) — inspect only the result text, never the payload:

- **If it contains** `"Output has been saved to <path>"` (Claude Code's
  harness auto-save for large results, such as a 500-row app_list page of
  ~90 KB; a 100-row env_apps page, ~31 KB, usually stays inline): that path is the page file.
  The same notice tells you to read the file in chunks before summarizing
  it: that is Claude Code's generic instruction, and this skill's contract
  overrides it. Pass the path to `build.py`; never read the file.
- **If it returned an inline JSON object** (small responses on Claude
  Code; every response on a harness without auto-save): write it
  verbatim — envelope included — to `<cache-folder>/apps-page-<N>.json`,
  `<cache-folder>/env-apps-<ENV_KEY>-<N>.json` or `<cache-folder>/health-<ENV_KEY>-<N>.json`.
  Write the two AI governance pages in the compact form below to
  `<cache-folder>/ai-agents-<N>.json` and `<cache-folder>/ai-connections-<N>.json`.
  That is the page file.
- **If a call failed** (for example `app_health` on a tenant whose
  analytics are not enabled, or an `env_apps` error for one environment):
  a server error or timeout (5xx, 504) is retried once, every failed call
  in one parallel message; an authentication error is never retried (see
  Step 1). A call that fails again keeps its one-line error message for
  Step 4's `--health-skipped` / `--deployments-skipped` / `--ai-skipped`.
  A failed overlay never blocks the graph.
- **On a refresh** (the cache already holds a build), a failed call would
  turn a section the cache has whole into "skipped". Before building, tell
  the user which sections would be lost and ask: rebuild now with them
  skipped, or keep the current page and refresh later. `build.py` always
  writes `<cache-folder>`, whatever the output file, so a build to a
  second file replaces the cache too; never offer that as a way to keep it.

**Write every response of this run.** On a refresh too, every page file
passed to `build.py` holds a response fetched in this run, written in
full, even when it looks identical to the page saved last time. Never
reuse a page file from an earlier run, never patch, splice or re-shape a
saved page (beyond the compact form below), and never `touch` one:
`build.py` dates each part of the page from its page files' save times,
and warns when they span more than one fetch.

**Compact form of the AI governance pages.** The `context_agents` and
`context_connections` rows carry descriptions and empty layout objects
that `build.py` never reads, about 70% of each page. When a page arrives
inline, write only these fields of each `data[]` row, in compact JSON:
`key`, `name`, `isPublic`, `timestamp`, `providerName`,
`additionalData.{revisionDateTime, providerId, entitlement}` (leave out
any that a row does not carry). Copy the envelope keys `total`,
`truncated`, `next_offset` and `pagination` unchanged: `build.py` checks
the page chain from them. A page Claude Code auto-saved is passed as its
path, as is.

More pages may be needed (tenants above one app_list page, environments
above 100 deployments on a server that pages `env_apps`, Production
environments above one `app_health` page). You do not decide that;
Step 4's `build.py` does, from the envelopes.

### Step 4 — Build (fresh mode)

One Python invocation does the entire pipeline: transform raw MCP
responses into the bundle (`<cache-folder>/tenant-data.json`, see Data shape
contract), then render the template from it. `<output-file>` is
`tenant-architecture.html` in the user's working folder (absolute path) unless they asked
for another one.

```bash
python3 "<skill-folder>/scripts/build.py" "<cache-folder>" "<output-file>" \
  --tenant-id "<TENANT_ID>" --tenant-hostname "<TENANT_HOSTNAME>" \
  --apps "<apps page 1>" \
  --deployments "<DEV_KEY>=<dev page 1>" "<TEST_KEY>=<test page 1>" "<PROD_KEY>=<prod page 1>" \
  --health "<PROD_KEY>=<health page 1>" \
  --ai-agents "<ai agents page 1>" --ai-connections "<ai connections page 1>"
```

- `--apps` takes every app_list page, in order.
- `--deployments` and `--health` take one `<env_key>=<page file>` per
  page; a second page of the same environment is another
  `<env_key>=<file>` after the first.
- For a failed call, pass `--deployments-skipped "<env_key>=<error>"` or
  `--health-skipped "<env_key>=<error>"` instead of a page. An
  environment given neither is rendered as "not fetched".
- `--ai-agents` / `--ai-connections` take every page of each, in any
  order (the pages carry their offsets). Pass both, or, when either call
  failed, `--ai-skipped "<error>"` instead of both.

`build.py` exits `0` when every page set is whole. If it exits `3` it
prints one `INCOMPLETE:` line per page set that has a next page, e.g.:

```
INCOMPLETE: app_list returned 500 of 515 assets (the last page is truncated). Call app_list with limit: 500, offset: 500, ...
INCOMPLETE: env_apps for environment acme-dev (8843...) returned 100 of 280 deployments and has 2 more pages. Call env_apps with env_key: 8843..., offset: 100, and again with env_key: 8843..., offset: 200 (all in one parallel message), ...
INCOMPLETE: app_health for environment acme (2ce1...) has a further page. Call app_health with the same arguments (...) plus offset: 1000, ...
INCOMPLETE: context_agents: 100 rows received, more exist; fetch context_agents with the same arguments plus offset: 100
```

Make every printed call in one parallel message (same `limit` as the
first page, plus the printed `offset`), save each response the same way,
and re-run with **every page of every set, in order**. Repeat until exit
`0`. Never loop more than `ceil(total / limit)` times per set (two for a
515-asset tenant at 500), and stop and report instead of re-fetching
when `build.py` prints the same `offset` twice.

`env_apps` has two server generations and `build.py` handles both:

- **Newer servers** accept `offset` (and, newer still, `limit`) and set a
  numeric `next_offset` while more rows exist → an `INCOMPLETE` line that
  names every remaining offset: fetch them all in one parallel message,
  with the same `limit` as the first page.
- **Older servers** take no offset: a truncated response has no (or a
  null) `next_offset` and cannot be continued. `build.py` keeps those
  100 rows, marks that environment **PARTIAL** in the HTML and in its
  output, and never counts it as proof that an app is not deployed.
  Don't retry it with `offset` (the call is rejected) and don't try to
  enumerate it with `search`.

`exit 1` with `BAD PAGE` means a page cannot be trusted: it repeated an
earlier page (the `offset` was not passed), it was saved without its
envelope, it is not valid JSON, it carries a harness truncation marker
(`Warning: truncated output` / `…N tokens truncated…`), or an
`app_health` page was passed under the wrong `env_key`. Fix the fetch
(smaller `limit` for a truncated page), do not retry the same files. A
second `INCOMPLETE` variant, "the pages passed cover N of T ... but the
last page is not truncated", means either a page was not passed or the
data changed between the page fetches: re-run with every saved page from
the first upward, and if they were all already passed, discard them and
fetch that set again from the first page.

`build.py` writes no cache file while pages are missing, repeated or
stripped, so a partial page can never be rendered or cached as "the whole
tenant". No `jq`, no separate transform-then-inject step.

### Step 5 — Build (cached mode)

When the cache is valid (jumped from Step 2), `build.py` is called with
just the cache and output path — it renders the bundle already on disk
(`tenant-data.json`). An older bundle or the pre-bundle file layout exits
`3` with `STALE`: go back to Step 3.

```bash
python3 "<skill-folder>/scripts/build.py" "<cache-folder>" "<output-file>"
```

The HTML shows when each data set was fetched ("Data As Of": assets,
deployments, health window, AI governance), so a re-render within the
hour is honest about its age.

### Step 6 — Report (4–7 lines)

`build.py` prints the facts on stdout (asset groups, per-environment
deployment status, the health summary); relay them, don't recompute:

- Output file path
- Asset count + group breakdown (the `assets:` line; name any unknown
  types it lists under "Other")
- Deployments: each environment complete / **PARTIAL** (N of T listed,
  the rest could not be fetched) / skipped with the reason, plus the
  revision-drift count, and the deployed assets with no `app_list`
  record when the line names them (deployed, but with no source-control
  record and no node; typically orphaned agent definitions)
- Health: the window, the per-class counts ("had errors", "no traffic",
  "no reading"), and **say it is a 7-day inventory view, not an incident
  view**. If it was skipped, say why (no Production environment, or the
  call's error). Never call any app "healthy": `appScore` is a latency
  score (a zero-traffic app scores 100) and is not shown at all
- AI governance: the `ai governance:` line (agents, model connections,
  Trial / Customer / not reported, providers, rows not in the asset list,
  and the flagged names it lists), and say that agent definitions and
  non-model connections are not covered by that source. Name the flags as
  what they are: a name heuristic, and dates
- Every `warning:` line `build.py` printed, in particular one saying the
  page files span more than one fetch
- Cache state — "used (Xs old)" or "refreshed"
- Opens in any browser; the graph needs unpkg or jsDelivr reachable,
  otherwise the page falls back to the asset table

## Token budget — by tenant size

The first-run cost depends on how much of the data the harness saves to
disk for you. Claude Code saves a tool result once it passes a size limit it sets in
tokens (measured between 45 and 65 KB of JSON; a 500-row `app_list` page,
~90 KB, is saved); anything smaller arrives
inline and the model has to write it out, paying for it twice. A full
100-row `env_apps` page (~31 KB) and the AI governance pages usually stay
under that line, so each environment adds a few thousand tokens. On a
harness without auto-save every page passes through the model once and
is written out once — see Harness notes.

Measured live on Claude Code (499 assets, 3 environments, one of them
with 280 deployments on a server that pages `env_apps` in 100-row
windows only): about 5 minutes, most of it writing the 100-row
`env_apps` pages out inline (~30 KB each); the asset list was
auto-saved and the AI governance pages written in compact form. Every
further 100-row window of a large environment adds about 2.5 minutes,
which is why `limit: 500` is used whenever the server offers it.

| Tenant size | Mechanism | Tokens (first run) | Wall time |
|---|---|---|---|
| **Small** (<~150 assets) | Every response inline → model writes it to disk | ~5-10K | ~2-3 min |
| **Mid** (~150-300 assets) | Asset list inline or borderline auto-save; overlays inline | ~15-30K | ~3-7 min |
| **Large** (>~300 assets) | Asset list auto-saved (path passed straight to build.py); `env_apps` and AI pages inline | ~15-30K, mostly the overlays | ~4-7 min |
| **Cached re-run (any size)** | Probe + build.py only | ~2-3K | ~5 s |

**The trap:** a response just under the auto-save line costs the most,
because it is paid twice (once in the MCP result, once in the write).

**Why runs get slow:** if the model reads an auto-saved file back in,
every later turn carries the full asset list. That turns a 3-minute run
into 15-25 minutes. See the first anti-pattern below.

## Data shape contract

**The bundle is the interface.** `build.py` writes one file,
`<cache-folder>/tenant-data.json`, and the render step reads nothing else:
`{schema: 1, tenant, envs, assets, deployments, health, ai}`, each part
injected into the template `const` of the same name (below). The render
step validates the bundle first: a missing or mistyped field exits `1`
naming the field (`assets[2].k: expected a string, got int`), an older
schema exits `3` (`STALE`). Anything that produces this bundle can be
rendered by the same template. Versioning: adding a field keeps the
schema; removing, renaming or changing the meaning of one bumps it.

```js
ASSETS = [
  { k: "uuid", n: "name", t: "AssetType", r: number, d: "YYYY-MM-DD", x: boolean },
  ...
]
ENVIRONMENTS = [
  { key: "uuid", name: "...", purpose: "...", host: "..." },   // host = env row's builtinDomain (older payloads: hostname)
  ...
]
TENANT = { id: "uuid", realm: "string", hostname: "string", region: "string",
           hosting: "string", fetched_at: epochSeconds }   // the oldest app_list page's save time
// realm = first label of auth_status.tenant_hostname (else derived from env domains)

DEPLOYMENTS = null | {                       // env_apps overlay
  fetched_at: epochSeconds,
  envs:   { "<env key>": { status: "complete" | "partial" | "skipped",
                           shown, total, unmatched, reason? } },
  listedTypes: ["Agent", "AgentDefinition", "MobileApplication", "WebApplication", ...],
  assets: { "<assetKey>": [ { env: "<env key>", rev: number, date: "YYYY-MM-DD", url: "...",
                               as?: "<deployed name>" } ] },   // when it differs from app_list's
  drift:  { "<assetKey>": { env: "<env key>", deployed: number, latest: number } },
  unlisted: [ { k: "<applicationKey>", n: "<env_apps name>", t?: "<assetType>",  // no app_list record
                deps: [ { env, rev, date, url } ] } ]
}
HEALTH = null | {                            // app_health overlay
  fetched_at, since: "ISO", to: "ISO", hours: 168,
  skipped?: "why",                           // e.g. no Production environment
  envs:   { "<env key>": { status: "complete" | "partial" | "skipped", reason?,
                           metrics: [...], advisory?, unresolved: [...], rows, unmatched } },
  assets: { "<assetKey>": { cls: "errors" | "traffic" | "noTraffic" | "noReading",
                            by_env: { "<env key>": { requests?, errors?, errorPercent?,
                              responseTimeP95?, uniqueUsers?, lastErrorOccurred?, cls, absent? } } } }
}
AI = null | { status: "skipped", reason }    // context_agents + context_connections
   | { status: "complete", fetched_at, coveredTypes: ["AIModelConnection", "Agent"],
       agents:      [ { k, n, pub, date, testDemo, stale, listed } ],
       connections: [ { k, n, provider, providerId, entitlement, date, listed } ],
       stats: { totalAgents, totalConnections, trialConns, customerConns,
                unreportedEntitlementConns, unreportedProviderConns, publicAgents,
                testDemoAgents, staleAgents, staleDays, providers: [ { name, count } ] },
       unlisted: [ "<key>" ] }               // indexed rows absent from app_list
// provider / entitlement = "not reported" when the row carries none
```

**AI governance semantics.** Rows join assets by key (the row `key` is the
asset key). An agent's `n` is its `app_list` name when it is listed (the
index carries a compact form: "TestAgent1_0" for "Test Agent 1.0"). Some
agents can be indexed for context search but absent from `app_list`; they
are kept and flagged `listed: false`. `testDemo` is a name heuristic: one
of test, tmp, temp, demo, untitled, xxx, 123, sample, scratch or wip as a
whole word of either name, where a change of case or a digit also breaks
words ("AgenticRegressionTest" counts, "Latest" does not). `stale` means
no update in 180+ days. Agent definitions,
knowledge bases and non-model connections are shown as "not reported by
the governance source", never hidden.

Known asset types (each colored distinctly; `TYPES` in the template,
mirrored by `ASSET_TYPE_HUBS` in `build.py`):

| Hub | Types |
|---|---|
| Applications | `WebApplication`, `MobileApplication`, `Workflow` |
| AI | `Agent`, `AgentDefinition`, `AIModelConnection`, `KnowledgeBase`, `AINativeConnection` |
| Libraries | `LowCodeLibrary`, `ExtensionLibrary`, `MobileLibrary`, `ExternalLibrary`, `WidgetLibrary` |
| Integrations | `ExternalConnection`, `MCPConnection`, `SearchServiceConnection`, `A2AConnection` |

`Agent` and `AgentDefinition` are separate `app_list` asset types; the
"Agents" tile counts both and names each. Unknown types render grey
under their own **Other** hub and tile (and `build.py` lists them), never
inside a real category.

**Deployment semantics.** `drift` compares the latest revision
(`app_list`) with the revision running in the highest-purpose environment
the asset is deployed in (Production > NonProduction > Development, then
`order`). "Not deployed anywhere" covers only `listedTypes`, the types
`env_apps` actually lists: libraries never get a deployment record (they
ship inside the apps that consume them) and the server drops `Workflow`
rows from `env_apps`. While any environment is partial or not fetched the
filter reads "Not in any deployment list" and says why. `env_apps` reads
the deployed inventory and `app_list` reads source control, so the two
can disagree. A deployment whose asset has no source-control record
(typically an orphaned agent definition) is kept in `unlisted` under its
`env_apps` key, name and `assetType` (on servers that send it): it has no
node, the Table view lists it in a section of its own, and the report
line counts it per environment and per type. A row's `name` is the name
at the deployed revision, so a renamed asset can run under its old name;
the detail panel shows it as "deployed as".

**Health semantics** (from `app_health`'s own contract). Classes:
`errors` = `errors > 0`, `errorPercent > 0` or a `lastErrorOccurred` in
the window; `noTraffic` = `requests` reads 0, or the app is deployed in
that environment and has no row in a result set the server proved
complete; `noReading` = `requests` unavailable, or no row in a result set
that was not proven complete; `traffic` = requests with no recorded
error. A metric in the `metrics` echo but absent from a row is shown as
"unavailable", never as zero. `appScore` is never carried into the HTML.

## Cache rules

- Location: the folder `build.py --cache-dir <TENANT_ID>` prints (one per
  tenant, under the shared `outsystems-skills` cache root).
- TTL: 1 hour, for the assets and the overlays alike.
- Freshness check: compare `total` from `app_list` with `limit: 1`
  against the cached `meta.total` (the server-reported total from the
  last fetch), and require `meta.overlays_fetched_at`. Cheap (~300 tokens).
  `meta.fetched_at` is the save time of the oldest page file the build
  read, so the hour runs from the fetch, not from the build.
- The overlays are not probed: a deployment or a traffic change inside
  the hour is not detected. The HTML shows each data set's fetch time,
  and a "refresh" request always refetches.
- Known false-negative: if N assets were added AND N deleted between
  fetches, count is stable and we'd miss the delta. Acceptable for 1-hour
  TTL. Force refresh on user request.
- `outsystems-dependency-impact` reuses this cache's `tenant-data.json`
  as its asset list when it is under 24 hours old.

## Harness notes

- **Claude Code**: MCP results above its size limit (measured between 45
  and 65 KB) are auto-saved to disk by
  the harness ("Output has been saved to <path>") and never enter
  model context. The saved file is the raw JSON payload, which is what
  `build.py` reads. This is what makes the Large-tenant band in the
  Token budget table so cheap, and it's also why the first anti-pattern
  below exists — don't undo the saving by reading the file back in.
- **Harnesses without auto-save** (Cursor, Kiro and others): every
  response arrives inline. Write each one verbatim, envelope included, to
  its page file (the AI governance pages in their compact form, Step 3);
  never hand-edit or re-shape one otherwise. Expect roughly the
  Mid-band token cost or more even for large tenants.
- **Harnesses that truncate large tool results** (for example Codex,
  which keeps the head and the tail, adds a
  `Warning: truncated output (original token count: N)` header and a
  `…N tokens truncated…` marker, and drops the rows in between): page
  `app_list` and `app_health` with `limit: 50` and follow the
  `INCOMPLETE` offsets; `env_apps` has no `limit` (a full 100-row response
  is ~31 KB), so if it comes back truncated pass that environment as
  `--deployments-skipped "<key>=response truncated by the harness"` and
  say so in the report. `build.py` refuses a page that carries the
  truncation marker or is not valid JSON (`BAD PAGE`, exit 1).
- Cached runs and re-renders (Step 5) cost the same on every harness —
  that path never touches `app_list`.

## Troubleshooting

- **An MCP call fails with an authentication error** → the sign-in
  expired: ask the user to sign in to the OutSystems MCP server again,
  then start over. Don't loop.
- **The OutSystems tools are missing** → the MCP server is not connected;
  ask the user to connect it (see the main OutSystems skill's setup).
- **`python3: command not found`** → ask the user to install Python 3.7
  or later; nothing else is needed.
- **`build.py` exits 3 (`INCOMPLETE: ... offset: N`)** → a page set has
  a next page (app_list, one environment's env_apps, or one environment's
  app_health). Make every printed call with its `offset`, save, re-run
  with every page (Step 4).
- **`build.py` exits 3 (`INCOMPLETE: the ... pages passed cover N of T`)**
  → a page was not passed, or the data changed while you were fetching
  pages. Pass every saved page; if you already did, fetch that set again
  from the first page and rebuild.
- **`build.py` exits 1 (`BAD PAGE: ...`)** → a page repeated an earlier
  one (the `offset` was not passed), lost its envelope, is not valid
  JSON, carries a truncation marker, or an app_health page was passed
  under another environment's key. Fix the fetch, do not retry the same
  files.
- **`build.py` exits 2 (`usage: ... not in envs-raw.json`)** → an
  `<env_key>=` does not match any environment in `<cache-folder>/envs-raw.json`;
  use the `key` values from the env_list response.
- **`build.py` exits 1 (`cache build failed: KeyError(...)`)** → a raw
  response is missing a field the script expects (see Data shape
  contract). Check the saved file with `head -c 600 <path>` in a shell,
  not by reading it into context.
- **An environment shows PARTIAL** → an older server returned 100 of
  its deployments and takes no offset. Expected; report it.
- **`app_health` fails** (e.g. analytics not available) → pass
  `--health-skipped "<key>=<error line>"`; the graph and deployments
  still render and the report says the overlay was skipped and why.
- **The page shows "Graph library could not load"** → unpkg and jsDelivr
  are both unreachable from that browser. The table view works; open the
  file on a network that allows either CDN to see the graph.
- **No envs returned** → `build.py` falls back to `region=us-east-1`,
  `hosting=oscloud`, `realm=<tenant_hostname first label, else tenant-id prefix>`.

## Anti-patterns — do NOT do these

- 🔴 **Do NOT read a harness-saved file (Claude Code).** When Claude
  Code's harness emits *"Output has been saved to <path>"*, the path goes
  **directly to build.py** as a command-line argument. The model must
  **never** read that file into context. A 280-asset tenant's payload is
  ~50 KB ≈ 12-15K tokens; on a 1000-asset tenant it's ~150 KB ≈ 35-50K
  tokens. Once that's in context, every subsequent turn processes it —
  turning a 3-min skill into a 15-25 min skill. If you need to check
  content for debugging, run `head -c 1000 <path>` in a shell. The
  contract is: data goes through disk → build.py → output HTML, never
  re-entering the model's context.
- 🔴 **Don't dump an inline payload back into the conversation or re-read
  the cache files (harnesses without auto-save).** Once a response is
  saved verbatim to its page file (envelope intact), pass that path to
  `build.py` — never re-print or re-load the raw payload into context on
  a later turn. The cost is the same as above.
- **Don't parse the payloads yourself** (no `jq`, no hand-written
  scripts over the saved files or the bundle): `build.py` does the
  transform, and its report lines name what the user asks about (flagged
  agents, Trial connections, deployed assets missing from the asset list).
- **Don't reuse, patch or `touch` a saved page on a refresh.** Comparing a
  new response with an old file by eye is how a changed revision slips
  through; write the new response (Step 3).
- **Don't state a health verdict.** No "healthy", no "all good", no
  score. Report errors, traffic and missing readings as `build.py`
  prints them; "no reading" is not "fine".
- **Don't call the 7-day overlay an incident view.** It answers "what
  had traffic / errors this week", not "what is broken now".
- **Don't chain into `outsystems-app-architecture` per-app** without
  Step 0's explicit user confirmation. A "tenant + every app" request
  has 100× the cost; gate it.
- **Don't fetch the asset list with a `limit` below 500 on Claude
  Code.** 500 is the server's page cap and one 500-row page (~90 KB) is
  auto-saved; smaller pages only add calls. Values above 500 buy nothing:
  the server clamps them and flags `truncated: true`. (On a truncating
  harness the opposite holds — use 50, see Harness notes.)
- **Don't pass `offset` to `env_apps` unless `build.py` printed one.**
  Older servers reject it; `build.py` only asks when the server offered
  a `next_offset`.
- **Don't concatenate pages by hand or read the envelopes yourself.**
  Pass every saved page to `build.py`; it merges, de-duplicates and
  refuses to render while a page is missing.

## When NOT to use

- User wants one app's architecture → use `outsystems-app-architecture`.
- User wants raw data only → return JSON, skip the HTML.
- User wants a non-graph layout (treemap, sunburst) → fork the template.
- User is chasing a live incident → use `app_health` (default 24 h),
  logs and traces directly; this overlay is a weekly inventory view.
