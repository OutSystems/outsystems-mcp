#!/usr/bin/env python3
"""
build.py — build the per-app architecture HTML from MCP responses.

Pure stdlib Python. No external dependencies.

Usage (fresh build):
    python3 build.py <cache-dir> <output-path> \
        --app-info <path>                         \
        --screens <path> [<page2> ...]            \
        --actions <path> [...]                    \
        --entities <path> [...]                   \
        --structures <path> [...]                 \
        --roles <path> [...]                      \
        [--connections <path> [...]]              \
        [--refs <path>] [--refs-cache <path>]     \
        [--revisions <path>]                      \
        [--env-list <path>] [--env-apps ENV_KEY=PATH ...]

Usage (cached re-render):
    python3 build.py <cache-dir> <output-path>

In fresh mode each flag is a path to a saved MCP response (an inline
compact write or a harness-saved tool-result file). The six context
sections are required; the rest are optional and each adds one part:

  --connections  context_connections {app, owned_only: false} page(s):
                 AI model connections the app uses (Dependencies layer).
  --refs         app_refs response: referenced libraries (Dependencies layer).
  --refs-cache   the outsystems-dependency-impact cache (root dir, tenant dir
                 or refs file). Used only when --refs is absent or a failed
                 placeholder, and only if it is not a failed placeholder, is
                 under 24h old and was written after app_info.revisionDateTime.
  --revisions    app_revisions {key, limit: 10}: recent history.
  --env-list / --env-apps
                 env_list and one env_apps {env_key, search: <app name>}
                 response per environment: where the app is deployed.

The script transforms them, writes the compact bundle to
<cache-dir>/app-data.json + meta.json, then injects into the template.
In cached mode the script reads <cache-dir>/app-data.json directly.

Exit codes: 0 written; 1 bad input (not JSON, cut by the harness, a
repeated page) or missing files; 2 usage; 3 a context section is
incomplete (fetch the offset it names) or the cache is from an older
schema (re-run fresh mode).

The template (assets/template.html) has a single placeholder:
    const APP_DATA = /*__APP_DATA__*/null;
"""

from __future__ import annotations

import argparse
import datetime
import json
import pathlib
import re
import sys
import time


PLACEHOLDER = "/*__APP_DATA__*/null"


# ---- BEGIN SHARED TRANSFORM ------------------------------------------------
# Everything between this marker and END SHARED TRANSFORM turns the raw MCP
# responses into the bundle (app-data.json). Keep it free of rendering code so
# another renderer can reuse the same bundle.

# Bump when the bundle shape changes in a way older caches must not be reused
# for. 2 = ownership by isReferenced, inheritedEnums / inheritedBuiltinCount,
# action kinds action/client/service (v1.5.0). 3 = entity / structure
# attributes with resolved foreign keys, static-entity records, action
# signatures, screen input parameters, AI model connections in deps,
# deployments and recent revisions (v1.6.0). The number is written into
# app-data.json itself (and meta.json), so a consumer can refuse a bundle
# without its meta file.
BUNDLE_SCHEMA = 3


def _bundle_schema(bundle: dict) -> int:
    """Schema of an app-data.json. Bundles before 3 carry no `schema` key:
    those with `inheritedBuiltinCount` are schema 2, anything older is 1."""
    s = bundle.get("schema")
    if isinstance(s, int):
        return s
    return 2 if "inheritedBuiltinCount" in bundle else 1


def _bundle_is_stale(bundle: dict) -> bool:
    return _bundle_schema(bundle) < BUNDLE_SCHEMA


class BadInput(Exception):
    """An input file that cannot be used as-is: not JSON, or cut by the harness."""


class BadPage(Exception):
    """A saved page that repeats an earlier one (the offset was not passed)."""


class TruncatedSection(Exception):
    """A context_* section's saved pages do not cover the inventory.

    `next_offset` is the offset to fetch next when the last page is truncated;
    it is None when a page is missing or the page chain is broken. `total_is_floor`
    says the server's `total` was only a lower bound (owned_only: false path).
    """

    def __init__(self, section: str, received: int, total, next_offset, total_is_floor: bool = False) -> None:
        super().__init__(section)
        self.section, self.received, self.total, self.next_offset = section, received, total, next_offset
        self.total_is_floor = total_is_floor


# Codex truncates an MCP tool result above ~10K tokens: it keeps the head and
# the tail, prefixes "Warning: truncated output (original token count: N)" and
# replaces the middle with "…N tokens truncated…" (older byte-based policy:
# "…N chars truncated…"; line-oriented output: "[... omitted N of M lines
# ...]"). Nothing is spilled to a file, so a response saved from that text has
# lost rows. The header is only ever at the start, and the mid-marker makes
# the JSON invalid, so only those two places are read: a tenant-chosen name
# that happens to contain the words ("12 tokens truncated") must not fail the
# build.
_CODEX_HEADER = "Warning: truncated output"
_CODEX_MID_MARKER = re.compile(
    r"…\d+ (?:tokens|chars) truncated…|\[\.\.\. omitted \d+ of \d+ lines \.\.\.\]")
_CODEX_ADVICE = ("Codex cuts MCP results above ~10K tokens and does not save the rest: "
                 "re-fetch this call with a smaller `limit` (25 on Codex) and page with "
                 "`offset`, writing each page to its own file.")


def _read_json(path, label: str):
    """Read one saved MCP response. Raises BadInput for a file that starts with
    Codex's truncation header and for a file that is not JSON (naming the
    mid-marker when one is present)."""
    path = pathlib.Path(path)
    text = path.read_text(encoding="utf-8")
    if text.lstrip().startswith(_CODEX_HEADER):
        raise BadInput(f"{label}: {path} starts with the harness's output-truncation header, "
                       f"so rows are missing. {_CODEX_ADVICE}")
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        seen = _CODEX_MID_MARKER.search(text)
        if seen:
            raise BadInput(f"{label}: {path} is not valid JSON and carries the harness's "
                           f"truncation marker '{seen.group(0)}', so rows are missing. "
                           f"{_CODEX_ADVICE}")
        raise BadInput(f"{label}: {path} is not valid JSON ({exc}). Save the tool's response "
                       f"unchanged (or a compact write of it) and re-run.")


