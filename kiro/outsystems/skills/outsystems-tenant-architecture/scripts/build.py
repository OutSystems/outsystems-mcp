#!/usr/bin/env python3
"""
build.py — build the tenant-architecture HTML from MCP responses.

Pure stdlib Python. No external dependencies (no jq, no pip installs).

Usage:
    # Fresh build (transforms raw MCP responses + injects into template).
    # Every page is a saved MCP tool result (harness auto-save path or a file
    # written verbatim). Pass pages in the order they were fetched.
    python3 build.py <cache-dir> <output-path> \\
        --tenant-id <auth_status.tenant_id> \\
        [--tenant-hostname <auth_status.tenant_hostname>] \\
        --apps <app_list page> [<app_list page> ...] \\
        [--deployments <env_key>=<env_apps page> ...] \\
        [--deployments-skipped <env_key>=<reason> ...] \\
        [--health <env_key>=<app_health page> ...] \\
        [--health-skipped <env_key>=<reason> ...] \\
        [--ai-agents <context_agents page> ...] \\
        [--ai-connections <context_connections page> ...] \\
        [--ai-skipped <reason>]

    # Cached re-render (renders the bundle already on disk):
    python3 build.py <cache-dir> <output-path>

    `--deployments` and `--health` repeat once per page; a second page of the
    same environment is a second `<env_key>=<page>` after the first.

Inputs (read):
    <cache-dir>/envs-raw.json          (required in fresh mode; env_list response)
    --apps pages                       (required in fresh mode; app_list pages)
    --deployments pages                (optional; env_apps pages, per environment)
    --health pages                     (optional; app_health pages, per environment)
    --ai-agents / --ai-connections     (optional; tenant-wide context_agents /
                                        context_connections pages, owned_only: false)
    <cache-dir>/tenant-data.json       (read in cached mode)
    ../assets/template.html            (relative to this script)

Outputs (write):
    <cache-dir>/tenant-data.json       (THE BUNDLE — the only input the render
                                        step reads; shape below)
    <cache-dir>/meta.json              ({schema, total, count, fetched_at, overlays_fetched_at})
    <output-path>                      (final HTML; data embedded, libraries from CDN)

The bundle (tenant-data.json, schema 1) is the interface between fetching and
rendering: anything that can produce it (today the MCP pages above) can be
rendered by the same template. The render step validates it first: a missing
or mistyped field fails naming the field (exit 1), an older schema is STALE
(exit 3). Adding a field does not bump the schema; removing, renaming or
changing the meaning of one does.
    {schema: 1,
     tenant:      {id, realm, hostname, region, hosting, fetched_at},
     envs:        [{key, name, purpose, host}],
     assets:      [{k, n, t, r, d, x}],             key, name, type, latest revision, date, external
     deployments: null | {fetched_at, envs, listedTypes, assets, drift},
     health:      null | {fetched_at, since, to, hours, envs, assets} | {skipped},
     ai:          null | {status: "complete", fetched_at, agents: [...],
                          connections: [...], stats, unlisted}
                       | {status: "skipped", reason}}

Exit codes:
    0  built
    1  input could not be read or has an unexpected shape (BAD PAGE: a repeated
       page, a page without its envelope, a page that is not valid JSON or that
       carries a harness truncation marker)
    2  usage error
    3  INCOMPLETE — a page set is missing its next page. stderr prints one
       `INCOMPLETE:` line per page set (app_list, one environment's env_apps,
       one environment's app_health, context_agents, context_connections)
       naming the call and the offset to fetch;
       fetch them, save them, and re-run with every page passed. No cache file
       is written in this case, so a partial page can never be mistaken for the
       whole tenant. Also 3 with STALE in cached mode: the bundle on disk is
       an older schema (or the pre-bundle file layout); re-run fresh mode.

Pagination contract (app_list):
    The server caps `limit` at 500 and reports the page in an envelope:
    `{results: [...], total, displayed, truncated, next_offset, ...}`.
    `total` is the tenant-wide count and is what the freshness probe
    (`app_list limit: 1`) compares against, so meta.total stores the
    server's total, never the number of rows that happened to arrive.

Pagination contract (env_apps):
    Same envelope, one environment per call, at most 100 rows per response.
    Two server generations exist. Newer servers accept `offset` and set
    `next_offset` whenever more rows exist: a truncated last page with a
    numeric `next_offset` is INCOMPLETE (exit 3). Older servers take no
    offset and leave `next_offset` absent or null: a truncated page there
    cannot be continued, so the environment is kept as PARTIAL — rendered,
    labelled partial, and never counted as proof that an app is absent.

Pagination contract (app_health):
    `nextPageOffset` is 0 on the last page. A whole-stage query (`apps: ""`)
    whose single page proved itself complete carries no `noData`; one that
    did not carries `noData: {status: "undetermined", reason}`. Only a
    complete result set lets an app deployed in that environment with no row
    read as "no traffic in the window"; otherwise it is "no reading".
    `appScore` is not carried into the HTML at all: it is a latency score
    (a zero-traffic app scores 100), not a health verdict.

Environment rows (env_list):
    The environment domain is `builtinDomain` (older payloads used
    `hostname`; both are accepted).

Design rationale:
    The whole point of this skill is to keep large asset data off the
    model's tokens. By doing transform + inject in one Python pass on
    disk, the data flows MCP → harness disk → this script → output HTML,
    never re-entering the model's output. That is also why this script,
    not the model, reads the pagination envelopes.
"""

from __future__ import annotations

import argparse
import datetime
import json
import pathlib
import re
import sys
import time


BUNDLE_NAME = "tenant-data.json"
BUNDLE_SCHEMA = 1
# Pre-bundle cache files (1.6 and early 1.7); removed on the next fresh build.
LEGACY_CACHE_FILES = ("assets.json", "envs.json", "tenant.json", "deployments.json", "health.json")

# (template placeholder, bundle key). Each bundle part lands in its own
# `const` in the template; the optional parts render as "not fetched" when null.
PLACEHOLDERS = [
    ("/*__ASSETS__*/null",      "assets"),
    ("/*__ENVS__*/null",        "envs"),
    ("/*__TENANT__*/null",      "tenant"),
    ("/*__DEPLOYMENTS__*/null", "deployments"),
    ("/*__HEALTH__*/null",      "health"),
    ("/*__AI__*/null",          "ai"),
]

# AI governance (context_agents / context_connections, tenant-wide).
# context_agents searches assetType AIAgent only (recorded tenant, 2026-09-29:
# never AgentDefinition); context_connections only AIModelConnection (never
# MCP / search-service / A2A / AI-native connections). Other AI-ish asset types are shown
# as "not reported by the governance source", not hidden.
AI_NOT_REPORTED = "not reported"
AI_COVERED_TYPES = {"Agent", "AIModelConnection"}
AI_STALE_DAYS = 180
AI_TEST_DEMO = re.compile(
    r"(?:^|[\s_-])(test|tmp|temp|demo|untitled|xxx|123|sample|scratch|wip)(?:$|[\s_-])",
    re.IGNORECASE)
AI_PROVIDER_LABELS = {
    "amazonbedrock": "Amazon Bedrock", "azureopenai": "Azure OpenAI", "openai": "OpenAI",
    "anthropic": "Anthropic", "gemini": "Gemini", "googlevertex": "Google Vertex AI",
    "customconnection": "Custom connection",
}

APP_LIST_MAX_LIMIT = 500  # server-side cap; larger values are clamped

