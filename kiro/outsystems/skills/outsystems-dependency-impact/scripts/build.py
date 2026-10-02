#!/usr/bin/env python3
r"""
build.py — build the dependency-impact (reverse dependency) HTML.

Pure stdlib Python. No external dependencies.

The data comes from the platform's deletion-impact analysis: one
`deploy_impact {key, delete: true}` per target, polled with
`deploy_impact_status {analysis_id, kind: "deletion"}` to a terminal state.
The analysis is read-only; nothing is deleted.

Usage (fresh build — after the analyses):
    python3 build.py <cache-dir> <output-path> \
        --impact-dir     <dir>   \   # one <targetKey>.json per analysed target
        --tenant-assets  <path>  \   # tenant asset list (names / types);
                                     # repeat once per app_list page
        [--env-list      <path>] \   # env_list response, for environment names
        [--tenant-id     <id>]

Usage (cached re-render):
    python3 build.py <cache-dir> <output-path>

Per-target file (<impact-dir>/<targetKey>.json):
    {
      "targetKey": "<assetKey>",                 # required
      "launch":  <deploy_impact response, or the tool-error payload
                  {"error": "...", "data": {"code": "..."}}>,
      "result":  <last deploy_impact_status response>,   # absent if launch failed
      "resultFile": "<path>",                    # instead of "result": a file
                                                 # holding that response (e.g. the
                                                 # harness's auto-saved output);
                                                 # relative paths resolve against
                                                 # the record's directory
      "gaveUp":  "unknown-status" | "still-in-progress", # optional
      "harnessTruncated": true,                  # optional: the harness cut the
                                                 # status response (Codex)
      "skipped": "type-unsupported",             # optional: not launched because
      "probeError": {...}                        # a same-type probe was refused
    }

Verdict rules (never weaker than the server's):
    - Only `result.impactKnown == true` with a `report` is a verdict.
    - `impactKnown: false`, `processStatus` Failed / Unknown / InProgress,
      a missing result, or a failed launch => "impact unknown". Never
      rendered as "no dependents".
    - A launch refused with `analysis_launch_rejected` (or a type skipped
      after such a refusal) => "analysis not available for this asset".
    - `report.impactedAssets` is capped (200): the count shown is
      `report.total`, and "Showing N of M" whenever N < M.

Writes:
    <cache-dir>/impact-data.json
    <cache-dir>/meta.json
    <output-path>  - injected HTML

Template placeholder: /*__IMPACT_DATA__*/null
"""

from __future__ import annotations

import argparse
import json
import pathlib
import re
import shutil
import sys
import time


PLACEHOLDER = "/*__IMPACT_DATA__*/null"

LAUNCH_REJECTED = "analysis_launch_rejected"
LAUNCH_UNAVAILABLE = "analysis_launch_unavailable"

# Worst-first ordering for a dependent's severity across environments.
_SEVERITY_RANK = {"error": 3, "warning": 2, "info": 1}


def parse_args(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("cache_dir", type=pathlib.Path)
    p.add_argument("out_path",  type=pathlib.Path)
    p.add_argument("--impact-dir",    type=pathlib.Path, default=None)
    p.add_argument("--tenant-assets", type=pathlib.Path, action="append",
                   default=None)
    p.add_argument("--env-list",      type=pathlib.Path, default=None)
    p.add_argument("--tenant-id",     type=str,          default="")
    p.add_argument("--targets",       type=pathlib.Path, default=None,
                   help="targets.json of this run: render only these target keys "
                        "(other records stay cached for reuse)")
    return p.parse_args(argv[1:])


# Every skill in this family caches under one root, the "outsystems-skills"
# folder of the user's cache directory, in a folder per skill and per tenant
# (or app). `build.py --cache-dir <id>` creates and prints that folder, so the
# skill docs never spell out a home-folder path; `--skill <name>` prints a
# sibling skill's folder (for reading its cache, never for writing it).
CACHE_ROOT = pathlib.Path.home() / ".cache" / "outsystems-skills"
SKILL_NAME = "outsystems-dependency-impact"
_CACHE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9-]{0,127}$")
_SKILL_ID = re.compile(r"^outsystems-[a-z-]+$")


# The record folders `--cache-dir <id> --clear <name>` may start over: the
# skill never needs a shell `rm -rf`, which its allowed tools do not grant.
CLEARABLE = ("impact", "impact-named")
# `--wait <seconds>` bounds: a poll pause, never a way to stall the agent.
WAIT_RANGE = (1, 60)