def _is_error_result(raw) -> bool:
    """A saved tool result that is an error, not data: an MCP `isError`
    result or a bare `{error: ...}` object with no payload keys."""
    if not isinstance(raw, dict):
        return False
    if raw.get("isError") is True:
        return True
    return "error" in raw and not any(k in raw for k in ("results", "data", "references"))


def _read_optional(path, label: str):
    """An optional input (refs, revisions, env-list, one env-apps response):
    a missing file or a saved error result degrades that section instead of
    failing the build. Returns None and says why on stderr."""
    if path is None:
        return None
    path = pathlib.Path(path)
    if not path.exists():
        print(f"note: {label}: {path} does not exist; that section is rendered as "
              f"unavailable", file=sys.stderr)
        return None
    raw = _read_json(path, label)
    if _is_error_result(raw):
        print(f"note: {label}: {path} is an error result, not data; that section is "
              f"rendered as unavailable", file=sys.stderr)
        return None
    return raw


# The server replaces any string over 2048 bytes inside `additionalData` with
# {"_truncated": true, "_originalBytes": N}. Every string read from `additionalData` goes through _s,
# so a marker never reaches .strip() or a template as if it were text.

def _truncated_bytes(v):
    """N for the server's truncation marker, else None."""
    if isinstance(v, dict) and v.get("_truncated") is True:
        n = v.get("_originalBytes")
        return n if isinstance(n, int) else 0
    return None


def _s(v) -> str:
    """A string field that may be absent, non-string or the truncation marker."""
    if isinstance(v, str):
        return v
    if v is None or _truncated_bytes(v) is not None:
        return ""
    return str(v)


def _desc(v) -> str:
    """A description: the text, or a note when the server truncated it."""
    n = _truncated_bytes(v)
    if n is not None:
        return f"[not shown: the server truncated it ({n} bytes)]"
    return _s(v).strip()[:TEXT_KEEP]


# Ownership and action-kind resolution -------------------------------------
#
# The Context Service indexes by VISIBILITY, not ownership: on an app-scoped
# query every row, inherited ones included, carries the visiting app's key in
# `ownerAppKey` (and `assetKey`). The ownership signal is `isReferenced`
# (false = defined in this app; true = inherited from a referenced library,
# with `producerAssetKey`/`producerAssetName` naming the producer). Rows from
# older payloads without `isReferenced` fall back to the `ownerAppKey` test.

def _is_owned(row: dict, app_key: str) -> bool:
    ref = row.get("isReferenced")
    if isinstance(ref, bool):
        return not ref
    # `isReferenced` is nullable and may be absent on a deployment that has
    # not backfilled it. `producerAssetKey` is the next-best signal: it names
    # the producing library on inherited rows and equals the app on owned ones.
    producer = row.get("producerAssetKey")
    if producer and producer not in (app_key, row.get("assetKey")):
        return False
    return row.get("ownerAppKey") == app_key


def _producer_name(row: dict) -> str:
    return (row.get("producerAssetName")
            or (row.get("additionalData") or {}).get("producerAssetName")
            or "<unknown module>")


def _load_section(paths, section: str) -> dict:
    """Load one or more saved pages of a context_* response and merge them.

    Each file is the tool's envelope `{data: [...], total?, truncated?,
    next_offset?, pagination?: {limit, offset, nextPageOffset, total?}}`; a
    compact-written file must keep those top-level keys. Rows are merged by
    `key`. Completeness is judged from the page chain, not from `total`:
    on an `owned_only: false` call the server's `total` is only a floor
    (`offset + rows + 1` while more pages exist). When every page echoes a
    distinct `pagination.offset` the pages are sorted by it and must run
    contiguously from 0 through each page's `next_offset`; otherwise the
    pages are taken in the order passed. The first page must start at 0 and
    the last must not be truncated. Owned-only pages carry a real
    `pagination.total`, which is also checked.

    Raises TruncatedSection (next_offset set) when the last page says more
    rows exist, TruncatedSection (next_offset None) when a page is missing or
    the chain is broken, BadPage when a page repeats an earlier one, and
    BadInput when a file is not JSON or was cut by the harness.
    """
    if isinstance(paths, (str, pathlib.Path)):
        paths = [paths]
    pages = []
    for path in paths:
        page = _read_json(path, section)
        if not isinstance(page, dict) or not isinstance(page.get("data"), list):
            raise KeyError(f"{section}: data")
        pages.append(page)

    def _offset(p):
        o = (p.get("pagination") or {}).get("offset")
        return o if isinstance(o, int) else None

    def _next(p):
        n = p.get("next_offset")
        if not isinstance(n, int):
            n = (p.get("pagination") or {}).get("nextPageOffset")
        return n if isinstance(n, int) else None

    def _truncated(p):
        return p.get("truncated") is True or (p.get("truncated") is None and _next(p) is not None)

    # `pagination.offset` has only been observed live for offset 0, so it is
    # trusted as a page position only when every page carries a distinct
    # value (a faithful echo). Otherwise pages are taken in the order passed
    # and linked through each page's `next_offset`.
    offsets = [_offset(p) for p in pages]
    has_pagination = all(o is not None for o in offsets)
    faithful = has_pagination and len(set(offsets)) == len(offsets)
    if faithful:
        pages.sort(key=_offset)
    if not has_pagination:
        print(f"warning: a saved {section} page has no `pagination` block; completeness "
              f"can only be checked against `total`, which may be a lower bound",
              file=sys.stderr)

    rows = []
    seen = set()
    for i, page in enumerate(pages, 1):
        added = 0
        for r in page["data"]:
            k = r.get("key")
            if k in seen:
                continue
            seen.add(k)
            rows.append(r)
            added += 1
        if i > 1 and added == 0 and page["data"]:
            raise BadPage(
                f"{section} page {i} added no new rows: it repeats an earlier page. "
                f"Was offset passed to the context tool?")

    last = pages[-1]
    total = last.get("total")
    total_is_floor = "total" not in (last.get("pagination") or {})
    first_offset = _offset(pages[0])

    if first_offset not in (None, 0):
        # The first page does not start at 0: the page(s) before it were not passed.
        raise TruncatedSection(section, len(rows), total, None, total_is_floor)
    if faithful:
        expected = 0
        for page in pages:
            if _offset(page) != expected:
                raise TruncatedSection(section, len(rows), total, None, total_is_floor)
            expected = _next(page)
    elif has_pagination:
        for prev, page in zip(pages, pages[1:]):
            if not _truncated(prev):
                print(f"warning: a {section} page was passed after a page that was not "
                      f"truncated; the pages may not belong together", file=sys.stderr)
    elif isinstance(total, int) and len(rows) >= total:
        # Legacy pages without a pagination block: a full row count against the
        # (owned-only, real) total is the only evidence available and it is
        # order-independent.
        return {"data": rows}
    if _truncated(last):
        raise TruncatedSection(section, len(rows), total,
                               _next(last) if _next(last) is not None else len(rows), total_is_floor)
    # A floor total is still a lower bound: fewer rows than `total` means rows
    # are missing whatever the page order. (The converse, rows >= total, proves
    # nothing on the floor path, which is why the chain is checked above.)
    if isinstance(total, int) and len(rows) < total:
        raise TruncatedSection(section, len(rows), total, None, total_is_floor)
    return {"data": rows}