# Asset type → category hub. Mirrors `TYPES` in assets/template.html (a test
# keeps the two in step). Types outside this map render grey under "Other".
ASSET_TYPE_HUBS = {
    "WebApplication":          "Applications",
    "MobileApplication":       "Applications",
    "Workflow":                "Applications",
    "Agent":                   "AI",
    "AgentDefinition":         "AI",
    "AIModelConnection":       "AI",
    "KnowledgeBase":           "AI",
    "AINativeConnection":      "AI",
    "LowCodeLibrary":          "Libraries",
    "ExtensionLibrary":        "Libraries",
    "MobileLibrary":           "Libraries",
    "ExternalLibrary":         "Libraries",
    "WidgetLibrary":           "Libraries",
    "ExternalConnection":      "Integrations",
    "MCPConnection":           "Integrations",
    "SearchServiceConnection": "Integrations",
    "A2AConnection":           "Integrations",
}
HUB_ORDER = ["Applications", "AI", "Libraries", "Integrations", "Other"]

# Asset types observed in real env_apps rows (recorded tenant,
# 2026-09-03). Only these can be called "not deployed anywhere": libraries
# never get a deployment record (they ship inside their consumers), env_apps
# drops Workflow rows server-side, and connection / knowledge-base types have
# never been seen in the listing. Any other type that does show up in a
# deployment row this build is added at build time.
DEPLOYMENT_LISTED_TYPES = {"WebApplication", "MobileApplication", "Agent", "AgentDefinition"}

# Higher rank = further along the pipeline. Drift is measured against the
# highest-ranked environment an asset is deployed in.
PURPOSE_RANK = {"Production": 3, "NonProduction": 2, "Development": 1}

# The metrics the HTML shows per app. `appScore` is left out on purpose.
HEALTH_FIELDS = ["requests", "errors", "errorPercent", "responseTimeP95",
                 "uniqueUsers", "lastErrorOccurred"]

# Codex truncates MCP tool results above its output budget (~10K tokens)
# head+tail: the text STARTS with a "Warning: truncated output (original
# token count: N)" header and carries a "…N tokens truncated…" marker (older
# byte-based policy: "…N chars truncated…") in the middle, which makes the
# JSON invalid. Only the header position and the parse failure are tested:
# the marker words alone can legitimately occur inside an asset name.
TRUNCATION_HEADER = "Warning: truncated output"
TRUNCATION_MID_MARKER = re.compile(r"\d+ (?:tokens|chars) truncated")


class IncompletePages(Exception):
    """The pages passed do not cover the tenant.

    `next_offset` is set when the last page says `truncated: true` (fetch the
    next page); it is None when the row count is short of the server total
    although the last page is not truncated (a page is missing or the pages
    were passed out of order).
    """

    def __init__(self, received: int, total: int, next_offset: int | None,
                 page_size: int = APP_LIST_MAX_LIMIT) -> None:
        super().__init__(f"received {received} of {total}, next offset {next_offset}")
        self.received = received
        self.total = total
        self.next_offset = next_offset
        self.page_size = page_size


class IncompleteOverlay(Exception):
    """An env_apps or app_health page set that has a further page to fetch.
    The message is the full INCOMPLETE line."""


class Incomplete(Exception):
    """Every INCOMPLETE line of one build, so the agent can fetch all the
    missing pages in one parallel round."""

    def __init__(self, lines: list[str]) -> None:
        super().__init__("; ".join(lines))
        self.lines = lines


class BadPage(Exception):
    """A page that cannot be trusted: a repeat of an earlier page, a page
    saved without its envelope, or a page that is not the JSON the tool
    returned (truncated by the harness, or not JSON at all)."""


class UsageError(Exception):
    """Arguments that do not describe a build (exit 2)."""


class BadBundle(Exception):
    """A bundle the render step cannot use: a missing or mistyped field
    (exit 1). The message names the field."""


class StaleBundle(Exception):
    """A bundle (or cache layout) older than this build.py renders (exit 3)."""



# Every skill in this family caches under one root, the "outsystems-skills"
# folder of the user's cache directory, in a folder per skill and per tenant
# (or app). `build.py --cache-dir <id>` creates and prints that folder, so the
# skill docs never spell out a home-folder path; `--skill <name>` prints a
# sibling skill's folder (for reading its cache, never for writing it).
CACHE_ROOT = pathlib.Path.home() / ".cache" / "outsystems-skills"
SKILL_NAME = "outsystems-tenant-architecture"
_CACHE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9-]{0,127}$")
_SKILL_ID = re.compile(r"^outsystems-[a-z-]+$")


def _cache_dir_command(argv) -> int:
    """`--cache-dir <id> [--skill <name>]`: create and print the folder."""
    skill = SKILL_NAME
    rest = list(argv)
    if len(rest) == 3 and rest[1] == "--skill":
        skill = rest.pop(2)
        rest.pop(1)
    if len(rest) != 1 or not _CACHE_ID.match(rest[0]) or not _SKILL_ID.match(skill):
        print("usage: build.py --cache-dir <tenant-or-app-key> [--skill outsystems-<name>]",
              file=sys.stderr)
        return 2
    path = CACHE_ROOT / skill / rest[0]
    if skill == SKILL_NAME:
        path.mkdir(parents=True, exist_ok=True)
    print(path)
    return 0


def main(argv: list[str]) -> int:
    if len(argv) > 1 and argv[1] == "--cache-dir":
        return _cache_dir_command(argv[2:])
    try:
        args = _parse_args(argv[1:])
    except UsageError as exc:
        print(f"usage: {exc}", file=sys.stderr)
        return 2

    cache_dir = pathlib.Path(args.cache_dir).resolve()
    out_path  = pathlib.Path(args.output_path).resolve()

    # Skill root is parent of scripts/
    skill_dir = pathlib.Path(__file__).resolve().parent.parent
    template_path = skill_dir / "assets" / "template.html"

    cache_dir.mkdir(parents=True, exist_ok=True)

    # ---- Fresh mode: build cache files from raw MCP responses ----
    if args.apps:
        try:
            _build_cache(cache_dir, args)
        except UsageError as exc:
            print(f"usage: {exc}", file=sys.stderr)
            return 2
        except Incomplete as inc:
            for line in inc.lines:
                print(f"INCOMPLETE: {line}", file=sys.stderr)
            print("Nothing was written to the cache.", file=sys.stderr)
            return 3
        except BadPage as bad:
            print(f"BAD PAGE: {bad}. Nothing was written to the cache.", file=sys.stderr)
            return 1
        except BadBundle as bad:
            print(f"BAD BUNDLE: {bad}. Nothing was written to the cache.", file=sys.stderr)
            return 1
        except (FileNotFoundError, KeyError, TypeError, json.JSONDecodeError) as exc:
            print(f"cache build failed: {exc!r}", file=sys.stderr)
            return 1

    # ---- Render (both modes): the bundle is the only input ----
    if not template_path.exists():
        print(f"template not found: {template_path}", file=sys.stderr)
        return 1
    try:
        bundle = _load_bundle(cache_dir)
    except StaleBundle as exc:
        print(f"STALE: {exc}. Re-run fresh mode with the Step 3 responses.", file=sys.stderr)
        return 3
    except BadBundle as exc:
        print(f"BAD BUNDLE: {exc}", file=sys.stderr)
        return 1

    html = template_path.read_text(encoding="utf-8")
    payloads: dict[str, str] = {}
    for placeholder, key in PLACEHOLDERS:
        if html.count(placeholder) != 1:
            print(f"placeholder {placeholder!r} must occur exactly once in the template",
                  file=sys.stderr)
            return 1
        # `<` only occurs inside JSON strings, where the escape \u003c is the
        # same character; escaping every `<` stops an asset named
        # "</script>" from closing the inline script and "<!--<script" from
        # putting the HTML parser into its double-escaped script state.
        payloads[placeholder] = json.dumps(bundle.get(key), separators=(",", ":")).replace("<", "\\u003c")

    # One pass over the template for every placeholder: injected data is
    # never scanned again, so an asset named "/*__DEPLOYMENTS__*/null"
    # stays a name instead of receiving the next part's JSON.
    pattern = re.compile("|".join(re.escape(p) for p in payloads))
    html = pattern.sub(lambda m: payloads[m.group(0)], html)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html, encoding="utf-8")

    size_kb = out_path.stat().st_size / 1024
    print(f"wrote {out_path} ({size_kb:.1f} KB; {len(bundle['assets'])} assets)")
    for line in _summary(bundle):
        print(line)
    return 0