def _cache_dir_command(argv) -> int:
    """`--cache-dir <id> [--skill <name> | --clear impact|impact-named]`:
    create and print the folder; with --clear, empty that record folder of
    this skill's cache first and print it (its raw/ subfolder recreated)."""
    skill = SKILL_NAME
    clear = None
    rest = list(argv)
    if len(rest) == 3 and rest[1] == "--skill":
        skill = rest.pop(2)
        rest.pop(1)
    elif len(rest) == 3 and rest[1] == "--clear" and rest[2] in CLEARABLE:
        clear = rest.pop(2)
        rest.pop(1)
    if len(rest) != 1 or not _CACHE_ID.match(rest[0]) or not _SKILL_ID.match(skill):
        print("usage: build.py --cache-dir <tenant-or-app-key> "
              "[--skill outsystems-<name> | --clear impact|impact-named]", file=sys.stderr)
        return 2
    path = CACHE_ROOT / skill / rest[0]
    if skill == SKILL_NAME:
        path.mkdir(parents=True, exist_ok=True)
        (path / "impact" / "raw").mkdir(parents=True, exist_ok=True)   # Step 1's record folder
    if clear:
        path = path / clear
        shutil.rmtree(path, ignore_errors=True)
        (path / "raw").mkdir(parents=True, exist_ok=True)
    print(path)
    return 0


def _wait_command(argv) -> int:
    """`--wait <seconds>`: the pause between status polls, so the skill
    needs no shell `sleep`. Run it in the background where the harness can."""
    try:
        seconds = int(argv[0]) if len(argv) == 1 else None
    except ValueError:
        seconds = None
    if seconds is None or not WAIT_RANGE[0] <= seconds <= WAIT_RANGE[1]:
        print(f"usage: build.py --wait <seconds, {WAIT_RANGE[0]}-{WAIT_RANGE[1]}>", file=sys.stderr)
        return 2
    time.sleep(seconds)
    print(f"waited {seconds}s")
    return 0



# Small read-only helpers, so the skill's steps run as this script (the one
# command its allowed-tools grant) instead of model-written `python3 -c`.
PEEK_MAX = 5000


def _cache_age_command(argv) -> int:
    """`--cache-age <folder>`: print that folder's meta.json and its age in
    seconds (from `fetched_at`, or `scanned_at` for dependency-impact)."""
    if len(argv) != 1:
        print("usage: build.py --cache-age <cache-folder>", file=sys.stderr)
        return 2
    meta_path = pathlib.Path(argv[0]) / "meta.json"
    try:
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        print(f"no cache: {meta_path} does not exist")
        return 0
    except (OSError, json.JSONDecodeError) as exc:
        print(f"unreadable cache: {meta_path}: {exc}")
        return 0
    stamp = meta.get("fetched_at", meta.get("scanned_at")) if isinstance(meta, dict) else None
    age = int(time.time()) - stamp if isinstance(stamp, int) and not isinstance(stamp, bool) else None
    print(json.dumps(meta, separators=(",", ":")))
    print(f"age_s={age if age is not None else 'unknown'}")
    return 0


def _peek_command(argv) -> int:
    """`--peek <path> [chars]`: print the start of a saved file, for a look
    at its shape without reading it into the conversation."""
    try:
        n = int(argv[1]) if len(argv) == 2 else 1000 if len(argv) == 1 else None
    except ValueError:
        n = None
    if n is None or not 1 <= n <= PEEK_MAX:
        print(f"usage: build.py --peek <path> [chars, 1-{PEEK_MAX}]", file=sys.stderr)
        return 2
    try:
        with open(argv[0], encoding="utf-8", errors="replace") as fh:
            print(fh.read(n))
    except OSError as exc:
        print(f"could not read {argv[0]}: {exc}", file=sys.stderr)
        return 1
    return 0


def _copy_command(argv) -> int:
    """`--copy <src> <dst>`: copy a harness-saved tool result into this
    skill's cache. The destination must be inside the skill's own cache
    folder, so this is never a general-purpose copy."""
    if len(argv) != 2:
        print("usage: build.py --copy <saved-file> <path inside this skill's cache>", file=sys.stderr)
        return 2
    src, dst = pathlib.Path(argv[0]), pathlib.Path(argv[1]).resolve()
    root = (CACHE_ROOT / SKILL_NAME).resolve()
    if root not in dst.parents:
        print(f"--copy only writes inside {root}", file=sys.stderr)
        return 2
    if not src.is_file():
        print(f"--copy: {src} is not a file", file=sys.stderr)
        return 1
    try:
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, dst)
    except OSError as exc:
        print(f"could not copy {src} to {dst}: {exc}", file=sys.stderr)
        return 1
    print(dst)
    return 0



# Producer types: the assets something else can depend on (Step 4).
PRODUCER_GROUPS = {
    "libraries":   ("LowCodeLibrary", "MobileLibrary", "ExtensionLibrary", "WidgetLibrary",
                    "ExternalLibrary"),
    "agents":      ("Agent",),
    "connections": ("AIModelConnection", "AINativeConnection", "ExternalConnection",
                    "MCPConnection", "SearchServiceConnection", "A2AConnection"),
}


