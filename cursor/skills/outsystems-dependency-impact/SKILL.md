---
name: outsystems-dependency-impact
description: "[Beta] Build an interactive HTML REVERSE-dependency explorer — answers 'who depends on this library/agent/connection?' from the platform's deletion-impact analysis (read-only; nothing is deleted). One named target is one analysis: seconds, a few K tokens. A whole-tenant map is one analysis per library/agent/connection in parallel batches (estimate: ~0.5K tokens per target plus ~0.1–0.15K per dependent found). Use ONLY for reverse questions like 'who depends on [library/agent]', 'if I publish [library] who breaks', 'blast radius of [library/agent]', 'reverse dependency map', 'library impact audit', 'agent impact audit'. For forward questions about a specific app ('what does App X depend on', 'deps of App X'), use outsystems-app-architecture or the app's references directly."
license: MIT
compatibility: Needs an agent that can run shell commands and Python 3.8+ (standard library only), with the OutSystems MCP server connected and signed in. Validated on Claude Code. Claude Desktop's Chat tab has no shell and cannot run it.
allowed-tools: Bash(python3 *) Bash(cp *) Bash(mkdir *) Write mcp__plugin_outsystems_outsystems__auth_status mcp__plugin_outsystems_outsystems__app_list mcp__plugin_outsystems_outsystems__app_refs mcp__plugin_outsystems_outsystems__env_list mcp__plugin_outsystems_outsystems__deploy_impact mcp__plugin_outsystems_outsystems__deploy_impact_status mcp__outsystems__auth_status mcp__outsystems__app_list mcp__outsystems__app_refs mcp__outsystems__env_list mcp__outsystems__deploy_impact mcp__outsystems__deploy_impact_status
metadata:
  version: "1.5.0"
  maturity: beta
  author: OutSystems
---

**Beta Feature.** This skill is a Beta Feature: a non-final OutSystems capability provided to collect customer feedback. It can change significantly, including through breaking changes, or be discontinued. The first time you use this skill in a conversation, tell the user it's a Beta Feature and share https://www.outsystems.com/legal/beta-features-agreement.

# OutSystems Dependency Impact

Produces a single-file HTML reverse-dependency explorer (it loads only its
fonts from a public CDN). Pick a
library, agent or connection — the page shows every asset that would
break if it were removed, in which environments, at which deployed
revision, and with what severity (`Error` / `Warning`).

The data comes from the platform's **deletion-impact analysis**:
`deploy_impact {key, delete: true}`, polled with `deploy_impact_status`.
It is an analysis only — nothing is deleted, and the MCP server calls no
delete endpoint for it. For "if I publish library X, who breaks?" it
lists everyone who depends on X; that is the most a pre-publish check can
give for a library (the deployment variant of the analysis does not work
for library types).

## Cost and time (estimates)

| Question | Calls | Wall time | Tokens |
|---|---|---|---|
| One named target | 1 launch + 1–3 polls | seconds | ~3–5K, plus ~0.1–0.15K per dependent |
| Whole-tenant map, N targets | N launches + N+ polls, 10 per message | ~0.5–1 min per 10 targets | ~0.5K × N, plus ~0.1–0.15K per dependent |

These are estimates, not end-to-end measurements. Measured live: a
launch returns in about a second, and finished reports came back for
every analysis polled; a heavily used UI library had 74 dependents in a
report of about 37 KB (roughly 9K tokens). The whole-tenant map is still
one analysis per target, so for a large tenant it is not cheap — prefer
the one-target path whenever the user names a target.

## Prerequisites

- The OutSystems MCP server is connected and signed in. This skill reads
  the tools named below; tool names here are the server's own, and your
  harness may show them with a prefix (in Claude Code,
  `mcp__plugin_outsystems_outsystems__deploy_impact` for `deploy_impact`).
- A shell with `python3` (3.8 or later, standard library only). The
  script reads the saved analysis results from disk and writes the HTML;
  it never calls the server and holds no sign-in of its own.