# ---------------------------------------------------------------------------
# Arguments
# ---------------------------------------------------------------------------

class _Parser(argparse.ArgumentParser):
    def error(self, message: str) -> None:  # argparse would sys.exit(2)
        raise UsageError(message)


def _parse_args(argv: list[str]) -> argparse.Namespace:
    p = _Parser(prog="build.py", add_help=False)
    p.add_argument("cache_dir")
    p.add_argument("output_path")
    p.add_argument("--tenant-id")
    p.add_argument("--tenant-hostname")
    p.add_argument("--apps", nargs="+", action="append", default=[])
    p.add_argument("--deployments", nargs="+", action="append", default=[])
    p.add_argument("--deployments-skipped", nargs="+", action="append", default=[])
    p.add_argument("--health", nargs="+", action="append", default=[])
    p.add_argument("--health-skipped", nargs="+", action="append", default=[])
    p.add_argument("--ai-agents", nargs="+", action="append", default=[])
    p.add_argument("--ai-connections", nargs="+", action="append", default=[])
    p.add_argument("--ai-skipped", nargs="+", action="append", default=[])
    args, extra = p.parse_known_args(argv)
    if extra:
        raise UsageError(
            f"unexpected arguments {extra!r}. build.py 1.7 takes flags: "
            f"<cache-dir> <output-path> --tenant-id <id> --apps <page>... "
            f"[--deployments <env_key>=<page>...] [--health <env_key>=<page>...]")
    # Flatten the append-of-lists (`action="extend"` is 3.8+).
    for name in ("apps", "deployments", "deployments_skipped", "health", "health_skipped",
                 "ai_agents", "ai_connections", "ai_skipped"):
        setattr(args, name, [v for group in getattr(args, name) for v in group])
    args.ai_skipped = " ".join(args.ai_skipped).strip() or None
    if args.ai_skipped and (args.ai_agents or args.ai_connections):
        raise UsageError("--ai-skipped cannot be combined with --ai-agents / --ai-connections")
    if bool(args.ai_agents) != bool(args.ai_connections):
        raise UsageError("the AI governance view needs both --ai-agents and --ai-connections pages "
                         "(or --ai-skipped <reason> when the calls failed)")

    overlays = (args.deployments or args.deployments_skipped or args.health or args.health_skipped
                or args.ai_agents or args.ai_connections or args.ai_skipped)
    if not args.apps:
        if args.tenant_id or args.tenant_hostname or overlays:
            raise UsageError("a fresh build needs --apps <app_list page>... "
                             "(cached mode takes only <cache-dir> <output-path>)")
        return args
    if not args.tenant_id:
        raise UsageError("--tenant-id is required with --apps (auth_status.tenant_id)")
    if pathlib.Path(args.tenant_id).exists() or args.tenant_id.endswith(".json"):
        raise UsageError(f"--tenant-id must be the tenant id, not a page file ({args.tenant_id!r})")
    for name in ("deployments", "deployments_skipped", "health", "health_skipped"):
        pairs = []
        for item in getattr(args, name):
            key, sep, value = item.partition("=")
            if not sep or not key or not value:
                raise UsageError(f"--{name.replace('_', '-')} takes <env_key>=<value>, got {item!r}")
            pairs.append((key.strip().lower(), value))
        setattr(args, name, pairs)
    return args


# ---------------------------------------------------------------------------
# Page readers
# ---------------------------------------------------------------------------

def _read_page(path: pathlib.Path, what: str) -> dict:
    """Load one saved tool result. Refuses harness-truncated or non-JSON files
    (BadPage) and unwraps an MCP result envelope if one was saved whole."""
    text = path.read_text(encoding="utf-8")
    if text.lstrip().startswith(TRUNCATION_HEADER):
        raise BadPage(
            f"{path} ({what}) starts with the harness truncation header "
            f"('{TRUNCATION_HEADER} ...'): the harness (Codex) cut rows out of the "
            f"middle of the tool result. Re-fetch that page with a smaller `limit` "
            f"(50) and page with the offset instead")
    try:
        page = json.loads(text)
    except json.JSONDecodeError as exc:
        seen = TRUNCATION_MID_MARKER.search(text)
        hint = (f" It carries the harness truncation marker '…{seen.group(0)}…': the "
                f"harness (Codex) cut rows out of the middle; re-fetch with a smaller "
                f"`limit` (50) and page with the offset" if seen else
                " Save the tool result verbatim; if it arrived cut short, re-fetch "
                "with a smaller `limit`")
        raise BadPage(f"{path} ({what}) is not valid JSON ({exc.msg}, line "
                      f"{exc.lineno}).{hint}") from None
    return _unwrap_tool_result(page)


def _unwrap_tool_result(page):
    """Accept a raw payload, an MCP `{structuredContent}` / `{content: [...]}`
    result, or a bare content-block list. Anything else is returned as-is."""
    if isinstance(page, dict) and "results" not in page:
        if isinstance(page.get("structuredContent"), dict):
            return page["structuredContent"]
        if isinstance(page.get("content"), list):
            page = page["content"]
    if isinstance(page, list) and page and all(isinstance(b, dict) for b in page):
        texts = [b.get("text") for b in page if b.get("type") == "text"]
        if len(texts) == 1 and isinstance(texts[0], str):
            try:
                return json.loads(texts[0])
            except json.JSONDecodeError:
                pass
    return page


def _env_host(env: dict) -> str:
    """Environment domain: `builtinDomain` today, `hostname` on older payloads."""
    return (env.get("builtinDomain")
            or env.get("defaultDomain")
            or env.get("hostname")
            or "")


def _is_int(v) -> bool:
    return isinstance(v, int) and not isinstance(v, bool)


# ---------------------------------------------------------------------------
# app_list
# ---------------------------------------------------------------------------

APP_LIST_SMALL_LIMIT = 50   # the page size SKILL.md gives for harnesses that truncate results