def _select_targets_command(argv) -> int:
    """`--select-targets <targets.json> [--only libraries|agents|connections]
    <asset list file>...`: write the Branch D work list (key, name, type) of
    every producer in the asset list, and print the counts and names the
    pre-flight confirmation needs. The asset files are checked like a build's."""
    rest = list(argv)
    only = None
    if len(rest) >= 3 and rest[1] == "--only" and rest[2] in PRODUCER_GROUPS:
        only = rest.pop(2)
        rest.pop(1)
    if len(rest) < 2:
        print("usage: build.py --select-targets <targets.json> [--only libraries|agents|connections] "
              "<asset list file>...", file=sys.stderr)
        return 2
    out, sources = pathlib.Path(rest[0]), rest[1:]
    try:
        by_key = load_assets(sources)
    except IncompleteAssets as exc:
        print(f"INCOMPLETE: {exc}. Nothing was written.", file=sys.stderr)
        return 3
    except (OSError, KeyError, ValueError, json.JSONDecodeError) as exc:
        print(f"could not read the asset list: {exc}", file=sys.stderr)
        return 1
    groups = {g: types for g, types in PRODUCER_GROUPS.items() if only in (None, g)}
    picked = {g: sorted((a for a in by_key.values() if a.get("t") in types),
                        key=lambda a: (a.get("n") or "").lower())
              for g, types in groups.items()}
    rows = [{"key": a["k"], "name": a.get("n") or "", "type": a.get("t") or ""}
            for g in picked for a in picked[g]]
    try:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps({"targets": rows}, indent=1), encoding="utf-8")
    except OSError as exc:
        print(f"could not write {out}: {exc}", file=sys.stderr)
        return 1
    print(f"wrote {out}: {len(rows)} targets ("
          + ", ".join(f"{len(v)} {g}" for g, v in picked.items()) + ")")
    for g, v in picked.items():
        if v:
            print(f"  {g}: " + ", ".join(a.get("n") or a["k"] for a in v))
    return 0



# Branch D resume: a record younger than this is reused.
RECORD_TTL_S = 24 * 3600


def _pending_command(argv) -> int:
    """`--pending <impact-dir> <targets.json> [--rescan-failures]`: which
    targets of the work list Step 5 still has to analyse. A target is reused
    when its record (and result file) is under 24h old; with
    --rescan-failures, a fresh record without a verdict is analysed again."""
    rest = list(argv)
    rescan = "--rescan-failures" in rest
    rest = [a for a in rest if a != "--rescan-failures"]
    if len(rest) != 2:
        print("usage: build.py --pending <impact-dir> <targets.json> [--rescan-failures]", file=sys.stderr)
        return 2
    impact_dir, targets_path = pathlib.Path(rest[0]), pathlib.Path(rest[1])
    try:
        keys = load_target_keys(targets_path)
        raw = json.loads(targets_path.read_text(encoding="utf-8"))
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"could not read {targets_path}: {exc}", file=sys.stderr)
        return 1
    rows = raw.get("targets", raw.get("results", [])) if isinstance(raw, dict) else raw
    names = {r.get("key") or r.get("k"): r.get("name") or r.get("n") or ""
             for r in rows if isinstance(r, dict)}
    records = {}
    for path in sorted(impact_dir.glob("*.json")) if impact_dir.is_dir() else []:
        record, files = _read_record(path)
        records[record.get("targetKey") or path.stem] = (record, files)
    now = time.time()
    fresh, todo = [], []
    for key in sorted(keys, key=lambda k: (names.get(k) or k).lower()):
        record, files = records.get(key, (None, []))
        age_ok = bool(files) and all(now - f.stat().st_mtime < RECORD_TTL_S for f in files if f.exists())
        verdict = record is not None and classify_target(record, {}, {})["state"] != "unknown"
        if record is not None and age_ok and (verdict or not rescan):
            fresh.append(key)
        else:
            todo.append(key)
    print(f"reuse: {len(fresh)} target(s) with a record under 24h old"
          + ("" if rescan else " (with or without a verdict)"))
    print(f"analyse: {len(todo)} target(s)")
    for key in todo:
        print(f"{key}\t{names.get(key, '')}")
    return 0