- `<skill-folder>` below is this skill's own folder: the one holding this
  file (in the OutSystems plugin, `skills/outsystems-dependency-impact/`), so
  `<skill-folder>/scripts/build.py` is the script next to it. Values in
  angle brackets are placeholders you substitute; quote every path, since
  a home folder can contain spaces.
- No shell available? Stop and tell the user this skill needs one (for
  example Claude Code, not Claude Desktop's Chat tab); don't try to build
  the page by hand.

## The reality checks

- **One analysis answers one target.** There is no tenant-wide reverse
  index on the server; a map is N analyses.
- **Which asset types the deletion analysis accepts is the platform's
  call.** The MCP server passes any asset key through. Verified live:
  `LowCodeLibrary`. Agents and connections are not verified. A launch the
  platform refuses (`analysis_launch_rejected`) renders as "Deletion
  analysis not available for this asset", never as "no dependents".
- **Only `impactKnown: true` is a verdict.** `impactKnown: false`,
  `processStatus` `Failed` / `Unknown` / still `InProgress`, or a missing
  `report` means the impact is unknown, and the page says so.
- **`report.impactedAssets` is capped at 200.** The count is
  `report.total`; when the list is shorter the page says "Showing N of M".

## Procedure

### Step 0 — Scope detection

Read the user's request and pick the matching branch:

**Branch A — Forward-deps for ONE specific app** ("what does App X use",
"show me the deps of App X", "what's in App X")
→ **Stop. Tell the user this skill is the wrong tool** and route to
`outsystems-app-architecture` (which shows the same forward-dep info
plus screens/entities/actions for ~10K tokens). Do NOT continue the
procedure.

**Branch B — Forward-deps for 2-3 specific apps** ("what do App X and
App Y depend on")
→ **Stop. Skip this skill entirely.** Call `app_refs` on each named
app, all in one message (~3-5K tokens total). Report the deps inline.

**Branch C — Reverse-deps for named targets** ("who depends on lib X",
"if I publish X who breaks", "blast radius of agent Y") — up to about
five named targets
→ Steps 1, 3, 4.5, 5, 6, 8. No tenant-wide asset list, no index.

**Branch D — Whole-tenant map** ("reverse dependency map", "library
impact audit", "audit all my deps")
→ Steps 1–8, with the confirmation gate in Step 4.5.

### Step 1 — Tenant id + environments

In one message:

- `auth_status` — used here only for the tenant id: read the top-level
  `tenant_id` (not `claims.*`). Over HTTP it always says
  `logged_in: true`; an expired sign-in fails this call (or any other)
  with an authentication error, in which case ask the user to sign in to
  the OutSystems MCP server again and retry once.
- `env_list` — environment names for the page. Save it to
  `<cache-folder>/env-list.json` (`results[].(key, name, purpose)`) once you have
  the cache folder below.

```
TENANT_ID = <auth_status.tenant_id>
```

Create this skill's cache folder for the tenant. The script prints the
folder's path; the steps below call it `<cache-folder>`. Then create the
folder for the per-target records:

```bash
python3 "<skill-folder>/scripts/build.py" --cache-dir <TENANT_ID>
mkdir -p "<cache-folder>/impact/raw"
```

### Step 2 — Cache freshness (Branch D only)

Records in `<cache-folder>/impact/` less than 24h old are reused (Step 5 skips
those targets), so an interrupted map resumes where it stopped. If the
user said "refresh" / "rescan" / "fresh data", start the folder over:

```bash
python3 "<skill-folder>/scripts/build.py" --cache-dir <TENANT_ID> --clear impact
```

(It empties `<cache-folder>/impact`, recreates its `raw/` folder and
prints the path; it can only clear this skill's own record folders.)

Branch C never reuses records; it starts its own folder in Step 3.

### Step 3 — Targets and the asset list

**Branch C:** start a fresh folder for this question, so the page shows
only the targets named now and never an earlier run's records (one
analysis takes seconds):

```bash
python3 "<skill-folder>/scripts/build.py" --cache-dir <TENANT_ID> --clear impact-named
```

Read `impact-named` wherever the steps below say `impact`. Then resolve
each named target with `app_list`
`{search: "<name>"}` (1 match → use it; several → ask the user to pick;
0 → ask for a more specific name). Save each search's response as its own
file, `<cache-folder>/tenant-assets-<n>.json` (never several searches in
one file), and pass every one in Step 6 with its own `--tenant-assets`.

**Branch D:** the full tenant asset list.

**Preferred (fast):** reuse the `outsystems-tenant-architecture` bundle
when that skill ran within the last 24 hours. Its folder is:

```bash
python3 "<skill-folder>/scripts/build.py" --cache-dir <TENANT_ID> --skill outsystems-tenant-architecture
```

It prints that folder's path (it does not create it); call it
`<tenant-cache-folder>`.

If `<tenant-cache-folder>/tenant-data.json` exists and `<tenant-cache-folder>/meta.json`'s
`fetched_at` is under 24 hours old, pass `<tenant-cache-folder>/tenant-data.json`
as the asset list (`--tenant-assets`). Check the age with a one-line
`python3 -c` over `meta.json`; don't read the bundle itself.

**Fallback:** `app_list` with `limit: 500` (larger values are clamped to
500), then `offset: <next_offset>` while `truncated` is true; save each
page as `<cache-folder>/assets-page-<n>.json` and pass every page to `build.py`.
On Claude Code a large page is saved to disk by the harness ("Output has
been saved to <path>") — `cp` it. On a harness that truncates large tool
results a 500-row page arrives cut, so page with `limit: 100` there.

### Step 4 — Filter to targets (Branch D)

Keep assets whose type is a producer — the `assetType` field of an
`app_list` page's `results[]`, or the `t` field of the tenant bundle's
`assets[]` (whose key and name are `k` and `n`):

- libraries: `LowCodeLibrary`, `MobileLibrary`, `ExtensionLibrary`,
  `WidgetLibrary`, `ExternalLibrary`
- agents: `Agent`
- connections: `AIModelConnection`, `AINativeConnection`,
  `ExternalConnection`, `MCPConnection`, `SearchServiceConnection`,
  `A2AConnection`

Save the list (key, name, type) to `<cache-folder>/targets.json`, with a short
`python3` one-liner over the asset list file rather than by reading it.
`targets.json` is your work list only: keep passing the asset list itself
as `--tenant-assets`.

### Step 4.5 — Pre-flight confirmation

Branch C: before launching, name the target(s) and say what runs — "a
deletion-impact analysis on <X>: read-only, nothing is deleted; it lists
who would break if X were removed" — and wait for the user's OK. The
analysis mutates nothing, but it is deletion-adjacent, so it is confirmed
like the destructive calls.

Branch D: compute the estimate from the actual counts and ask the user
before Step 5:

```
count      = len(targets)
rounds     = ceil(count / 10)
wall_min   = rounds * 0.5 .. rounds * 1.0     # estimate: 1-2 model turns per round
tokens_k   = count * 0.5                      # estimate, before dependents
```

Ask: *"Run {count} deletion-impact analyses ({libs} libraries, {agents}
agents, {conns} connections) to map who depends on what? Read-only:
nothing is deleted. Estimate: ~{wall_min} min, ~{tokens_k}K tokens plus
~0.1–0.15K per dependent found. Results are cached for 24h."* Name the
targets in the same message, grouped by type (the main OutSystems skill
names every asset before a deletion-impact analysis); for a long list,
name them all in a compact comma-separated form rather than leaving any
out. Offer three choices: **Yes — all {count}**, **Libraries only ({libs})**, and
**No — cancel**.

On "No" → stop; the asset list stays cached (cheap and useful for other
skills). On "Libraries only", rewrite `<cache-folder>/targets.json` to the
libraries before Step 5, so the build shows only them.

### Step 5 — Analyse

For each target:

1. `deploy_impact` with `key: <target>`, `delete: true` (no `env_key`).
   It returns immediately: `{analysisKey, kind: "deletion", impactKnown: false}`.
2. `deploy_impact_status` with `analysis_id: <analysisKey>` (the
   parameter is `analysis_id`, not `analysisKey`) and `kind: "deletion"`.
   Poll right away — small analyses are often finished by then. While
   `processStatus` is `InProgress`, pause 5–15 seconds between rounds
   (the response has no poll-interval hint), the way the main OutSystems
   skill's "Pacing polls" describes for your harness, with
   `python3 "<skill-folder>/scripts/build.py" --wait <seconds>` (1–60) as
   the pause: in the background where the harness has background tasks
   (Claude Code), in the foreground where it has none (Kiro). It is the
   script, not a shell `sleep`, so it runs within this skill's allowed
   tools. Poll the batch yourself:
   a status-watcher sub-agent waits on one operation at a time, which
   does not fit a batch of ten with a two-minute give-up. Stop at `Finished` or
   `Failed`. On `Unknown`, poll at most 3 more times while it stays
   `Unknown` (restart the count on any other status), then stop with
   `gaveUp: "unknown-status"`. Still `InProgress` after about 2 minutes:
   stop with `gaveUp: "still-in-progress"` (it continues server-side).

The host may prompt before each `deploy_impact`: the tool's annotation is
destructive because of this deletion variant, even though the analysis
changes nothing.

**Batching (Branch D).** Launch 10 targets per message, and in the same
message poll the previous batch's open analyses. Ten is a courtesy to
the shared dependency service and a batch the model can track, not a
server limit: the MCP server gates neither tool on concurrency.

**Probe per type (Branch D).** Put one asset of each type in the first
batch. If the platform refuses it with `analysis_launch_rejected` for a
reason other than an authentication or permission error (401/403) or an
unknown key, record every other asset of that type as skipped instead of
launching it (see the record shape below) — the page then says the
analysis is not available for that type.

**Launch failures.** `analysis_launch_rejected`: record it, do not retry
unchanged. `analysis_launch_unavailable`: retry that target once in a
later batch (the launch has no idempotency key, so a retry after an
ambiguous failure may start a second, harmless analysis). After 5
consecutive `unavailable` launches, stop: report the partial map (it
resumes on re-run) rather than pushing on.

**Progress.** After each round, one line to the user:
`Progress: 40/143 targets · 31 impact known · 9 unknown · est. 6 min left`
(recompute from actual throughput).

**Record per target** → `<cache-folder>/impact/<targetKey>.json`:

```js
{
  "targetKey": "<assetKey>",
  "launch":  <deploy_impact response, or its tool-error payload {error, data: {code}}>,
  "result":  <last deploy_impact_status response>,     // omit if the launch failed
  "resultFile": "raw/<targetKey>.status.json",          // instead of "result", see below
  "gaveUp":  "unknown-status" | "still-in-progress",    // only if polling stopped early
  "harnessTruncated": true,                             // only if the harness cut the result
  "skipped": "type-unsupported", "probeError": <error>  // only for a skipped target
}
```

Keep from `result` only: `analysisKey, processStatus, impactKnown,
error` and `report.(status, total, truncated,
impactedAssets[].(assetKey, name, type,
deployedRevisions[].(environmentKey, revision, severity, consumerType)))`.
When the harness saved the result to disk (Claude Code, large reports),
`cp` that file to `<cache-folder>/impact/raw/<targetKey>.status.json` and write a
record with `resultFile` instead of re-typing the rows. When a large
result arrived inline instead (a report with many dependents can stay
under the auto-save threshold), write the response verbatim with your
file-write tool to `<cache-folder>/impact/raw/<targetKey>.status.json` and point
the record at it with `resultFile` the same way. Never go looking for a
result in the harness's own session transcripts or logs. When a harness
cut the result, keep `processStatus`, `impactKnown`, `report.status`,
`report.total` and `report.truncated` from the visible tail, the rows
that arrived intact, and set `harnessTruncated: true`.

**Resume (Branch D).** Before launching, skip targets whose record exists and is
under 24h old. "rescan failures" re-runs the targets whose record has no
verdict.

### Step 6 — Build

`<output-file>` is `dependency-impact.html` in the user's working folder (absolute path)
unless they asked for another one:

```bash
python3 "<skill-folder>/scripts/build.py" "<cache-folder>" "<output-file>" \
  --impact-dir    "<cache-folder>/impact"            \
  --tenant-assets "<cache-folder>/tenant-assets-1.json" \
  --env-list      "<cache-folder>/env-list.json"     \
  --tenant-id     "<TENANT_ID>" \
  --targets       "<cache-folder>/targets.json"
# Branch D: --targets limits the page to this run's targets (older records stay cached).
# Branch C: --impact-dir "<cache-folder>/impact-named" and no --targets (that folder
#           holds only this question's records)
# Several searches (Branch C) or a paged asset list: repeat --tenant-assets once per file,
# each listing's pages one after another, in offset order.
# Reused tenant-architecture bundle: --tenant-assets "<tenant-cache-folder>/tenant-data.json"
```

`build.py` produces:
- `<cache-folder>/impact-data.json` — the unified data bundle
- `<cache-folder>/meta.json` — timestamp + stats
- `<output-file>` — the final HTML

It never renders a target without a verdict as "no dependents".

### Step 7 — Cached re-render

```bash
python3 "<skill-folder>/scripts/build.py" "<cache-folder>" "<output-file>"
```

### Step 8 — Report (3–5 lines)

- Output file path
- Branch C: per target, "N dependents (`report.status`)", "showing 200
  of N" when capped, or "impact unknown: <reason>" / "analysis not
  available for this asset"
- Branch D: targets analysed, impact known / unknown / not available,
  the top targets by dependents; when the `targets:` line counts targets
  "with no saved record", say they were not analysed and offer to re-run
- Cache state — "analysed now" / "reused records (Xh old)"; the page is
  dated by the oldest record it shows, so say that age

## Data shape contract

`build.py` writes `<cache-folder>/impact-data.json`:

```js
{
  tenant: { id, scannedAt },          // the oldest record file's save time
  stats: {
    targetCount, knownCount,
    unknownCount,      // includes refusedCount
    refusedCount,      // launch refused / type skipped
    edgeCount,         // sum of report.total over known targets
    edgeCountIsLowerBound, // a known target's report had no visible total
    consumerCount,     // distinct consumer assets in the listed rows
    missingCount,      // targets.json keys with no record file: unknown, not dropped
  },
  byTarget: {
    "<assetKey>": {
      n, kind, currentRev,                 // from the tenant asset list
      state: "known" | "unknown" | "refused",
      summary,                             // the sentence the page shows
      analysisKey, processStatus, reportStatus,
      total, totalKnown, shown, truncated,   // totalKnown false: total = rows seen, a floor
      users: [{ k, n, t, sev, rank, indirect,
                envs: [{ e, en, r, s, c }] }]   // env key/name, revision, severity, consumerType
    }
  }
}
```

## Cache rules

- Location: the folder `build.py --cache-dir <TENANT_ID>` prints (one per
  tenant, under the shared `outsystems-skills` cache root).
- Per-target records: 24h (Branch D resume); Branch C always fresh.
- Force refresh: "refresh" / "rescan" / "fresh data".
- Cross-skill reuse: reads the `outsystems-tenant-architecture` bundle
  (`tenant-data.json`) as the asset list when it is under 24h old; never
  writes into that skill's folder.

## Token budget (estimate)

| Scenario | Mechanism | Total |
|---|---|---|
| One target | auth_status + env_list + app_list search + launch + 1–3 polls + build | ~3–5K + ~0.1–0.15K per dependent |
| Whole-tenant map, N targets | N × (launch + poll + record) + build | ~0.5K × N + ~0.1–0.15K per dependent |
| Cached re-render | build.py | ~1K |

Per-dependent cost is estimated from a recorded report (74 dependents in
about 37 KB). A report at the 200-row cap is roughly 25K tokens by the
same ratio.

## Harness notes

- **Claude Code**: large results (a big `app_list` page, a report with
  many dependents) are saved to disk by the harness ("Output has been
  saved to <path>"), so they never enter model context — `cp` them into
  the cache and point the record at the copy (`resultFile`).
- **Harnesses without auto-save** (Cursor, Kiro and others): results
  arrive inline; write each record as described in Step 5.
- **Harnesses that truncate large tool results** (for example Codex,
  which keeps the head and the tail with a "truncated output" marker and
  saves nothing): page `app_list` with `limit: 100`; for a cut impact
  report keep the tail fields and intact rows and set
  `harnessTruncated: true` (Step 5). Never write a cut-off JSON body to
  the cache.

## Troubleshooting

- **An MCP call fails with an authentication error** → the sign-in
  expired: ask the user to sign in to the OutSystems MCP server again,
  then retry once.
- **The OutSystems tools are missing** → the MCP server is not connected;
  ask the user to connect it (see the main OutSystems skill's setup).
- **`python3: command not found`** → ask the user to install Python 3.8
  or later; nothing else is needed.
- **`build.py` exits 3 with `INCOMPLETE: the asset list pages starting
  at <file> cover N of T`** → an `app_list` page was truncated and its
  later pages were not passed right after it. Fetch the page at the
  printed `offset` (same arguments), save it, and re-run passing each
  listing's pages one after another, in offset order.
- **A target reads "record file is not a JSON object" or "a status was
  saved without the launch record"** → that target's record was cut,
  edited, or written without its `deploy_impact` response. Launch and
  poll it again, and save `launch` and `result` together in its record.
- **Cached re-render exits 3 with `STALE`** → `impact-data.json` was
  written by an older version or edited: re-run fresh mode (Step 6).
- **A target reads "the saved status is for analysis …"** → its saved
  `deploy_impact_status` response belongs to another analysis or asset
  (polls paired with the wrong record). Poll that target's own
  `analysisKey` again and save the response in its record.
- **`build.py` exits 1 with `could not write the output file`** → the
  output path is not writable (no space left, no permission, or a folder
  of that name). Only the HTML failed: ask the user for another output
  path and re-run the same command with it.
- **`--tenant-assets must be a list, ...`** → the file passed is not an
  `app_list` page, a compact asset list or a tenant-architecture bundle;
  pass the saved `app_list` page(s) instead.

## Anti-patterns — do NOT do these

- **Don't read `impactKnown: false`, a `Failed` / `Unknown` status, a
  refused launch, or an absent `report` as "no dependents".**
- **Don't read the length of `report.impactedAssets` as the blast
  radius.** It is capped; `report.total` is the number.
- **Don't sweep `app_refs` over every consumer to answer a reverse
  question.** The deletion analysis answers it server-side, per target.
- **Don't run a whole-tenant map for a question about named targets.**
- **Never call a delete tool** (`extlib_delete` or any other). The
  deletion analysis deletes nothing; nothing in this skill should.
- **Don't chase dependencies of dependencies yourself.** The report's
  `consumerType` says how each consumer depends on the target.
- **Don't recover a tool result from the harness's session transcript,
  logs or caches.** Those files are the harness's internals, not an
  interface: use the saved-to path it printed, or write the response you
  received.
- **Don't read a harness-saved report or asset page into context.**
  `cp` it into the cache and pass the path; check its start with
  `python3 -c "print(open('<path>').read(1000))"` if you must.

## When NOT to use

- User wants the architecture of one app → use
  `outsystems-app-architecture` (it shows that app's deps via its own
  data, more focused).
- User wants to check ONE specific app's deps (forward) → call
  `app_refs` directly.
- User asks whether promoting an app to an environment is safe → run a
  deployment-impact analysis (`delete: false` with the target `env_key`),
  as the main OutSystems skill's "Run a deployment-impact analysis"
  workflow describes.