# `additionalData.actionTypeStr` labels the action kind; the numeric
# `additionalData.actionType` mirrors it. Observed live (2026-09-03): 0 =
# "ServerAction", 1 = "ClientAction". "ServiceAction" is mapped in case the
# label appears, but no numeric code is assumed for it: an unknown code
# without a label is treated as a server action rather than guessed.
ACTION_KINDS = {"ServerAction": "action", "ClientAction": "client", "ServiceAction": "service"}
_ACTION_KIND_BY_CODE = {0: "action", 1: "client"}


def _action_kind(row: dict) -> str:
    ad = row.get("additionalData") or {}
    label = ad.get("actionTypeStr")
    if isinstance(label, str) and label in ACTION_KINDS:
        return ACTION_KINDS[label]
    return _ACTION_KIND_BY_CODE.get(ad.get("actionType"), "action")


# Built-in OutSystems modules. Inherited rows produced by them are counted but
# not listed, and they are filtered out of the Dependencies view: virtually
# every app inherits them, so they add noise without signal.
_BUILTIN_MODULES = {
    "(System)",
    "OutSystemsUI",
    "OutSystemsCharts",
    "OutSystemsMaps",
    "OutSystemsSampleData",
    "OutSystemsSecurity",
    "OutSystemsPipelines",
    "OutSystemsServerlessAddon",
}


# Timestamps ----------------------------------------------------------------
#
# The server writes ISO-8601 with 'Z' and 5-7 fraction digits
# ("2026-08-14T02:50:26.41323Z"), which datetime.fromisoformat() rejects
# before Python 3.11, so parse by hand.
_ISO_TS = re.compile(r"^(\d{4})-(\d{2})-(\d{2})[T ](\d{2}):(\d{2}):(\d{2})(?:\.(\d+))?(Z|[+-]\d{2}:?\d{2})?$")


def _parse_ts(value):
    """Aware UTC datetime for an ISO-8601 string, None if it does not parse."""
    if not isinstance(value, str):
        return None
    m = _ISO_TS.match(value.strip())
    if not m:
        return None
    y, mo, d, h, mi, s, frac, tz = m.groups()
    us = int((frac or "0")[:6].ljust(6, "0"))
    dt = datetime.datetime(int(y), int(mo), int(d), int(h), int(mi), int(s), us,
                           tzinfo=datetime.timezone.utc)
    if tz and tz != "Z":
        digits = tz[1:].replace(":", "")
        offset = datetime.timedelta(hours=int(digits[:2]), minutes=int(digits[2:]))
        dt = dt - offset if tz[0] == "+" else dt + offset
    return dt