def main(argv: list[str]) -> int:
    if len(argv) > 1 and argv[1] == "--cache-dir":
        return _cache_dir_command(argv[2:])
    if len(argv) > 1 and argv[1] == "--pending":
        return _pending_command(argv[2:])
    if len(argv) > 1 and argv[1] == "--select-targets":
        return _select_targets_command(argv[2:])
    if len(argv) > 1 and argv[1] == "--cache-age":
        return _cache_age_command(argv[2:])
    if len(argv) > 1 and argv[1] == "--peek":
        return _peek_command(argv[2:])
    if len(argv) > 1 and argv[1] == "--copy":
        return _copy_command(argv[2:])
    if len(argv) > 1 and argv[1] == "--wait":
        return _wait_command(argv[2:])
    args = parse_args(argv)
    skill_dir = pathlib.Path(__file__).resolve().parent.parent
    template_path = skill_dir / "assets" / "template.html"

    cache_dir = args.cache_dir.resolve()
    out_path  = args.out_path.resolve()
    cache_dir.mkdir(parents=True, exist_ok=True)

    fresh_mode = args.impact_dir is not None or args.tenant_assets is not None
    if fresh_mode:
        if args.impact_dir is None or args.tenant_assets is None:
            print("fresh mode requires --impact-dir and --tenant-assets",
                  file=sys.stderr)
            return 2
        try:
            bundle = build_bundle(args.impact_dir, args.tenant_assets,
                                  args.env_list, args.tenant_id,
                                  load_target_keys(args.targets))
        except IncompleteAssets as exc:
            print(f"INCOMPLETE: {exc}. Nothing was written to the cache.", file=sys.stderr)
            return 3
        except (FileNotFoundError, KeyError, ValueError, json.JSONDecodeError) as exc:
            print(f"build failed: {exc}", file=sys.stderr)
            return 1
        s = bundle["stats"]
        try:
            (cache_dir / "impact-data.json").write_text(
                json.dumps(bundle, separators=(",", ":")), encoding="utf-8")
            (cache_dir / "meta.json").write_text(json.dumps({
                "scanned_at":    bundle["tenant"]["scannedAt"],
                "target_count":  s["targetCount"],
                "known_count":   s["knownCount"],
                "unknown_count": s["unknownCount"],
                "refused_count": s["refusedCount"],
                "edge_count":    s["edgeCount"],
            }, separators=(",", ":")), encoding="utf-8")
        except OSError as exc:
            print(f"could not write the cache files in {cache_dir}: {exc}", file=sys.stderr)
            return 1

    data_path = cache_dir / "impact-data.json"
    if not data_path.exists():
        print(f"missing {data_path} — run fresh mode first", file=sys.stderr)
        return 1
    if not template_path.exists():
        print(f"template not found: {template_path}", file=sys.stderr)
        return 1

    html = template_path.read_text(encoding="utf-8")
    payload = data_path.read_text(encoding="utf-8").strip()
    try:
        b = json.loads(payload)
    except json.JSONDecodeError as exc:
        print(f"{data_path} not valid JSON: {exc}", file=sys.stderr)
        return 1
    stats = b.get("stats") if isinstance(b, dict) else None
    if not isinstance(stats, dict) or not isinstance(b.get("byTarget"), dict) or not all(
            isinstance(stats.get(f), int) for f in ("targetCount", "knownCount", "unknownCount",
                                                    "refusedCount", "edgeCount", "consumerCount")):
        print(f"STALE: {data_path} is not a bundle this build.py renders (written by an "
              f"older version, or edited); re-run fresh mode", file=sys.stderr)
        return 3
    if PLACEHOLDER not in html:
        print(f"placeholder {PLACEHOLDER!r} not in template", file=sys.stderr)
        return 1
    # The bundle lands inside a <script> element. `<` only occurs inside JSON
    # strings, where \u003c is the same character: escaping every one stops an
    # asset name or error text with "</script>" from closing the element and
    # one with "<!--<script" from putting the HTML parser into its
    # double-escaped script state (which blanks the page).
    html = html.replace(PLACEHOLDER, payload.replace("<", "\\u003c"), 1)

    try:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(html, encoding="utf-8")
    except OSError as exc:  # disk full, permission denied, a folder in the way
        print(f"could not write the output file {out_path}: {exc}", file=sys.stderr)
        return 1

    s = b["stats"]
    size_kb = out_path.stat().st_size / 1024
    print(f"wrote {out_path} ({size_kb:.1f} KB)")
    print(f"  targets: {s['targetCount']} analysed · {s['knownCount']} impact known · "
          f"{s['unknownCount']} impact unknown ({s['refusedCount']} not available"
          + (f", {s['missingCount']} with no saved record" if s.get("missingCount") else "") + ")")
    print(f"  dependents: {'at least ' if s.get('edgeCountIsLowerBound') else ''}"
          f"{s['edgeCount']} (sum of report totals) · "
          f"{s['consumerCount']} distinct consumer assets listed")
    return 0


# =====================================================================
# Build (fresh mode)
# =====================================================================