def _merge_pages(pages: list[dict]) -> tuple[list[dict], int]:
    """Concatenate app_list pages, de-duplicated by assetKey, in order.

    Returns (rows, total) where `total` is the server-reported tenant-wide
    count (the same figure the `limit: 1` freshness probe returns). Raises
    IncompletePages when the last page reports `truncated: true`.
    """
    rows: list[dict] = []
    seen: set[str] = set()
    total: int | None = None
    for i, page in enumerate(pages, 1):
        if not isinstance(page, dict) or not isinstance(page.get("results"), list):
            raise KeyError("results")
        if "truncated" not in page:
            # The envelope is what tells us whether this page is the whole
            # tenant; a saved page must keep it. A page as long as either page
            # size the skill uses (500, or 50 on a truncating harness) without
            # it is almost certainly a clamped page that was re-shaped.
            if len(page["results"]) >= APP_LIST_SMALL_LIMIT:
                raise BadPage(
                    f"page {i} has {len(page['results'])} rows but no envelope "
                    f"(truncated/total/next_offset missing); save the app_list "
                    f"response verbatim and re-run")
            print(f"warning: page {i} has no `truncated` field; assuming it is complete",
                  file=sys.stderr)
        added = 0
        for a in page["results"]:
            key = a["assetKey"]
            if key in seen:
                continue
            seen.add(key)
            rows.append(a)
            added += 1
        if i > 1 and added == 0 and page["results"]:
            raise BadPage(
                f"page {i} added no new assets: it repeats an earlier page. Was "
                f"offset passed to app_list?")
        if _is_int(page.get("total")):
            total = page["total"]  # the latest page's figure is the freshest
    last = pages[-1]
    page_size = len(pages[0]["results"]) or APP_LIST_MAX_LIMIT
    if total is not None and len(rows) >= total:
        return rows, total  # every asset present, whatever the page order
    if last.get("truncated") is True:
        next_offset = last.get("next_offset")
        if not _is_int(next_offset):
            next_offset = len(rows)
        raise IncompletePages(len(rows), total if total is not None else -1,
                              next_offset, page_size)
    if total is not None and len(rows) < total:
        raise IncompletePages(len(rows), total, None, page_size)
    return rows, (total if total is not None else len(rows))


def _app_list_incomplete_line(inc: IncompletePages) -> str:
    if inc.next_offset is not None:
        return (f"app_list returned {inc.received} of {inc.total} assets (the last page "
                f"is truncated). Call app_list with limit: {inc.page_size}, offset: "
                f"{inc.next_offset}, save the response, and re-run build.py passing every "
                f"app_list page to --apps in order.")
    return (f"the app_list pages passed cover {inc.received} of {inc.total} assets but "
            f"the last page is not truncated. Either a page from offset 0 upward was not "
            f"passed, or the tenant changed between page fetches (a later page overlapped "
            f"or skipped rows). If every saved page is already passed in order, discard "
            f"them and re-fetch ALL pages from offset 0 with the same limit, then re-run.")


# ---------------------------------------------------------------------------
# env_apps (deployments overlay)
# ---------------------------------------------------------------------------

def _merge_deployments(env: dict, pages: list[dict]) -> tuple[list[dict], dict]:
    """Merge one environment's env_apps pages.

    Returns (rows, status) where status is {"status": "complete" | "partial",
    "shown", "total"[, "reason"]}. Raises IncompleteOverlay when a newer server
    says there is a next page, BadPage on a repeated or shapeless page.
    """
    label = f"{env['name']} ({env['key']})"
    rows: list[dict] = []
    seen: set[tuple[str, str]] = set()
    total: int | None = None
    cut_short = False
    for i, page in enumerate(pages, 1):
        if not isinstance(page, dict) or not isinstance(page.get("results"), list):
            raise BadPage(f"env_apps page {i} for {label} has no `results` list; save the "
                          f"env_apps response verbatim")
        if "truncated" not in page:
            raise BadPage(f"env_apps page {i} for {label} has no envelope "
                          f"(truncated/total missing); save the env_apps response verbatim")
        added = 0
        for r in page["results"]:
            ident = (str(r["applicationKey"]).lower(), r.get("deploymentKey") or "")
            if ident in seen:
                continue
            seen.add(ident)
            rows.append(r)
            added += 1
        if i > 1 and added == 0 and page["results"]:
            raise BadPage(f"env_apps page {i} for {label} added no new deployments: it "
                          f"repeats an earlier page. Was offset passed to env_apps?")
        if _is_int(page.get("total")):
            total = page["total"]
        # Truncated with no cursor: an older server (no offset input) or a
        # listing cut short upstream. Either way the rest cannot be fetched.
        if page.get("truncated") is True and not _is_int(page.get("next_offset")):
            cut_short = True
    if total is None:
        total = len(rows)
    last = pages[-1]
    if cut_short:
        return rows, {
            "status": "partial", "shown": len(rows), "total": total,
            "reason": (f"env_apps listed {len(rows)} of {total} deployments and offered no "
                       f"next page (this server takes no offset, or the listing was cut "
                       f"short upstream); the rest could not be fetched"),
        }
    # A last page that says more rows exist wins over a count that looks
    # whole (a page without `total` falls back to the rows seen so far).
    if len(rows) >= total and not (last.get("truncated") is True and _is_int(last.get("next_offset"))):
        return rows, {"status": "complete", "shown": len(rows), "total": total}
    if last.get("truncated") is True:
        raise IncompleteOverlay(
            f"env_apps for environment {label} returned {len(rows)} of {total} deployments "
            f"and has a next page. Call env_apps with env_key: {env['key']}, offset: "
            f"{last['next_offset']}, save the response, and re-run build.py adding "
            f"--deployments {env['key']}=<that file> after this environment's earlier pages.")
    raise IncompleteOverlay(
        f"the env_apps pages passed for environment {label} cover {len(rows)} of {total} "
        f"deployments but the last page is not truncated: a page is missing or out of "
        f"order. Pass every page from the first (no offset) upward, in order.")


def _deployments(envs_raw: list[dict], assets: list[dict], args) -> tuple[dict, list[str], list[pathlib.Path]]:
    """Build deployments.json. Returns (data, incomplete lines, page paths)."""
    env_by_key = {e["key"].lower(): e for e in envs_raw}
    pages_by_env: dict[str, list[pathlib.Path]] = {}
    for key, path in args.deployments:
        if key not in env_by_key:
            raise UsageError(f"--deployments names env key {key!r}, which is not in envs-raw.json")
        pages_by_env.setdefault(key, []).append(pathlib.Path(path).resolve())
    skipped = {}
    for key, reason in args.deployments_skipped:
        if key not in env_by_key:
            raise UsageError(f"--deployments-skipped names env key {key!r}, which is not in envs-raw.json")
        skipped[key] = reason

    by_key = {a["k"].lower(): a for a in assets}
    latest = {a["k"]: a["r"] for a in assets}
    listed_types = set(DEPLOYMENT_LISTED_TYPES)
    env_status: dict[str, dict] = {}
    per_asset: dict[str, dict[str, dict]] = {}
    incomplete: list[str] = []
    all_paths: list[pathlib.Path] = []

    for e in envs_raw:
        key = e["key"]
        paths = pages_by_env.get(key.lower())
        if not paths:
            env_status[key] = {"status": "skipped",
                               "reason": skipped.get(key.lower(), "not fetched")}
            continue
        all_paths.extend(paths)
        pages = [_read_page(p, f"env_apps {e['name']}") for p in paths]
        try:
            rows, status = _merge_deployments(e, pages)
        except IncompleteOverlay as inc:
            incomplete.append(str(inc))
            continue
        unmatched = 0
        for r in rows:
            asset = by_key.get(str(r["applicationKey"]).lower())
            if asset is None:
                unmatched += 1  # deployed, but not in the app_list pages passed
                continue
            entry = {
                "env": key,
                "rev": r.get("revision"),
                "date": (r.get("deploymentDateTime") or "")[:10],
                "url": r.get("url") or "",
            }
            prev = per_asset.setdefault(asset["k"], {}).get(key)
            if prev is None or entry["date"] > prev["date"]:
                per_asset[asset["k"]][key] = entry
            listed_types.add(asset["t"])
        status["unmatched"] = unmatched
        env_status[key] = status

    rank = {e["key"]: (PURPOSE_RANK.get(e.get("purpose", ""), 0), e.get("order", 0))
            for e in envs_raw}
    assets_out: dict[str, list[dict]] = {}
    drift: dict[str, dict] = {}
    for k, by_env in per_asset.items():
        entries = sorted(by_env.values(), key=lambda d: rank.get(d["env"], (0, 0)))
        assets_out[k] = entries
        top = entries[-1]
        if _is_int(top["rev"]) and _is_int(latest.get(k)) and latest[k] > top["rev"]:
            drift[k] = {"env": top["env"], "deployed": top["rev"], "latest": latest[k]}

    data = {
        "fetched_at": _oldest_mtime(all_paths),
        "envs": env_status,
        "listedTypes": sorted(listed_types),
        "assets": assets_out,
        "drift": drift,
    }
    return data, incomplete, all_paths