def _iso_utc(ts: float) -> str:
    return datetime.datetime.fromtimestamp(ts, datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# Entities, attributes, foreign keys, records --------------------------------
#
# `additionalData.attributes[]` carries {name, dataType, isPrimaryKey,
# isMandatory, length, decimals, description, key}. A reference attribute's
# dataType is "<Entity> Identifier" (EmployeeId: "Employee Identifier"); the
# target is resolved by name against every entity row the app can see: owned
# first, then inherited from user libraries, then platform modules. A name that
# matches none of them is "external" (the entity was not in the payload).

_FK_TYPE = re.compile(r"^(?P<target>.+?) Identifier$")
RECORDS_KEEP = 50          # static-entity records kept in the bundle per entity
TEXT_KEEP = 160            # attribute / parameter descriptions


def _attr(a: dict) -> dict:
    out = {"n": _s(a.get("name")), "t": _s(a.get("dataType"))}
    if a.get("isPrimaryKey"):
        out["pk"] = True
    if a.get("isMandatory"):
        out["req"] = True
    length = _s(a.get("length")).strip()
    if length:
        out["len"] = length
    desc = _desc(a.get("description"))
    if desc:
        out["d"] = desc
    return out


def _attrs(row: dict) -> list:
    return [_attr(a) for a in (row.get("additionalData") or {}).get("attributes") or []
            if isinstance(a, dict)]


def _entity_index(rows: list, app_key: str) -> dict:
    """name -> {in, k, from?} over every entity row, owned names winning over
    inherited ones and user libraries over platform modules."""
    index = {}
    rank = {"owned": 0, "inherited": 1, "platform": 2}
    for e in rows:
        name = e.get("name")
        if not name:
            continue
        if _is_owned(e, app_key):
            hit = {"in": "owned", "k": e.get("key")}
        else:
            module = _producer_name(e)
            hit = {"in": "platform" if module in _BUILTIN_MODULES else "inherited",
                   "k": e.get("key"), "from": module}
        prev = index.get(name)
        if prev is None or rank[hit["in"]] < rank[prev["in"]]:
            index[name] = hit
    return index


def _resolve_fk(data_type: str, index: dict):
    """{n, in, k?, from?} for a "<Entity> Identifier" type, else None."""
    m = _FK_TYPE.match(data_type or "")
    if not m:
        return None
    target = m.group("target")
    hit = index.get(target)
    if hit is None:
        return {"n": target, "in": "external"}
    fk = {"n": target, "in": hit["in"], "k": hit["k"]}
    if hit.get("from"):
        fk["from"] = hit["from"]
    return fk


def _record_label(item) -> str:
    if isinstance(item, str):
        return item
    if isinstance(item, (int, float)) and not isinstance(item, bool):
        return str(item)
    if isinstance(item, dict):
        for k in ("identifier", "Identifier", "name", "Name", "label", "Label"):
            if item.get(k) not in (None, ""):
                return str(item[k])
        return json.dumps(item, separators=(",", ":"))[:80]
    return ""


def _parse_records(raw, entity: str):
    """(labels[:RECORDS_KEEP], count, truncated_bytes) from `additionalData.records`.

    A static entity with many records (a country list) arrives as the server's
    truncation marker instead of the string: that returns ([], None, N), and the
    renderers say the records were truncated, never that there are none.

    The field is a JSON *string* ("[]", '["InStock","Assigned"]'). An absent
    field is no records; a string that is not a JSON list is reported on stderr
    and treated as no records. "[]" is common on inherited static entities
    whose records the Context Service did not index, so it means "none
    recorded", not "none exist"."""
    cut = _truncated_bytes(raw)
    if cut is not None:
        return [], None, cut
    if raw is None or raw == "":
        return [], 0, None
    items = raw
    if isinstance(raw, str):
        try:
            items = json.loads(raw)
        except json.JSONDecodeError:
            items = None
    if not isinstance(items, list):
        print(f"warning: entity {entity}: additionalData.records is not a JSON list; "
              f"rendered without records", file=sys.stderr)
        return [], 0, None
    labels = [l for l in (_record_label(x) for x in items) if l]
    return labels[:RECORDS_KEEP], len(labels), None


# Actions and screens --------------------------------------------------------

def _signature(row: dict):
    """(inputs, outputs) from `additionalData.parameters[]`, in payload order.
    `parameterTypeStr` is "Input" or "Output" (numeric `parameterType` 0 / 1)."""
    ins, outs = [], []
    for p in (row.get("additionalData") or {}).get("parameters") or []:
        if not isinstance(p, dict):
            continue
        item = {"n": _s(p.get("name")), "t": _s(p.get("dataType"))}
        if p.get("isMandatory"):
            item["req"] = True
        desc = _desc(p.get("description"))
        if desc:
            item["d"] = desc
        kind = _s(p.get("parameterTypeStr")) or {0: "Input", 1: "Output"}.get(p.get("parameterType"))
        (outs if kind == "Output" else ins).append(item)
    return ins, outs


# `additionalData.title` can hold a serialised expression instead of text:
# '"Change password" [TitleExpression[ServiceStudio.Expressions.AbstractExpression]]'.
# Keep a plain string literal, drop anything that still looks like an expression.
_TITLE_EXPR = re.compile(r"\s*\[TitleExpression\[[^\]]*\]\]\s*$")


def _clean_title(raw, name: str) -> str:
    if not isinstance(raw, str):
        return ""
    t = _TITLE_EXPR.sub("", raw).strip()
    if len(t) >= 2 and t[0] == t[-1] == '"' and '"' not in t[1:-1]:
        t = t[1:-1].strip()
    elif '"' in t or "[" in t or "ServiceStudio." in t:
        return ""
    return "" if t == name else t[:120]


# Screen roles are deliberately NOT read. `additionalData.roles` is filled from
# the model's screen roles list, which does not carry the screen's access mode
# (Everyone / Authenticated / selected roles): a screen "Accessible by:
# Everyone" can still list the app role (the recorded template Login screen
# does). Keeping it out of the bundle stops any consumer from presenting it as
# who can open the screen.


def _screen_inputs(row: dict) -> list:
    out = []
    for p in (row.get("additionalData") or {}).get("inputParameters") or []:
        if not isinstance(p, dict):
            continue
        item = {"n": _s(p.get("name")), "t": _s(p.get("dataType"))}
        if p.get("isRequired") or p.get("isMandatory"):
            item["req"] = True
        out.append(item)
    return out


# Dependencies: app_refs, the dependency-impact cache, AI model connections ---

def _categorize_dep(kind: str) -> str:
    """Map a reference's kind → visual category in the graph.

    Only the legacy producer-asset kind (`kind`/`importedKind`) ever
    carried "AIModelConnection". The current Context-Service-first app_refs
    reports imported ELEMENT kinds instead (entities/actions/…), which never
    identify the producer as an AI model, so those fall through to Library.
    AI model connections come from `context_connections` (see
    _connection_deps).
    """
    if kind == "AIModelConnection":
        return "AIModel"
    return "Library"  # eSpace, Extension, entities-import, etc.


def _ref_kind(r: dict) -> str:
    """Best scalar 'kind' for a reference across every app_refs shape.

    Prefers the scalar producer kind when present:
      - legacy MCP:                     `kind`  (e.g. "AIModelConnection", "eSpace")
      - schemaVersion 2 / oml-fallback: `importedKind`
    Otherwise falls back to the schemaVersion-2 / context-service `kinds`
    LIST of imported element kinds (e.g. ["entities"]), joined to a string.
    """
    scalar = r.get("kind") or r.get("importedKind")
    if scalar:
        return scalar
    kinds = r.get("kinds")
    if isinstance(kinds, list):
        return ", ".join(str(k) for k in kinds if k)
    if isinstance(kinds, str):
        return kinds
    return ""


def _refs_deps(raw) -> list:
    """Dependency edges from one app_refs response (or dependency-impact cache
    file). Tolerant of every reference shape seen in the wild:
      - legacy:                         {moduleKey, name, kind, revision}
      - schemaVersion 2 / oml-fallback: {producerAssetKey, producerAssetName, importedKind}
      - schemaVersion 2 / context-service (live 2026-07-09):
                                        {producerAssetKey, producerAssetName, kinds: [...]}
    Built-in modules are dropped. A `failed` placeholder yields []."""
    if not isinstance(raw, dict) or raw.get("failed"):
        return []
    deps = []
    for r in raw.get("references", []) or []:
        name = r.get("name") or r.get("producerAssetName") or ""
        if not name or name in _BUILTIN_MODULES:
            continue
        kind = _ref_kind(r)
        deps.append({
            "k":    r.get("moduleKey") or r.get("producerAssetKey") or "",
            "n":    name,
            "kind": kind,
            "cat":  _categorize_dep(kind),
            "rev":  str(r.get("revision") or ""),
        })
    return deps


def _build_deps(refs_path, app_key: str) -> list:
    """_refs_deps over a saved file; [] when the file is missing or malformed."""
    if refs_path is None:
        return []
    try:
        raw = json.loads(pathlib.Path(refs_path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    return _refs_deps(raw)


REFS_CACHE_MAX_AGE = 24 * 3600


def _find_refs_cache(path, app_key: str):
    """The dependency-impact refs file for this app. `path` is the file itself,
    a tenant cache dir (holding refs/), or the skill's cache root (holding
    <tenant-id>/refs/). App keys are UUIDs, so a match under any tenant folder
    is this app; the newest one wins."""
    if path is None:
        return None
    path = pathlib.Path(path).expanduser()
    if path.is_file():
        return path
    if not path.is_dir():
        return None
    hits = list(path.glob(f"refs/{app_key}.json")) + list(path.glob(f"*/refs/{app_key}.json"))
    return max(hits, key=lambda p: p.stat().st_mtime) if hits else None


def _refs_cache_verdict(path, app_key: str, revision_at, now=None):
    """(raw, None) when the dependency-impact cache file may stand in for a
    fresh app_refs call, else (None, reason). Rejected: an unreadable file, a
    `failed: true` placeholder (the scan timed out; it is not a result), a
    file for another app, a file older than 24h, and a file written before
    the app's current revision was saved (`app_info.revisionDateTime`), whose
    references may predate the change."""
    now = time.time() if now is None else now
    try:
        mtime = path.stat().st_mtime
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return None, f"unreadable ({exc})"
    if not isinstance(raw, dict):
        return None, "not an app_refs object"
    if raw.get("failed"):
        return None, "a failed-scan placeholder"
    if raw.get("assetKey") not in (None, app_key):
        return None, f"for another app ({raw.get('assetKey')})"
    if now - mtime > REFS_CACHE_MAX_AGE:
        return None, "older than 24h"
    if revision_at is not None and mtime < revision_at.timestamp():
        return None, "written before the app's current revision"
    return raw, None


def _connection_deps(rows: list, app_key: str) -> list:
    """AI model connections the app uses, from `context_connections` scoped
    with `app` and `owned_only: false`. A connection is its own asset, so on
    an app-scoped query it is a referenced row (isReferenced: true) that
    owned_only: true would filter out. The row's own `key`/`name` identify the
    connection: the Context Service never sets producerAssetKey /
    producerAssetName on agent or connection rows; they are read only as a
    fallback. A row naming the app itself is skipped."""
    deps = []
    for r in rows:
        key = _s(r.get("key")) or _s(r.get("producerAssetKey"))
        if key == app_key:
            continue
        name = _s(r.get("name")) or _s(r.get("producerAssetName"))
        if not name:
            continue
        deps.append({"k": key, "n": name, "kind": _s(r.get("providerName")) or "AIModelConnection",
                     "cat": "AIModel", "rev": ""})
    return deps


def _merge_deps(connections: list, refs: list) -> list:
    """Connections first (their AIModel category wins), then app_refs rows not
    already present by key, or by name when a row has no key."""
    out, keys, names = [], set(), set()
    for d in list(connections) + list(refs):
        if (d["k"] and d["k"] in keys) or d["n"].lower() in names:
            continue
        if d["k"]:
            keys.add(d["k"])
        names.add(d["n"].lower())
        out.append(d)
    return out


# Deployments and revisions ---------------------------------------------------

def _results(raw) -> list:
    if isinstance(raw, list):
        return raw
    if isinstance(raw, dict):
        for k in ("results", "data"):
            if isinstance(raw.get(k), list):
                return raw[k]
    return []


def _env_apps_truncated(raw) -> bool:
    if not isinstance(raw, dict):
        return False
    total, shown = raw.get("total"), raw.get("displayed")
    return raw.get("truncated") is True or (
        isinstance(total, int) and isinstance(shown, int) and shown < total)


def _not_listed_reason(app_type: str):
    """Why env_apps can say nothing about this asset type, or None.

    The server drops Workflow rows from env_apps, so a workflow's absence
    is no evidence; libraries are consumed by the apps that reference them and
    have no deployment of their own."""
    t = app_type or ""
    if t == "Workflow":
        return "unknown", "env_apps does not list workflows"
    if t.endswith("Library"):
        return "n/a", "libraries are not deployed on their own"
    return None


def _build_deployments(env_list, env_apps: dict, app_key: str, latest, fetched_at, app_type=""):
    """Per-environment deployment state of this app.

    `env_apps` maps env key -> the saved `env_apps {env_key, search: <app name>}`
    response. `search` is a server-side name substring, so rows for other apps
    whose names contain this one come back too: only a row whose
    `applicationKey` equals the app key counts. The tool takes no offset, so
    a truncated response without a match is "unknown", never "not deployed";
    so is an environment whose response was not fetched or was an error, and
    every environment for an asset type env_apps cannot list. A matching row
    whose `revision` is null is deployed at an unknown revision: no drift."""
    envs = sorted((e for e in _results(env_list) if isinstance(e, dict) and e.get("key")),
                  key=lambda e: (e.get("order") if isinstance(e.get("order"), int) else 1 << 30))
    known = {e["key"] for e in envs}
    envs += [{"key": k, "name": k} for k in env_apps if k not in known]
    if not envs:
        return None
    out = []
    blind = _not_listed_reason(app_type)
    for e in envs:
        item = {"k": e["key"], "n": e.get("name") or e["key"], "purpose": e.get("purpose") or ""}
        raw = env_apps.get(e["key"])
        match = [r for r in _results(raw) if isinstance(r, dict) and r.get("applicationKey") == app_key]
        if blind is not None:
            item.update(status=blind[0], reason=blind[1])
        elif raw is None:
            item.update(status="unknown", reason="not fetched")
        elif match:
            row = max(match, key=lambda r: r.get("revision") if isinstance(r.get("revision"), int) else -1)
            rev = row.get("revision")
            item.update(status="deployed", rev=rev if isinstance(rev, int) else None,
                        at=_s(row.get("deploymentDateTime")))
            if isinstance(rev, int) and isinstance(latest, int):
                item["behind"] = max(latest - rev, 0)
        elif _env_apps_truncated(raw):
            item.update(status="unknown", reason="env_apps response truncated before a match")
        else:
            item["status"] = "not-deployed"
        out.append(item)
    return {"fetchedAt": fetched_at, "latestRevision": latest, "envs": out}


REVISIONS_KEEP = 10


def _build_revisions(raw):
    """Newest-first compact rows from an `app_revisions` page: {rev, at, digest, tag?}."""
    if raw is None:
        return None
    rows = []
    for r in _results(raw):
        if not isinstance(r, dict) or not isinstance(r.get("revision"), int):
            continue
        item = {"rev": r["revision"], "at": r.get("revisionDateTime") or "",
                "digest": r.get("modelDigest") or ""}
        if r.get("tag"):
            item["tag"] = r["tag"]
        rows.append(item)
    rows.sort(key=lambda x: -x["rev"])
    total = raw.get("total") if isinstance(raw, dict) else None
    return {"rows": rows[:REVISIONS_KEEP], "total": total if isinstance(total, int) else len(rows)}


# Transform --------------------------------------------------------------------

def _build_from_raw(args) -> dict:
    """Transform raw MCP responses into the compact bundle (schema 3).

    `args` carries app_info, screens, actions, entities, structures, roles
    (required) and refs, refs_cache, connections, revisions, env_list,
    env_apps (optional; env_apps is a list of (env_key, path) pairs)."""
    app_info = _read_json(args.app_info, "app-info")
    screens_raw    = _load_section(args.screens, "screens")
    actions_raw    = _load_section(args.actions, "actions")
    entities_raw   = _load_section(args.entities, "entities")
    structures_raw = _load_section(args.structures, "structures")
    roles_raw      = _load_section(args.roles, "roles")
    connections = getattr(args, "connections", None)
    connections_raw = _load_section(connections, "connections") if connections else {"data": []}

    app_key = app_info["assetKey"]
    revision_at = _parse_ts(app_info.get("revisionDateTime"))

    app = {
        "key":         app_info["assetKey"],
        "name":        app_info["name"],
        "type":        app_info.get("assetType", "WebApplication"),
        "revision":    app_info["revision"],
        "description": app_info.get("description", "") or "",
        "date":        (app_info.get("revisionDateTime") or "")[:10],
    }

    # ----- UI flows (derived from screens) -----
    ui_flows = {}
    screens = []
    for s in screens_raw.get("data", []):
        if not _is_owned(s, app_key):
            continue  # skip inherited
        ad = s.get("additionalData") or {}
        flow_key = ad.get("uiFlowKey", "default")
        flow_name = ad.get("uiFlowName", "Default")
        if flow_key not in ui_flows:
            ui_flows[flow_key] = {"key": flow_key, "name": flow_name}
        item = {
            "k":      s["key"],
            "n":      s["name"],
            "flow":   flow_key,
            "desc":   (s.get("description") or "")[:200],
            "pub":    bool(s.get("isPublic", False)),
            "date":   (s.get("timestamp", "") or "")[:10],
            "inputs": _screen_inputs(s),
        }
        title = _clean_title(ad.get("title"), s["name"])
        if title:
            item["title"] = title
        screens.append(item)

    # ----- Actions (server / client / service, per the Context Service) -----
    actions = []
    for a in actions_raw.get("data", []):
        if not _is_owned(a, app_key):
            continue
        ins, outs = _signature(a)
        actions.append({
            "k":    a["key"],
            "n":    a["name"],
            "kind": _action_kind(a),
            "desc": (a.get("description") or "")[:240],
            "pub":  bool(a.get("isPublic", False)),
            "in":   ins,
            "out":  outs,
        })

    # ----- Entities (business non-static) vs static enums -----
    # Owned rows and inherited rows from user libraries are listed (with their
    # attributes, so the data model can be drawn); rows produced by platform
    # modules (OutSystemsUI, Charts, Maps, System, ...) are counted but not
    # listed so they cannot drown the app's own model. Foreign keys resolve
    # against all of them, platform rows included (e.g. "User Identifier").
    index = _entity_index(entities_raw.get("data", []), app_key)
    entities, inherited_entities, enums, inherited_enums = [], [], [], []
    inherited_builtin_count = 0
    for e in entities_raw.get("data", []):
        is_owned = _is_owned(e, app_key)
        item = {
            "k":    e["key"],
            "n":    e["name"],
            "desc": (e.get("description") or "")[:200],
        }
        if not is_owned:
            item["fromModule"] = _producer_name(e)
            if item["fromModule"] in _BUILTIN_MODULES:
                inherited_builtin_count += 1
                continue
        attrs = _attrs(e)
        for at in attrs:
            fk = _resolve_fk(at["t"], index)
            if fk is not None:
                at["fk"] = fk
        item["attrs"] = attrs
        if e.get("isStatic", False):
            records, count, cut = _parse_records((e.get("additionalData") or {}).get("records"), e["name"])
            item["records"], item["recordCount"] = records, count
            if cut is not None:
                item["recordsTruncatedBytes"] = cut
            (enums if is_owned else inherited_enums).append(item)
        else:
            (entities if is_owned else inherited_entities).append(item)
    inherited_entity_count = len(inherited_entities) + len(inherited_enums) + inherited_builtin_count

    # ----- Structures -----
    structures = [
        {
            "k":     s["key"],
            "n":     s["name"],
            "desc":  (s.get("description") or "")[:200],
            "attrs": _attrs(s),
        }
        for s in structures_raw.get("data", [])
        if _is_owned(s, app_key)
    ]

    # ----- Roles -----
    roles = [
        {
            "k":    r["key"],
            "n":    r["name"],
            "desc": (r.get("description") or "") or "",
            "pub":  bool(r.get("isPublic", False)),
        }
        for r in roles_raw.get("data", [])
        if _is_owned(r, app_key)
    ]

    # ----- Dependencies: fresh app_refs, else the dependency-impact cache -----
    refs_raw, deps_source = None, None
    if getattr(args, "refs", None) is not None:
        fresh = _read_optional(args.refs, "refs")
        if isinstance(fresh, dict) and not fresh.get("failed"):
            refs_raw, deps_source = fresh, "app_refs"
        else:
            print("warning: no usable app_refs response (missing, an error or a failed "
                  "placeholder); trying the dependency-impact cache", file=sys.stderr)
    if refs_raw is None and getattr(args, "refs_cache", None) is not None:
        cache_file = _find_refs_cache(args.refs_cache, app_key)
        if cache_file is None:
            print("note: no dependency-impact refs cache for this app", file=sys.stderr)
        else:
            refs_raw, reason = _refs_cache_verdict(cache_file, app_key, revision_at)
            if refs_raw is None:
                print(f"note: dependency-impact refs cache {cache_file} not used: {reason}",
                      file=sys.stderr)
            else:
                deps_source = "dependency-impact cache"
    conn_deps = _connection_deps(connections_raw.get("data", []), app_key)
    deps = _merge_deps(conn_deps, _refs_deps(refs_raw))

    # ----- Deployments + recent revisions -----
    env_apps = {}
    apps_mtimes = []
    for env_key, path in getattr(args, "env_apps", None) or []:
        raw = _read_optional(path, f"env-apps {env_key}")
        if raw is not None:     # a missing or failed call stays out: "unknown (not fetched)"
            env_apps[env_key] = raw
            apps_mtimes.append(pathlib.Path(path).stat().st_mtime)
    env_list = _read_optional(getattr(args, "env_list", None), "env-list")
    deployments = None
    if env_apps or env_list is not None:
        # The env_apps files were saved as the calls returned: the oldest one
        # dates the snapshot. Shown as "as of" because deployments change
        # without the app revision changing. With no env_apps response at all,
        # every environment is "unknown (not fetched)".
        deployments = _build_deployments(env_list, env_apps, app_key, app["revision"],
                                         _iso_utc(min(apps_mtimes) if apps_mtimes else time.time()),
                                         app["type"])
    revisions = _build_revisions(_read_optional(getattr(args, "revisions", None), "revisions"))

    return {
        "schema":            BUNDLE_SCHEMA,
        "app":               app,
        "uiFlows":           list(ui_flows.values()),
        "screens":           screens,
        "actions":           actions,
        "entities":          entities,
        "inheritedEntities": inherited_entities,
        "enums":             enums,
        "inheritedEnums":    inherited_enums,
        "structures":        structures,
        "roles":             roles,
        "deps":              deps,
        "depsSource":        deps_source,   # where the library refs came from; None = unavailable
        "deployments":       deployments,
        "revisions":         revisions,
        "inheritedCount":    inherited_entity_count,
        "inheritedBuiltinCount": inherited_builtin_count,
    }


def _parse_env_apps(values) -> list:
    """`--env-apps KEY=PATH ...` -> [(key, Path)]."""
    out = []
    for v in values or []:
        key, sep, path = str(v).partition("=")
        if not sep or not key or not path:
            raise BadInput(f"--env-apps expects ENV_KEY=PATH, got {v!r}")
        out.append((key, pathlib.Path(path)))
    return out


def _add_input_args(p) -> None:
    """The raw-response flags, identical in both skills' build.py."""
    p.add_argument("--app-info",   type=pathlib.Path, default=None)
    # Each context section accepts one or more saved pages (see _load_section).
    p.add_argument("--screens",    type=pathlib.Path, nargs="+", default=None)
    p.add_argument("--actions",    type=pathlib.Path, nargs="+", default=None)
    p.add_argument("--entities",   type=pathlib.Path, nargs="+", default=None)
    p.add_argument("--structures", type=pathlib.Path, nargs="+", default=None)
    p.add_argument("--roles",      type=pathlib.Path, nargs="+", default=None)
    p.add_argument("--connections", type=pathlib.Path, nargs="+", default=None,
                   help="context_connections {app, owned_only: false} page(s): AI model connections")
    p.add_argument("--refs",       type=pathlib.Path, default=None,
                   help="app_refs response (library dependencies)")
    p.add_argument("--refs-cache", type=pathlib.Path, default=None,
                   help="outsystems-dependency-impact cache root, tenant dir or refs file; "
                        "used only when --refs is absent or a failed placeholder")
    p.add_argument("--revisions",  type=pathlib.Path, default=None,
                   help="app_revisions {key, limit: 10} response")
    p.add_argument("--env-list",   type=pathlib.Path, default=None, help="env_list response")
    p.add_argument("--env-apps",   nargs="+", default=None, metavar="ENV_KEY=PATH",
                   help="env_apps {env_key, search: <app name>} response per environment")


def _report_build_error(exc) -> int:
    """Print the stderr message for a failed fresh build; return the exit code."""
    if isinstance(exc, BadInput):
        print(f"BAD INPUT: {exc} Nothing was written to the cache.", file=sys.stderr)
        return 1
    if isinstance(exc, BadPage):
        print(f"BAD PAGE: {exc} Nothing was written to the cache.", file=sys.stderr)
        return 1
    if isinstance(exc, TruncatedSection):
        of_total = ""
        if exc.total is not None:
            of_total = f" of at least {exc.total}" if exc.total_is_floor else f" of {exc.total}"
        if exc.next_offset is not None:
            print(
                f"INCOMPLETE: {exc.section} page(s) hold {exc.received} rows{of_total} and more "
                f"exist. Call the same context tool again with offset: {exc.next_offset} "
                f"(same limit), save it, and re-run passing every saved page after "
                f"--{exc.section} in order. Nothing was written to the cache.",
                file=sys.stderr,
            )
        else:
            print(
                f"INCOMPLETE: {exc.section} page(s) hold {exc.received} rows{of_total} but do not "
                f"form a contiguous chain from offset 0 (a page is missing, or the inventory "
                f"changed between fetches). Re-run passing EVERY saved page after "
                f"--{exc.section}; if they are all there, re-fetch the section from offset 0 "
                f"(same limit) and rebuild. Nothing was written to the cache.",
                file=sys.stderr,
            )
        return 3
    print(f"build failed: {exc}", file=sys.stderr)
    return 1

# ---- END SHARED TRANSFORM --------------------------------------------------


def parse_args(argv: list) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("cache_dir", type=pathlib.Path)
    p.add_argument("out_path", type=pathlib.Path)
    _add_input_args(p)
    return p.parse_args(argv[1:])


def _inject(html: str, payload: str) -> str:
    # The bundle lands inside a <script> element. `<` only occurs inside JSON
    # strings, where \u003c is the same character: escaping every one stops a
    # description with "</script>" from closing the element and one with
    # "<!--<script" from putting the HTML parser into its double-escaped
    # script state. The template holds the placeholder once, and the payload
    # is not re-scanned after insertion.
    return html.replace(PLACEHOLDER, payload.replace("<", "\\u003c"), 1)



# Every skill in this family caches under one root, the "outsystems-skills"
# folder of the user's cache directory, in a folder per skill and per tenant
# (or app). `build.py --cache-dir <id>` creates and prints that folder, so the
# skill docs never spell out a home-folder path; `--skill <name>` prints a
# sibling skill's folder (for reading its cache, never for writing it).
CACHE_ROOT = pathlib.Path.home() / ".cache" / "outsystems-skills"
SKILL_NAME = "outsystems-app-architecture"
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


def main(argv: list) -> int:
    if len(argv) > 1 and argv[1] == "--cache-dir":
        return _cache_dir_command(argv[2:])
    args = parse_args(argv)

    # Skill root = parent of scripts/
    skill_dir = pathlib.Path(__file__).resolve().parent.parent
    template_path = skill_dir / "assets" / "template.html"

    cache_dir = args.cache_dir.resolve()
    out_path  = args.out_path.resolve()
    cache_dir.mkdir(parents=True, exist_ok=True)

    raw_flags = [args.app_info, args.screens, args.actions,
                 args.entities, args.structures, args.roles]
    optional = [args.connections, args.refs, args.refs_cache, args.revisions, args.env_list, args.env_apps]
    fresh_mode = any(p is not None for p in raw_flags + optional)

    if fresh_mode:
        if not all(p is not None for p in raw_flags):
            print("fresh mode requires ALL six --app-info/--screens/--actions/--entities/"
                  "--structures/--roles paths (or none for cached mode)", file=sys.stderr)
            return 2
        try:
            args.env_apps = _parse_env_apps(args.env_apps)
            app_data = _build_from_raw(args)
        except (BadInput, BadPage, TruncatedSection, FileNotFoundError, KeyError) as exc:
            return _report_build_error(exc)
        except (AttributeError, TypeError, ValueError) as exc:
            # A payload shape this build does not know: say so in one line
            # instead of a traceback, and write nothing.
            print(f"BAD INPUT: a saved response has an unexpected shape ({type(exc).__name__}: "
                  f"{exc}). Nothing was written; re-fetch the Step 3 responses unchanged, and "
                  f"report the file if it persists.", file=sys.stderr)
            return 1
        # Write compact bundle + freshness metadata
        (cache_dir / "app-data.json").write_text(
            json.dumps(app_data, separators=(",", ":")), encoding="utf-8")
        meta = {
            "revision": app_data["app"]["revision"],
            "fetched_at": int(time.time()),
            "schema": BUNDLE_SCHEMA,
        }
        if app_data.get("deployments"):
            meta["deployments_fetched_at"] = app_data["deployments"]["fetchedAt"]
        (cache_dir / "meta.json").write_text(json.dumps(meta, separators=(",", ":")), encoding="utf-8")

    # Inject
    data_path = cache_dir / "app-data.json"
    if not data_path.exists():
        print(f"missing {data_path} — run fresh mode first", file=sys.stderr)
        return 1
    if not template_path.exists():
        print(f"template not found: {template_path}", file=sys.stderr)
        return 1

    html = template_path.read_text(encoding="utf-8")
    payload = data_path.read_text(encoding="utf-8").strip()
    try:
        bundle = json.loads(payload)
    except json.JSONDecodeError as exc:
        print(f"{data_path} is not valid JSON: {exc}", file=sys.stderr)
        return 1
    if not fresh_mode and _bundle_is_stale(bundle):
        print(
            f"STALE: this cache is bundle schema {_bundle_schema(bundle)}, written by an older "
            f"build.py; this one renders schema {BUNDLE_SCHEMA} (attributes, signatures, "
            f"deployments). Re-run fresh mode with the Step 3 responses.",
            file=sys.stderr,
        )
        return 3
    if PLACEHOLDER not in html:
        print(f"placeholder {PLACEHOLDER!r} not in template", file=sys.stderr)
        return 1
    html = _inject(html, payload)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html, encoding="utf-8")

    fk_edges = sum(1 for e in bundle["entities"] + bundle.get("enums", [])
                   for a in e.get("attrs", []) if (a.get("fk") or {}).get("in") in ("owned", "inherited"))
    counts = {
        "uiFlows":    len(bundle["uiFlows"]),
        "screens":    len(bundle["screens"]),
        "serverActions":  sum(1 for a in bundle["actions"] if a["kind"] == "action"),
        "clientActions":  sum(1 for a in bundle["actions"] if a["kind"] in ("client", "function")),
        "serviceActions": sum(1 for a in bundle["actions"] if a["kind"] == "service"),
        "entities":   len(bundle["entities"]),
        "inheritedEntities": len(bundle.get("inheritedEntities", [])),
        "enums":      len(bundle["enums"]),
        "structures": len(bundle["structures"]),
        "roles":      len(bundle["roles"]),
        "fkEdges":    fk_edges,
        "aiModels":   sum(1 for d in bundle.get("deps", []) if d.get("cat") == "AIModel"),
        "libraries":  sum(1 for d in bundle.get("deps", []) if d.get("cat") == "Library"),
    }
    size_kb = out_path.stat().st_size / 1024
    print(f"wrote {out_path} ({size_kb:.1f} KB)")
    print(f"  app: {bundle['app']['name']} (rev {bundle['app']['revision']})")
    print("  " + " · ".join(f"{k}:{v}" for k, v in counts.items()))
    dep = bundle.get("deployments")
    if dep:
        print("  deployed: " + " · ".join(
            f"{e['n']} " + (f"r{e.get('rev')}" if e["status"] == "deployed" else e["status"])
            for e in dep["envs"]) + f" (as of {dep['fetchedAt']})")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