def load_target_keys(path):
    """The keys in a targets.json work list (a list of keys, of {key|k|assetKey}
    rows, or {targets: [...]}), or None when no list was given."""
    if path is None:
        return None
    raw = json.loads(pathlib.Path(path).read_text(encoding="utf-8"))
    if isinstance(raw, dict):
        raw = raw.get("targets", raw.get("results"))
    if not isinstance(raw, list):
        raise ValueError(f"--targets {path}: expected a list of target keys or rows")
    keys = set()
    for r in raw:
        k = r if isinstance(r, str) else next(
            (r.get(f) for f in ("key", "k", "assetKey", "targetKey") if isinstance(r, dict) and r.get(f)), None)
        if not isinstance(k, str):
            raise ValueError(f"--targets {path}: a row has no key: {str(r)[:80]}")
        keys.add(k)
    return keys


class IncompleteAssets(Exception):
    """The app_list pages passed stop before the listing's end (exit 3)."""


def _cut_listing(chain: dict) -> str:
    nxt = chain["next"] if isinstance(chain["next"], int) else chain["rows"]
    return (f"the asset list pages starting at {pathlib.Path(chain['path']).name} cover "
            f"{len(chain['keys'])} of {chain['total']} assets; call app_list with the same "
            f"arguments plus offset: {nxt}, save the response, and re-run passing each "
            f"listing's pages one after another, in offset order, to --tenant-assets")


def build_bundle(impact_dir: pathlib.Path, tenant_assets_paths,
                 env_list_path: pathlib.Path | None, tenant_id: str,
                 target_keys=None) -> dict:
    by_key = load_assets(tenant_assets_paths)
    env_names = load_env_names(env_list_path)

    impact_dir = impact_dir.resolve()
    if not impact_dir.is_dir():
        raise FileNotFoundError(f"--impact-dir is not a directory: {impact_dir}")
    return _build_from_records(impact_dir, by_key, env_names, tenant_id, target_keys)


def load_assets(tenant_assets_paths) -> dict:
    """The asset list by key, from every --tenant-assets file, with each
    app_list listing checked as a whole page chain (IncompleteAssets)."""
    if isinstance(tenant_assets_paths, (str, pathlib.Path)):
        tenant_assets_paths = [tenant_assets_paths]
    by_key: dict[str, dict] = {}
    # A truncated app_list page needs its later pages: without them targets
    # would be missing from the map without a word. Pages carry no offset or
    # query echo, so each listing's pages must be passed one after another:
    # a truncated page opens a chain that only its continuation (same total)
    # may extend, and the chain must reach that total on a page that is not
    # truncated. Two searches with equal totals never count as one listing.
    chain = None   # {"path", "total", "keys", "next"} while a listing is open
    for path in tenant_assets_paths:
        tenant = _unwrap_tool_result(json.loads(pathlib.Path(path).read_text(encoding="utf-8")))
        rows = normalize_tenant_assets(tenant)
        for a in rows:
            by_key[a["k"]] = a
        paged = (isinstance(tenant, dict) and isinstance(tenant.get("results"), list)
                 and isinstance(tenant.get("total"), int))
        if (isinstance(tenant, dict) and tenant.get("truncated") is True
                and not isinstance(tenant.get("total"), int)):
            # Truncated with no total: nothing can say when the listing ends.
            raise IncompleteAssets(
                f"{pathlib.Path(path).name} is a truncated app_list page with no `total`, so "
                f"its listing cannot be checked; save the app_list responses verbatim "
                f"(envelope included) and pass every page")
        if chain is not None and (not paged or tenant["total"] != chain["total"]):
            raise IncompleteAssets(_cut_listing(chain))
        if not paged:
            continue
        if chain is None and tenant.get("truncated") is True:
            chain = {"path": path, "total": tenant["total"], "keys": set(), "rows": 0, "next": None}
        if chain is None:
            # A whole listing in one page carries all of its total. One that
            # carries fewer is a later page passed without its first.
            if len(rows) < tenant["total"]:
                raise IncompleteAssets(
                    f"{pathlib.Path(path).name} holds {len(rows)} of {tenant['total']} assets but is "
                    f"not truncated: it is a later page of a listing whose earlier pages were "
                    f"not passed; pass every page of that listing from offset 0, in order")
            continue
        chain["keys"].update(a["k"] for a in rows)
        chain["rows"] += len(rows)
        chain["next"] = tenant.get("next_offset")
        # One listing's pages add up to its total exactly; more rows than
        # that means another listing's page was taken as the continuation.
        if chain["rows"] > chain["total"]:
            raise IncompleteAssets(_cut_listing(chain))
        if tenant.get("truncated") is not True:
            if chain["rows"] < chain["total"] or len(chain["keys"]) < chain["rows"]:
                raise IncompleteAssets(_cut_listing(chain))
            chain = None
    if chain is not None:
        raise IncompleteAssets(_cut_listing(chain))
    return by_key