# ---------------------------------------------------------------------------
# app_health (health overlay)
# ---------------------------------------------------------------------------

def _merge_health(env: dict, pages: list[dict]) -> tuple[list[dict], dict]:
    """Merge one environment's app_health pages (whole-stage, `apps: ""`).

    Returns (rows, status) where status is {"status": "complete" | "partial",
    "metrics", "since", "to", "rows", "keyless", "unresolved"[, "reason",
    "advisory"]}. Raises IncompleteOverlay while `nextPageOffset` > 0 on the
    last page, BadPage on a shapeless, foreign or repeated page.
    """
    label = f"{env['name']} ({env['key']})"
    rows: list[dict] = []
    seen: set[str] = set()
    keyless = 0
    for i, page in enumerate(pages, 1):
        if (not isinstance(page, dict) or not isinstance(page.get("results"), list)
                or not _is_int(page.get("nextPageOffset"))):
            raise BadPage(f"app_health page {i} for {label} is not an app_health response "
                          f"(`results` / `nextPageOffset` missing); save it verbatim")
        stage = page.get("stageKey")
        if isinstance(stage, str) and stage and stage.lower() != env["key"].lower():
            raise BadPage(f"app_health page {i} passed for {label} ran against environment "
                          f"{stage}; pass each page with the env_key it was fetched for")
        added = 0
        for r in page["results"]:
            key = (r.get("applicationKey") or "").lower()
            if not key:
                keyless += 1
                added += 1
                continue
            if key in seen:
                continue
            seen.add(key)
            rows.append(r)
            added += 1
        if i > 1 and added == 0 and page["results"]:
            raise BadPage(f"app_health page {i} for {label} added no new rows: it repeats an "
                          f"earlier page. Was offset passed to app_health?")
    first, last = pages[0], pages[-1]
    if last["nextPageOffset"] > 0:
        raise IncompleteOverlay(
            f"app_health for environment {label} has a further page. Call app_health with "
            f"the same arguments (env_key: {env['key']}, apps: \"\", hours: 168, same limit) "
            f"plus offset: {last['nextPageOffset']}, save the response, and re-run build.py "
            f"adding --health {env['key']}=<that file> after this environment's earlier pages.")
    status = {
        # The echo tells "unavailable" (requested, no reading) from "not
        # requested"; only the fields the HTML shows are kept.
        "metrics": [m for m in first.get("metrics") or [] if m in HEALTH_FIELDS],
        "since": first.get("since"),
        "to": first.get("to"),
        "rows": len(rows),
        "keyless": keyless,
        "unresolved": first.get("unresolved") or [],
    }
    if first.get("metricsAdvisory"):
        status["advisory"] = first["metricsAdvisory"]
    total = last.get("total") if _is_int(last.get("total")) else len(rows) + keyless
    no_data = last.get("noData") if len(pages) == 1 else None
    if len(pages) == 1 and isinstance(no_data, dict) and no_data.get("status") == "undetermined":
        status.update(status="partial", reason=str(no_data.get("reason") or "undetermined"))
    elif keyless:
        status.update(status="partial",
                      reason=f"{keyless} row(s) carried no application key and cannot be matched")
    elif len(rows) < total:
        status.update(status="partial",
                      reason=f"the pages passed carry {len(rows)} of {total} rows")
    elif len(pages) > 1 and not _is_int(last.get("total")):
        # Several pages add up only against the server's `total`; without it a
        # missing middle page would pass as complete.
        status.update(status="partial",
                      reason="the pages carry no total, so their completeness cannot be checked")
    else:
        # One page with no noData is the server's own proof. Several pages
        # that end on nextPageOffset 0 and add up to `total` are complete by
        # count (a page past offset 0 never proves itself server-side).
        status["status"] = "complete"
    return rows, status


def _classify(row: dict) -> str:
    """One app's reading in one environment. Never a health verdict: the
    classes are "had errors", "had traffic", "no traffic" and "no reading"."""
    errors, pct, req = row.get("errors"), row.get("errorPercent"), row.get("requests")
    if ((isinstance(errors, (int, float)) and errors > 0)
            or (isinstance(pct, (int, float)) and pct > 0)
            or row.get("lastErrorOccurred")):
        return "errors"
    if isinstance(req, (int, float)) and not isinstance(req, bool):
        return "traffic" if req > 0 else "noTraffic"
    return "noReading"  # `requests` absent: unavailable, not zero


# Asset-level class across environments; the first match wins.
_CLASS_PRIORITY = ["errors", "traffic", "noReading", "noTraffic"]


def _health(envs_raw: list[dict], assets: list[dict], deployments: dict | None,
            args) -> tuple[dict, list[str], list[pathlib.Path]]:
    """Build health.json. Returns (data, incomplete lines, page paths)."""
    env_by_key = {e["key"].lower(): e for e in envs_raw}
    pages_by_env: dict[str, list[pathlib.Path]] = {}
    for key, path in args.health:
        if key not in env_by_key:
            raise UsageError(f"--health names env key {key!r}, which is not in envs-raw.json")
        pages_by_env.setdefault(key, []).append(pathlib.Path(path).resolve())
    skipped = {}
    for key, reason in args.health_skipped:
        if key not in env_by_key:
            raise UsageError(f"--health-skipped names env key {key!r}, which is not in envs-raw.json")
        skipped[key] = reason

    # Production environments are the overlay's subject; any other env that
    # was passed explicitly is included too.
    subject = [e for e in envs_raw
               if e.get("purpose") == "Production" or e["key"].lower() in pages_by_env
               or e["key"].lower() in skipped]
    by_key = {a["k"].lower(): a for a in assets}
    env_status: dict[str, dict] = {}
    per_asset: dict[str, dict[str, dict]] = {}
    incomplete: list[str] = []
    all_paths: list[pathlib.Path] = []

    for e in subject:
        key = e["key"]
        paths = pages_by_env.get(key.lower())
        if not paths:
            env_status[key] = {"status": "skipped",
                               "reason": skipped.get(key.lower(), "not fetched")}
            continue
        all_paths.extend(paths)
        pages = [_read_page(p, f"app_health {e['name']}") for p in paths]
        try:
            rows, status = _merge_health(e, pages)
        except IncompleteOverlay as inc:
            incomplete.append(str(inc))
            continue
        unmatched = 0
        for r in rows:
            asset = by_key.get(r["applicationKey"].lower())
            if asset is None:
                unmatched += 1
                continue
            reading = {f: r[f] for f in HEALTH_FIELDS if f in r and r[f] is not None}
            reading["cls"] = _classify(reading)
            per_asset.setdefault(asset["k"], {})[key] = reading
        # An app deployed here with no row: no traffic in the window if the
        # result set is complete, otherwise nothing can be said.
        deployed_here = [k for k, entries in (deployments or {}).get("assets", {}).items()
                         if any(d["env"] == key for d in entries)]
        for k in deployed_here:
            if key not in per_asset.get(k, {}):
                per_asset.setdefault(k, {})[key] = {
                    "cls": "noTraffic" if status["status"] == "complete" else "noReading",
                    "absent": True,
                }
        status["unmatched"] = unmatched
        env_status[key] = status

    assets_out = {}
    for k, by_env in per_asset.items():
        classes = {r["cls"] for r in by_env.values()}
        overall = next(c for c in _CLASS_PRIORITY if c in classes)
        assets_out[k] = {"cls": overall, "by_env": by_env}

    first_ok = next((s for s in env_status.values() if s.get("since")), {})
    data = {
        "fetched_at": _oldest_mtime(all_paths),
        "since": first_ok.get("since"),
        "to": first_ok.get("to"),
        "hours": _window_hours(first_ok.get("since"), first_ok.get("to")),
        "envs": env_status,
        "assets": assets_out,
    }
    if not subject:
        data["skipped"] = "no Production-purpose environment in this tenant"
    return data, incomplete, all_paths