def _read_record(path: pathlib.Path) -> tuple[dict, list[pathlib.Path]]:
    """One target's record, with its launch / result unwrapped and its
    resultFile read, plus the files it came from. An unreadable record is a
    `badRecord` (that target unknown); it never stops a build."""
    try:
        record = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        record = None
    if not isinstance(record, dict):
        return {"targetKey": path.stem, "badRecord": True}, [path]
    files = [path]
    # A launch or result saved as the whole MCP result is unwrapped, the
    # same as a resultFile.
    for part in ("launch", "result"):
        if part in record:
            record[part] = _unwrap_tool_result(record[part])
    if "result" not in record and record.get("resultFile"):
        rf = pathlib.Path(record["resultFile"]).expanduser()
        if not rf.is_absolute():
            rf = path.parent / rf
        # A missing or unreadable file leaves no result: impact unknown.
        try:
            record["result"] = _unwrap_tool_result(json.loads(rf.read_text(encoding="utf-8")))
            files.append(rf)
        except (OSError, json.JSONDecodeError):
            pass
    return record, files


def _build_from_records(impact_dir, by_key, env_names, tenant_id, target_keys) -> dict:
    by_target: dict[str, dict] = {}
    used: list[pathlib.Path] = []   # the record (and result) files this report reads
    for path in sorted(impact_dir.glob("*.json")):
        record, files = _read_record(path)
        if target_keys is not None and (record.get("targetKey") or path.stem) not in target_keys:
            continue   # cached from another run's scope: kept on disk, not shown
        used += files
        key = record.get("targetKey") or path.stem
        meta = by_key.get(key, {})
        by_target[key] = classify_target(record, meta, env_names)

    # A target of this run with no record file (the run stopped before it, or
    # its launch was never saved) is unknown, never left out: otherwise the
    # totals would understate the scope the user asked about.
    missing = sorted((target_keys or set()) - set(by_target))
    for key in missing:
        by_target[key] = classify_target({"targetKey": key, "noRecord": True},
                                         by_key.get(key, {}), env_names)

    known = [t for t in by_target.values() if t["state"] == "known"]
    refused = [t for t in by_target.values() if t["state"] == "refused"]
    consumers = {u["k"] for t in known for u in t["users"] if u.get("k")}
    # Dated by the oldest record it shows, not by the build: records reused
    # from the 24-hour cache must not read as freshly scanned.
    stamps = [p.stat().st_mtime for p in used if p.exists()]
    return {
        "tenant": {"id": tenant_id or "", "scannedAt": int(min(stamps)) if stamps else int(time.time())},
        "stats": {
            "targetCount":   len(by_target),
            "knownCount":    len(known),
            "unknownCount":  len(by_target) - len(known),
            "refusedCount":  len(refused),
            "edgeCount":     sum(t["total"] for t in known),
            # True when a known target's count is only the rows that arrived.
            "edgeCountIsLowerBound": any(t.get("totalKnown") is False for t in known),
            "consumerCount": len(consumers),
            "missingCount":  len(missing),   # targets with no record: counted as unknown
        },
        "byTarget": by_target,
    }


def classify_target(record: dict, meta: dict, env_names: dict) -> dict:
    """One target's verdict. Anything short of a recognised verdict is
    'unknown' (or 'refused'), never an empty dependents list."""
    type_name = meta.get("t") or record.get("targetType") or "?"
    base = {
        "n": meta.get("n") or record.get("targetName") or record.get("targetKey") or "?",
        "kind": type_name,
        "currentRev": meta.get("r"),
        "analysisKey": None,
        "processStatus": None,
        "reportStatus": None,
        "total": 0,
        "shown": 0,
        "truncated": False,
        "users": [],
    }

    if record.get("badRecord"):
        return {**base, "state": "unknown",
                "summary": "Impact unknown: this target's record file is not a JSON "
                           "object (it was cut or edited). Re-run the analysis for it. "
                           "This is not the same as 'no dependents'."}

    if record.get("noRecord"):
        return {**base, "state": "unknown",
                "summary": "Impact unknown: no analysis record was saved for this "
                           "target (the run stopped before it, or its launch was "
                           "not saved). Re-run to analyse it. This is not the same "
                           "as 'no dependents'."}

    if record.get("skipped") == "type-unsupported":
        why = error_text(record.get("probeError")) or "the platform refused it"
        return {**base, "state": "refused",
                "summary": f"Deletion analysis not available for this asset type "
                           f"({type_name}): the platform refused the same analysis "
                           f"for another {type_name} asset ({why}). Dependents "
                           f"unknown, not 'no dependents'."}

    launch = record.get("launch")
    launch = launch if isinstance(launch, dict) else {}
    code, message = launch_error(launch) if launch else ("", "")
    if code or message:
        if code == LAUNCH_REJECTED:
            return {**base, "state": "refused",
                    "summary": f"Deletion analysis not available for this asset "
                               f"({type_name}): the platform refused it "
                               f"({code}: {message}). Dependents unknown, not "
                               f"'no dependents'."}
        retry = " Worth retrying later." if code == LAUNCH_UNAVAILABLE else ""
        return {**base, "state": "unknown",
                "summary": f"Impact unknown: the analysis could not be started "
                           f"({code or 'error'}: {message}).{retry} This is not "
                           f"the same as 'no dependents'."}

    base["analysisKey"] = launch.get("analysisKey")
    result = record.get("result")
    # A status saved for another analysis or asset (batched polls paired with
    # the wrong record) must not publish someone else's dependents here.
    if isinstance(result, dict):
        target = record.get("targetKey")
        if not base["analysisKey"]:
            return {**base, "state": "unknown",
                    "summary": "Impact unknown: a status was saved without the launch "
                               "record (its analysisKey) to pair it with, so it cannot be "
                               "trusted for this target. Re-run the analysis. This is not "
                               "the same as 'no dependents'."}
        if result.get("analysisKey") != base["analysisKey"]:
            return {**base, "state": "unknown",
                    "summary": f"Impact unknown: the saved status is for analysis "
                               f"{result.get('analysisKey') or '(none named)'}, not this "
                               f"target's {base['analysisKey']}. Re-poll this target. This is "
                               f"not the same as 'no dependents'."}
        if target and result.get("assetKey") and result["assetKey"] != target:
            return {**base, "state": "unknown",
                    "summary": f"Impact unknown: the saved status is for asset "
                               f"{result['assetKey']}, not this target. Re-poll this target. "
                               f"This is not the same as 'no dependents'."}
    if not isinstance(result, dict):
        return {**base, "state": "unknown",
                "summary": "Impact unknown: the analysis was started but never "
                           "polled to a result. This is not the same as "
                           "'no dependents'."}

    status = result.get("processStatus")
    base["processStatus"] = status
    report = result.get("report")
    if result.get("impactKnown") is not True or not isinstance(report, dict):
        return {**base, "state": "unknown",
                "summary": unknown_reason(status, result, record.get("gaveUp"))}

    rows = [normalize_row(r, env_names) for r in (report.get("impactedAssets") or [])
            if isinstance(r, dict)]
    rows.sort(key=lambda u: (-u["rank"], u["n"].lower()))
    total_seen = isinstance(report.get("total"), int)
    total = report["total"] if total_seen and report["total"] >= len(rows) else len(rows)
    truncated = bool(report.get("truncated")) or len(rows) < total
    harness_cut = bool(record.get("harnessTruncated"))
    report_status = report.get("status") or "?"

    # The count is report.total. Without it (a cut response, or a server that
    # left it out) the rows that arrived are a floor, never proof of zero.
    if not total_seen and not rows:
        return {**base, "state": "unknown", "reportStatus": report_status,
                "summary": ("Impact unknown: the report arrived without its total "
                            "and without rows" + (" (the harness cut the response)"
                                                  if harness_cut else "") +
                            ". This is not the same as 'no dependents'.")}
    if not total_seen:
        # No total at all, with or without a truncation hint: the rows that
        # arrived are a floor, never an exact count.
        return {**base, "state": "known", "reportStatus": report_status,
                "total": len(rows), "totalKnown": False,
                "shown": len(rows), "truncated": True, "users": rows,
                "summary": (f"At least {len(rows)} dependent{'' if len(rows) == 1 else 's'} "
                            f"({report_status}); the "
                            f"total was not visible. The full list is in the ODC "
                            f"Portal's impact analysis view.")}

    if total == 0:
        summary = (f"No dependents: the platform's deletion analysis found none "
                   f"({report_status}).")
    elif truncated or harness_cut:
        why = ("the harness cut the response" if harness_cut and len(rows) < total
               else "the list is capped")
        summary = (f"Showing {len(rows)} of {total} dependents ({report_status}); "
                   f"{why}. The full list is in the ODC Portal's impact "
                   f"analysis view.")
    else:
        summary = f"{total} dependent{'' if total == 1 else 's'} ({report_status})."

    return {**base, "state": "known", "reportStatus": report_status,
            "total": total, "totalKnown": True,
            "shown": len(rows), "truncated": truncated or harness_cut,
            "users": rows, "summary": summary}


def unknown_reason(status, result: dict, gave_up) -> str:
    tail = " This is not the same as 'no dependents'."
    if status == "Failed":
        err = error_text(result.get("error")) or "no reason given"
        return f"Impact unknown: the analysis failed ({err}).{tail}"
    if status == "Finished":
        return ("Impact unknown: the analysis finished without a verdict the "
                f"server recognises (impactKnown: false).{tail}")
    if status == "InProgress" or gave_up == "still-in-progress":
        return ("Impact unknown: the analysis was still in progress when polling "
                f"stopped; it continues server-side, re-run to read it.{tail}")
    if status == "Unknown" or gave_up == "unknown-status":
        return ("Impact unknown: the platform returned a status this server does "
                f"not recognise (processStatus: Unknown).{tail}")
    return f"Impact unknown (processStatus: {status or 'missing'}).{tail}"