# datetime.fromisoformat before Python 3.11 rejects fractions that are not 3
# or 6 digits, and the server writes 5 to 7: parse by hand instead.
_ISO_TS = re.compile(r"^(\d{4})-(\d{2})-(\d{2})(?:[T ](\d{2}):(\d{2}):(\d{2})(?:\.(\d+))?)?(Z|[+-]\d{2}:?\d{2})?$")


def _parse_iso(value):
    """Aware UTC datetime for an ISO-8601 string; raises ValueError otherwise."""
    m = _ISO_TS.match(value.strip()) if isinstance(value, str) else None
    if not m:
        raise ValueError(f"not an ISO-8601 timestamp: {value!r}")
    y, mo, d, h, mi, sec, frac, tz = m.groups()
    us = int((frac or "0")[:6].ljust(6, "0"))
    dt = datetime.datetime(int(y), int(mo), int(d), int(h or 0), int(mi or 0), int(sec or 0), us,
                           tzinfo=datetime.timezone.utc)
    if tz and tz != "Z":
        digits = tz[1:].replace(":", "")
        offset = datetime.timedelta(hours=int(digits[:2]), minutes=int(digits[2:]))
        dt = dt - offset if tz[0] == "+" else dt + offset
    return dt


def _window_hours(since: str | None, to: str | None) -> int | None:
    parse = _parse_iso
    try:
        return round((parse(to) - parse(since)).total_seconds() / 3600)
    except (TypeError, ValueError, AttributeError):
        return None


def _oldest_mtime(paths: list[pathlib.Path]) -> int | None:
    """When the overlay data was fetched: the oldest page's save time."""
    if not paths:
        return None
    return int(min(p.stat().st_mtime for p in paths))


# ---------------------------------------------------------------------------
# Cache build
# ---------------------------------------------------------------------------

def _build_cache(cache_dir: pathlib.Path, args) -> None:
    """Transform raw MCP responses into the compact cache files."""

    incomplete: list[str] = []

    # ----- assets.json (compact list with single-letter keys) -----
    page_paths = [pathlib.Path(p).resolve() for p in args.apps]
    pages = [_read_page(p, "app_list") for p in page_paths]
    rows: list[dict] = []
    total = 0
    try:
        rows, total = _merge_pages(pages)
    except IncompletePages as inc:
        incomplete.append(_app_list_incomplete_line(inc))
    assets = [
        {
            "k": a["assetKey"],
            "n": a["name"],
            "t": a.get("assetType") or "",
            "r": a.get("revision"),
            "d": (a.get("revisionDateTime") or "")[:10],
            "x": bool(a.get("isExternal", False)),
        }
        for a in rows
    ]

    # ----- envs.json (compact) + side-data for tenant.json -----
    envs_raw_path = cache_dir / "envs-raw.json"
    if not envs_raw_path.exists():
        raise FileNotFoundError(envs_raw_path)
    envs_page = _read_page(envs_raw_path, "env_list")
    envs_raw = envs_page["results"]
    envs = [
        {
            "key": e["key"],
            "name": e["name"],
            "purpose": e.get("purpose", ""),
            "host": _env_host(e),
        }
        for e in envs_raw
    ]

    # ----- overlays (deployments first: health reads it) -----
    deployments = None
    overlay_paths: list[pathlib.Path] = []
    if args.deployments or args.deployments_skipped:
        deployments, inc, paths = _deployments(envs_raw, assets, args)
        incomplete += inc
        overlay_paths += paths
    # With no Production environment there is nothing to fetch; health.json
    # still records why, so the HTML and the report can say so.
    has_prod = any(e.get("purpose") == "Production" for e in envs_raw)
    health = None
    if args.health or args.health_skipped or not has_prod:
        health, inc, paths = _health(envs_raw, assets, deployments, args)
        incomplete += inc
        overlay_paths += paths

    ai = None
    if args.ai_skipped:
        ai = {"status": "skipped", "reason": args.ai_skipped}
    elif args.ai_agents:
        ai, inc, paths = _ai(assets, args)
        incomplete += inc
        overlay_paths += paths

    if incomplete:
        raise Incomplete(incomplete)

    # ----- tenant.json (realm from auth_status.tenant_hostname, else envs) -----
    now = int(time.time())
    region = "us-east-1"
    realm  = args.tenant_id[:8]
    hosting = "oscloud"
    if envs_raw:
        first = envs_raw[0]
        region = first.get("region", region)
        hosting = first.get("hosting", hosting)
        host = _env_host(first)
        if host:
            realm = re.sub(r"-(?:dev|test)$", "", host.split(".")[0])
    if args.tenant_hostname:
        realm = args.tenant_hostname.split(".")[0]
    tenant = {
        "id": args.tenant_id,
        "realm": realm,
        "hostname": args.tenant_hostname or "",
        "region": region,
        "hosting": hosting,
        "fetched_at": now,
    }

    # ----- meta.json (cache fingerprint) -----
    # `total` is the server-reported tenant-wide count so that Step 2's
    # `probe.total == meta.total` compares like with like; `count` is how
    # many rows are actually rendered (equal when every page was passed).
    # `overlays_fetched_at` is null when no overlay was requested, which
    # Step 2 treats as a stale cache (deployments/health change without the
    # asset total changing).
    overlays_at = None
    if deployments is not None or health is not None or (ai and ai.get("status") == "complete"):
        overlays_at = _oldest_mtime(overlay_paths) or now
    if ai and ai.get("status") == "complete":
        ai["fetched_at"] = overlays_at
    meta = {"schema": BUNDLE_SCHEMA, "total": total, "count": len(assets), "fetched_at": now,
            "overlays_fetched_at": overlays_at}
    bundle = {"schema": BUNDLE_SCHEMA, "tenant": tenant, "envs": envs, "assets": assets,
              "deployments": deployments, "health": health, "ai": ai}
    _validate_bundle(bundle)      # the producer is held to the same contract as the renderer

    # Write only after every input parsed, so a failure leaves any previous
    # complete cache untouched.
    def write(name, obj):
        (cache_dir / name).write_text(json.dumps(obj, separators=(",", ":")), encoding="utf-8")

    write(BUNDLE_NAME, bundle)
    write("meta.json", meta)
    for name in LEGACY_CACHE_FILES:
        if (cache_dir / name).exists():
            (cache_dir / name).unlink()