def normalize_row(row: dict, env_names: dict) -> dict:
    envs = []
    worst = ""
    worst_rank = 0
    indirect = False
    for d in row.get("deployedRevisions") or []:
        if not isinstance(d, dict):
            continue
        sev = d.get("severity") or ""
        rank = _SEVERITY_RANK.get(str(sev).lower(), 0)
        if rank > worst_rank:
            worst, worst_rank = sev, rank
        env_key = d.get("environmentKey") or ""
        envs.append({
            "e":  env_key,
            "en": env_names.get(env_key) or (env_key[:8] + "…" if env_key else "?"),
            "r":  d.get("revision"),
            "s":  sev,
            "c":  d.get("consumerType") or "",
        })
        if d.get("indirectDependencies"):
            indirect = True
    return {
        "k":    row.get("assetKey") or row.get("applicationKey") or "",
        "n":    row.get("name") or "?",
        "t":    row.get("type") or "?",
        "sev":  worst,
        "rank": worst_rank,
        "envs": envs,
        "indirect": indirect,
    }


def launch_error(launch: dict) -> tuple[str, str]:
    """(code, message) when the deploy_impact call itself failed."""
    if not isinstance(launch, dict):
        return "", ""
    if launch.get("analysisKey") and not launch.get("isError"):
        return "", ""
    data = launch.get("data") if isinstance(launch.get("data"), dict) else {}
    code = data.get("code") or launch.get("code") or ""
    message = error_text(launch.get("error")) or launch.get("message") or ""
    if not (code or message) and not launch.get("analysisKey"):
        message = "no analysisKey in the deploy_impact response"
    return str(code), str(message)


def error_text(err) -> str:
    if err is None:
        return ""
    if isinstance(err, str):
        return err
    if isinstance(err, dict):
        for k in ("message", "detail", "error", "title"):
            if isinstance(err.get(k), str) and err[k]:
                return err[k]
    return json.dumps(err, separators=(",", ":"))[:300]


def _unwrap_tool_result(page):
    """Accept a raw payload, an MCP `{structuredContent}` / `{content: [...]}`
    result, or a bare content-block list (the form Claude Code saves when a
    result has no structuredContent). An `isError` result is returned as-is
    so it is still recognised as an error. Anything else is returned as-is."""
    if isinstance(page, dict) and page.get("isError") is True:
        return page
    if isinstance(page, dict) and not any(k in page for k in ("results", "data", "references", "report")):
        if isinstance(page.get("structuredContent"), dict):
            return page["structuredContent"]
        if isinstance(page.get("content"), list):
            page = page["content"]
    if isinstance(page, list) and page and all(isinstance(b, dict) for b in page) \
            and all(b.get("type") for b in page):
        texts = [b.get("text") for b in page if b.get("type") == "text"]
        if len(texts) == 1 and isinstance(texts[0], str):
            try:
                return json.loads(texts[0])
            except json.JSONDecodeError:
                pass
    return page


def normalize_tenant_assets(raw) -> list[dict]:
    """Accept the tenant-architecture bundle (tenant-data.json), its compact
    asset list, or a raw app_list page."""
    raw = _unwrap_tool_result(raw)
    if isinstance(raw, list):
        # A compact list ({k, n, t, ...}) as is; a list of raw app_list rows
        # (several searches merged by hand) is converted like a page.
        if raw and all(isinstance(a, dict) and "k" not in a and "assetKey" in a for a in raw):
            raw = {"results": raw}
        else:
            return raw
    if isinstance(raw, dict) and isinstance(raw.get("assets"), list) and "schema" in raw:
        return raw["assets"]
    if isinstance(raw, dict) and "results" in raw:
        return [{
            "k": a["assetKey"],
            "n": a.get("name") or "",
            "t": a.get("assetType") or "",
            "r": a.get("revision"),
            "d": (a.get("revisionDateTime") or "")[:10],
            "x": bool(a.get("isExternal", False)),
        } for a in raw["results"]]
    raise ValueError("--tenant-assets must be a list, {results: [...]} or a tenant-data.json bundle")


def load_env_names(path: pathlib.Path | None) -> dict:
    if path is None or not path.exists():
        return {}
    raw = json.loads(path.read_text(encoding="utf-8"))
    rows = raw.get("results", []) if isinstance(raw, dict) else raw
    return {e["key"]: e.get("name") or e["key"] for e in rows
            if isinstance(e, dict) and e.get("key")}


if __name__ == "__main__":
    sys.exit(main(sys.argv))