# ---------------------------------------------------------------------------
# The bundle: load + validate (the render step's only input)
# ---------------------------------------------------------------------------

def _load_bundle(cache_dir: pathlib.Path) -> dict:
    path = cache_dir / BUNDLE_NAME
    if not path.exists():
        if any((cache_dir / n).exists() for n in LEGACY_CACHE_FILES):
            raise StaleBundle(f"{cache_dir} holds the pre-bundle cache layout (1.6 / early 1.7)")
        raise BadBundle(f"missing {path}: run fresh mode first")
    try:
        bundle = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise BadBundle(f"{path} is not valid JSON: {exc}") from None
    _validate_bundle(bundle)
    return bundle


def _validate_bundle(b) -> None:
    """Raise StaleBundle for an older schema, BadBundle naming the first
    missing or mistyped field. Only what the template reads is checked;
    unknown extra fields are allowed (additive changes keep the schema)."""
    if not isinstance(b, dict):
        raise BadBundle("the bundle is not a JSON object")
    schema = b.get("schema")
    if not _is_int(schema) or schema < BUNDLE_SCHEMA:
        raise StaleBundle(f"bundle schema {schema!r}; this build.py renders schema {BUNDLE_SCHEMA}")
    if schema > BUNDLE_SCHEMA:
        raise BadBundle(f"schema: bundle schema {schema} is newer than this build.py ({BUNDLE_SCHEMA})")

    def expect(path, value, kinds, name):
        if not isinstance(value, kinds):
            got = "missing" if value is None else type(value).__name__
            raise BadBundle(f"{path}: expected {name}, got {got}")

    t = b.get("tenant")
    expect("tenant", t, dict, "an object")
    expect("tenant.id", t.get("id"), str, "a string")
    for i, e in enumerate(_expect_list(b, "envs")):
        expect(f"envs[{i}]", e, dict, "an object")
        expect(f"envs[{i}].key", e.get("key"), str, "a string")
        expect(f"envs[{i}].name", e.get("name"), str, "a string")
    for i, a in enumerate(_expect_list(b, "assets")):
        expect(f"assets[{i}]", a, dict, "an object")
        for f in ("k", "n", "t"):
            expect(f"assets[{i}].{f}", a.get(f), str, "a string")
    dep = b.get("deployments")
    if dep is not None:
        expect("deployments", dep, dict, "an object or null")
        expect("deployments.envs", dep.get("envs"), dict, "an object")
        expect("deployments.assets", dep.get("assets"), dict, "an object")
    health = b.get("health")
    if health is not None:
        expect("health", health, dict, "an object or null")
        if not health.get("skipped"):
            expect("health.envs", health.get("envs"), dict, "an object")
            expect("health.assets", health.get("assets"), dict, "an object")
    ai = b.get("ai")
    if ai is not None:
        expect("ai", ai, dict, "an object or null")
        expect("ai.status", ai.get("status"), str, "a string")
        if ai["status"] == "complete":
            for part in ("agents", "connections"):
                for i, row in enumerate(_expect_list(ai, part, f"ai.{part}")):
                    expect(f"ai.{part}[{i}]", row, dict, "an object")
                    expect(f"ai.{part}[{i}].k", row.get("k"), str, "a string")
            expect("ai.stats", ai.get("stats"), dict, "an object")
        elif ai["status"] != "skipped":
            raise BadBundle(f"ai.status: expected 'complete' or 'skipped', got {ai['status']!r}")


def _expect_list(obj: dict, key: str, path: str | None = None) -> list:
    v = obj.get(key)
    if not isinstance(v, list):
        raise BadBundle(f"{path or key}: expected a list, got "
                        f"{'missing' if v is None else type(v).__name__}")
    return v


# ---------------------------------------------------------------------------
# AI governance (context_agents / context_connections, tenant-wide)
# ---------------------------------------------------------------------------

def _ctx_offset(p):
    v = (p.get("pagination") or {}).get("offset")
    return v if _is_int(v) else None


def _ctx_next(p):
    n = p.get("next_offset")
    if not _is_int(n):
        n = (p.get("pagination") or {}).get("nextPageOffset")
    return n if _is_int(n) else None


def _merge_ctx_pages(pages: list[dict], tool: str) -> tuple[list[dict], str | None]:
    """Merge one tenant-wide context_* section. Returns (rows, incomplete line).

    On `owned_only: false` the server's `total` is only a lower bound
    (`offset + rows + 1`) while more pages exist, so completeness is judged
    from the page chain: pages ordered by `pagination.offset` when each
    echoes a distinct one, the first at 0, each where the previous one's
    `next_offset` pointed, the last not truncated. Raises BadPage for a page
    that repeats an earlier one."""
    for p in pages:
        if not isinstance(p.get("data"), list):
            raise BadPage(f"{tool} page has no `data` list (was it saved without its envelope?)")
    offsets = [_ctx_offset(p) for p in pages]
    chained = all(o is not None for o in offsets) and len(set(offsets)) == len(offsets)
    if chained:
        pages = sorted(pages, key=_ctx_offset)
    rows, seen = [], set()
    for i, page in enumerate(pages, 1):
        added = 0
        for r in page["data"]:
            if not isinstance(r, dict) or r.get("key") in seen:
                continue
            seen.add(r.get("key"))
            rows.append(r)
            added += 1
        if i > 1 and page["data"] and added == 0:
            raise BadPage(f"{tool} page {i} added no new rows: it repeats an earlier page. "
                          f"Pass `offset` (the previous page's `next_offset`)")
    last = pages[-1]
    broken = (_ctx_offset(pages[0]) not in (None, 0))
    if chained and not broken:
        expected = 0
        for page in pages:
            if _ctx_offset(page) != expected:
                broken = True
                break
            expected = _ctx_next(page)
    if broken:
        return rows, (f"{tool}: the pages passed do not form a chain from offset 0; re-fetch "
                      f"{tool} {{owned_only: false, limit: 100, offset: 0}} and page with "
                      f"`next_offset`, passing every page")
    if last.get("truncated") is True:
        nxt = _ctx_next(last)
        return rows, (f"{tool}: {len(rows)} rows received, more exist; fetch {tool} with the "
                      f"same arguments plus offset: {nxt if nxt is not None else len(rows)}")
    total = last.get("total")
    if _is_int(total) and len(rows) < total:
        return rows, (f"{tool}: {len(rows)} rows received of {total}; a page is missing, "
                      f"re-fetch from offset 0")
    return rows, None


def _ai_date(row: dict) -> str:
    ad = row.get("additionalData") if isinstance(row.get("additionalData"), dict) else {}
    return (_ai_str(ad.get("revisionDateTime")) or _ai_str(row.get("timestamp")))


def _ai_str(v) -> str:
    """A string field, or "" when absent, null or the server's
    `{"_truncated": true, "_originalBytes": N}` marker."""
    return v if isinstance(v, str) else ""


def _ai(assets: list[dict], args) -> tuple[dict, list[str], list[pathlib.Path]]:
    """The AI governance part of the bundle, joined to assets by key."""
    incomplete: list[str] = []
    paths: list[pathlib.Path] = []
    sections = {}
    for tool, files in (("context_agents", args.ai_agents), ("context_connections", args.ai_connections)):
        fps = [pathlib.Path(f).resolve() for f in files]
        paths += fps
        rows, inc = _merge_ctx_pages([_read_page(p, tool) for p in fps], tool)
        if inc:
            incomplete.append(inc)
        sections[tool] = rows
    asset_keys = {a["k"] for a in assets}
    now = datetime.datetime.now(datetime.timezone.utc)

    connections = []
    for c in sections["context_connections"]:
        ad = c.get("additionalData") if isinstance(c.get("additionalData"), dict) else {}
        pid = _ai_str(ad.get("providerId"))
        connections.append({
            "k": _ai_str(c.get("key")), "n": _ai_str(c.get("name")) or "—",
            "provider": _ai_str(c.get("providerName")) or AI_PROVIDER_LABELS.get(pid, pid) or AI_NOT_REPORTED,
            "providerId": pid,
            "entitlement": _ai_str(ad.get("entitlement")) or AI_NOT_REPORTED,
            "date": _ai_date(c)[:10],
            "listed": _ai_str(c.get("key")) in asset_keys,
        })
    connections.sort(key=lambda c: (c["provider"], c["n"].lower()))

    agents = []
    for a in sections["context_agents"]:
        name = _ai_str(a.get("name")) or "—"
        date = _ai_date(a)
        stale = False
        if date:
            try:
                d = _parse_iso(date)
                stale = (now - d).days > AI_STALE_DAYS
            except ValueError:
                pass
        agents.append({
            "k": _ai_str(a.get("key")), "n": name,
            "pub": a.get("isPublic") is True,
            "date": date[:10],
            "testDemo": bool(AI_TEST_DEMO.search(name)),
            "stale": stale,
            "listed": _ai_str(a.get("key")) in asset_keys,
        })
    agents.sort(key=lambda a: a["n"].lower())

    counts: dict[str, int] = {}
    for c in connections:
        counts[c["provider"]] = counts.get(c["provider"], 0) + 1
    stats = {
        "totalAgents": len(agents), "totalConnections": len(connections),
        "trialConns": sum(1 for c in connections if c["entitlement"] == "Trial"),
        "customerConns": sum(1 for c in connections if c["entitlement"] == "Customer"),
        "unreportedEntitlementConns": sum(1 for c in connections if c["entitlement"] == AI_NOT_REPORTED),
        "unreportedProviderConns": sum(1 for c in connections if c["provider"] == AI_NOT_REPORTED),
        "publicAgents": sum(1 for a in agents if a["pub"]),
        "testDemoAgents": sum(1 for a in agents if a["testDemo"]),
        "staleAgents": sum(1 for a in agents if a["stale"]),
        "staleDays": AI_STALE_DAYS,
        "providers": [{"name": n, "count": k} for n, k in sorted(counts.items(), key=lambda x: -x[1])],
    }
    unlisted = [r["k"] for r in agents + connections if not r["listed"]]
    return ({"status": "complete", "agents": agents, "connections": connections,
             "stats": stats, "unlisted": unlisted,
             "coveredTypes": sorted(AI_COVERED_TYPES)}, incomplete, paths)


# ---------------------------------------------------------------------------
# Report lines (stdout, both modes) — what Step 6 relays
# ---------------------------------------------------------------------------

def _summary(bundle: dict) -> list[str]:
    assets = bundle.get("assets") or []
    envs = bundle.get("envs") or []
    names = {e["key"]: e["name"] for e in envs}
    hubs = {h: 0 for h in HUB_ORDER}
    unknown: dict[str, int] = {}
    for a in assets:
        hub = ASSET_TYPE_HUBS.get(a["t"])
        if hub is None:
            hub = "Other"
            unknown[a["t"] or "(none)"] = unknown.get(a["t"] or "(none)", 0) + 1
        hubs[hub] += 1
    line = "assets: " + " · ".join(f"{h} {n}" for h, n in hubs.items() if n or h != "Other")
    if unknown:
        line += " (unknown types under Other: " + ", ".join(
            f"{t} {n}" for t, n in sorted(unknown.items())) + ")"
    out = [line]

    dep = bundle.get("deployments")
    if dep is None:
        out.append("deployments: not fetched")
    else:
        parts = []
        for key, s in dep["envs"].items():
            name = names.get(key, key)
            if s["status"] == "complete":
                parts.append(f"{name} complete ({s['shown']})")
            elif s["status"] == "partial":
                parts.append(f"{name} PARTIAL ({s['shown']} of {s['total']} listed; the rest "
                             f"could not be fetched)")
            else:
                parts.append(f"{name} SKIPPED ({s.get('reason')})")
        out.append(f"deployments (as of {_fmt_ts(dep.get('fetched_at'))}): " + " · ".join(parts)
                   + f"; {len(dep.get('drift') or {})} asset(s) with revision drift")

    health = bundle.get("health")
    if health is None:
        out.append("health: not fetched")
    elif health.get("skipped"):
        out.append(f"health: skipped ({health['skipped']})")
    elif all(s["status"] == "skipped" for s in health["envs"].values()):
        out.append("health: skipped (" + "; ".join(
            f"{names.get(k, k)}: {s.get('reason')}" for k, s in health["envs"].items()) + ")")
    else:
        parts = []
        for key, s in health["envs"].items():
            name = names.get(key, key)
            if s["status"] == "skipped":
                parts.append(f"{name} SKIPPED ({s.get('reason')})")
                continue
            counts = {c: 0 for c in _CLASS_PRIORITY}
            for entry in health["assets"].values():
                r = entry["by_env"].get(key)
                if r:
                    counts[r["cls"]] += 1
            text = (f"{name} {s['status'].upper() if s['status'] != 'complete' else 'complete'}: "
                    f"{counts['errors']} had errors, {counts['traffic']} traffic without "
                    f"recorded errors, {counts['noTraffic']} no traffic, "
                    f"{counts['noReading']} no reading")
            if s["status"] != "complete":
                text += f" (no-traffic claims withheld: {s.get('reason')})"
            if s.get("advisory"):
                text += f" (advisory: {s['advisory']})"
            if s.get("unresolved"):
                text += f" ({len(s['unresolved'])} unresolved)"
            parts.append(text)
        window = f"{health.get('hours')}h, {health.get('since')} → {health.get('to')}"
        out.append(f"health ({window}; not an incident view): " + " · ".join(parts))

    ai = bundle.get("ai")
    if ai is None:
        out.append("ai governance: not fetched")
    elif ai.get("status") == "skipped":
        out.append(f"ai governance: skipped ({ai.get('reason')})")
    else:
        st = ai["stats"]
        prov = ", ".join(f"{p['name']} {p['count']}" for p in st["providers"]) or "none"
        text = (f"ai governance: {st['totalAgents']} agents ({st['testDemoAgents']} test/demo-named, "
                f"{st['staleAgents']} not updated in {AI_STALE_DAYS}+ days), "
                f"{st['totalConnections']} model connections ({st['trialConns']} Trial, "
                f"{st['customerConns']} Customer, {st['unreportedEntitlementConns']} entitlement not "
                f"reported; providers: {prov})")
        if ai.get("unlisted"):
            text += f"; {len(ai['unlisted'])} not in the asset list"
        out.append(text + ". Agent definitions and non-model connections are not covered by this source")
    return out


def _fmt_ts(ts) -> str:
    if not _is_int(ts):
        return "unknown"
    return datetime.datetime.fromtimestamp(ts, tz=datetime.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


if __name__ == "__main__":
    sys.exit(main(sys.argv))
