#!/usr/bin/env python3
"""Lay out a Test Evidence Pack for one app, from the extractor's requirements.json.

The pack is a Playwright project shipped beside the generated app: tests tagged with
the requirement they prove, a traceability matrix built from each run, and an HTML
report with a trace and screenshots per test. This writes everything but the
tests, which the tester writes from the flows it drives:

* the template (config, helpers, matrix builder, handover script, README), with the app's
  name and URL filled in;
* `requirements/requirements.json`: every extractor requirement, with its id and text
  unchanged, plus an empty `screens` list for the tester to fill. That file is the
  coverage denominator: a requirement no test is tagged with shows as Not covered.

Re-running it on an existing pack (`--update`) refreshes the requirements from a new
extraction. It keeps the app's name, the `screens` and `untestable` the tester added
and the `screens` map, and never touches `tests/`. Ids the new extraction dropped are
listed.

Usage:

    python3 scaffold_pack.py <requirements.json> <out-dir> --app-name "Order Desk"
        --base-url https://tenant.outsystems.app/OrderDesk
        [--sample NAME=VALUE ...] [--locale en-GB] [--timezone Europe/London]
    python3 scaffold_pack.py <requirements.json> <out-dir> --update
    python3 scaffold_pack.py --no-requirements <out-dir> --app-name "Order Desk" --base-url ...

Exit 1 when the requirements can't be read, the pack exists and --update isn't set,
or --update finds no pack (or one whose requirements.json can't be read).
Standard library only, Python 3.8+.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from pathlib import Path
from typing import Dict, List, Tuple

TEMPLATE = Path(__file__).resolve().parent.parent / "template"
SCHEMA = "test-evidence-pack/requirements@1"
# Lines the tester must replace before the pack ships; check_pack.py fails while any remain.
TODO = "TODO(pack)"
SAMPLE_NAME = re.compile(r"^[A-Z][A-Z0-9_]*$")


def extractor_requirements(path: Path) -> List[dict]:
    """The extractor's requirement rows, in order, one per id. ValueError with a readable reason."""
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeDecodeError, ValueError) as exc:
        raise ValueError("{}: can't be read as JSON ({})".format(path.name, exc))
    if isinstance(data, list):
        rows = data
    elif isinstance(data, dict) and isinstance(data.get("requirements"), list):
        rows = data["requirements"]
    elif isinstance(data, dict) and isinstance(data.get("by_tier"), dict):
        rows = [r for tier in data["by_tier"].values() if isinstance(tier, list) for r in tier]
    else:
        raise ValueError("{}: expected a list of requirements, a `requirements` list or a `by_tier` mapping".format(
            path.name))
    seen = {}  # type: Dict[str, dict]
    for index, row in enumerate(rows):
        if not isinstance(row, dict) or not isinstance(row.get("id"), str) or not row["id"].strip():
            raise ValueError("{}: requirement {} has no `id` string".format(path.name, index + 1))
        if not isinstance(row.get("text"), str) or not row["text"].strip():
            raise ValueError("{}: requirement {} has no `text`".format(path.name, row["id"]))
        seen.setdefault(row["id"], row)
    if not seen:
        raise ValueError("{}: lists no requirements".format(path.name))
    return list(seen.values())


def merge(fresh: List[dict], existing: dict) -> Tuple[List[dict], List[str]]:
    """Fresh extractor rows, carrying over what the tester added to the old ones; and the dropped ids."""
    old = {r["id"]: r for r in existing.get("requirements", []) if isinstance(r, dict) and "id" in r}
    out = []
    for row in fresh:
        entry = dict(row)
        kept = old.get(row["id"], {})
        entry["screens"] = kept.get("screens", row.get("screens", []))
        if kept.get("untestable"):
            entry["untestable"] = kept["untestable"]
        out.append(entry)
    dropped = [i for i in old if i not in {r["id"] for r in fresh}]
    return out, dropped


def fill(text: str, values: Dict[str, str], suffix: str = "") -> str:
    """The template with each `{{KEY}}` replaced, escaped for the file it lands in.

    A `.json` file gets a JSON string body, a `.ts`/`.js` file a single-quoted JavaScript string
    body, so an app name like `Orders "EU"` or `O'Brien` still makes a valid package.json and config.
    """
    for key, value in values.items():
        if suffix == ".json":
            value = json.dumps(value, ensure_ascii=False)[1:-1]
        elif suffix in (".ts", ".js", ".mjs"):
            value = (value.replace("\\", "\\\\").replace("'", "\\'")
                     .replace("\n", "\\n").replace("\r", "\\r"))
        text = text.replace("{{" + key + "}}", value)
    return text


def package_name(app_name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", app_name.lower()).strip("-")
    return (slug or "app") + "-test-evidence-pack"


def parse_samples(pairs: List[str]) -> List[Tuple[str, str]]:
    samples = []
    for pair in pairs:
        name, sep, value = pair.partition("=")
        if not sep or not SAMPLE_NAME.match(name):
            raise ValueError("--sample takes NAME=VALUE with an upper-case NAME, got {!r}".format(pair))
        samples.append((name, value))
    return samples


def write_lf(path: Path, text: str) -> None:
    """Write with LF line endings on every OS. Path.write_text has no `newline` before 3.10."""
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)


def main(argv: List[str] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("requirements", type=Path, nargs="?", help="the extractor's requirements.json")
    parser.add_argument("out", type=Path, help="the pack directory to create")
    parser.add_argument("--app-name", help="required for a new pack; --update keeps the pack's own")
    parser.add_argument("--base-url", help="the deployed app's root URL; required for a new pack")
    parser.add_argument("--sample", action="append", default=[], metavar="NAME=VALUE",
                        help="a named sample record the tests read as SAMPLE_<NAME>")
    parser.add_argument("--locale", default="en-GB")
    parser.add_argument("--timezone", default="Europe/London")
    parser.add_argument("--update", action="store_true", help="refresh an existing pack's requirements")
    parser.add_argument("--no-requirements", action="store_true",
                        help="start a pack with no requirements yet, for screen tests during a build "
                             "with no extraction; a later --update adds them")
    args = parser.parse_args(argv)
    if (args.requirements is None) != args.no_requirements:
        print("FAIL pass the extractor's requirements.json, or --no-requirements (not both)", file=sys.stderr)
        return 1
    if args.no_requirements and args.update:
        # Merging no requirements over a pack would drop every one it holds.
        print("FAIL --update needs the extractor's requirements.json; --no-requirements only starts a new pack",
              file=sys.stderr)
        return 1

    try:
        fresh = [] if args.no_requirements else extractor_requirements(args.requirements)
        samples = parse_samples(args.sample)
    except ValueError as exc:
        print("FAIL " + str(exc), file=sys.stderr)
        return 1

    out = args.out
    target = out / "requirements" / "requirements.json"
    if target.exists() and not args.update:
        print("FAIL {} already holds a pack; pass --update to refresh its requirements".format(out), file=sys.stderr)
        return 1
    if args.update and not target.exists():
        print("FAIL {} holds no pack to update; leave out --update to create one".format(out), file=sys.stderr)
        return 1
    if not args.update and not (args.app_name and args.base_url):
        print("FAIL a new pack needs --app-name and --base-url", file=sys.stderr)
        return 1

    app_name = args.app_name
    if args.update:
        try:
            existing = json.loads(target.read_text(encoding="utf-8-sig"))
            if not isinstance(existing, dict) or not isinstance(existing.get("requirements"), list):
                raise ValueError("it has no `requirements` list")
        except (OSError, UnicodeDecodeError, ValueError) as exc:
            print("FAIL {} can't be read as a pack's requirements ({}); fix or remove it first".format(
                target, exc), file=sys.stderr)
            return 1
        rows, dropped = merge(fresh, existing)
        screens = existing.get("screens", {})
        # The pack's name is set once, when it is created; an update never renames it.
        app_name = existing.get("app") or app_name
    else:
        rows, dropped = merge(fresh, {})
        screens = {}
        base = args.base_url.rstrip("/")
        values = {
            "APP_NAME": args.app_name,
            "PACKAGE_NAME": package_name(args.app_name),
            "BASE_URL": base,
            "LOCALE": args.locale,
            "TIMEZONE": args.timezone,
            "EXAMPLE_ID": fresh[0]["id"] if fresh else "REQ-001",
            "SAMPLES": "\n".join("SAMPLE_{}={}".format(n, v) for n, v in samples) or "# (none yet)",
            "SAMPLE_ROWS": "\n".join("| `SAMPLE_{}` | {} One {} record the tests rely on. |".format(n, TODO, n.lower())
                                     for n, _ in samples),
            "SEED_DATA": "{} Name the records the tests read, and what each must look like.".format(TODO),
        }
        for source in sorted(TEMPLATE.rglob("*")):
            if source.is_dir() or "__pycache__" in source.parts:
                continue
            # A Markdown template keeps a `.template` suffix in the skill, so the skill's own
            # pointer check doesn't read the pack's paths as resources it should bundle.
            dest = out / source.relative_to(TEMPLATE)
            if dest.suffix == ".template":
                dest = dest.with_suffix("")
            dest.parent.mkdir(parents=True, exist_ok=True)
            try:
                text = source.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                shutil.copyfile(source, dest)
                continue
            filled = fill(text, values, dest.suffix)
            write_lf(dest, filled)

    target.parent.mkdir(parents=True, exist_ok=True)
    pack = {
        "schema": SCHEMA,
        "app": app_name,
        "source": "{} ({} requirements)".format(args.requirements.name if args.requirements else "none yet", len(rows)),
        "requirements": rows,
        "screens": screens,
    }
    write_lf(target, json.dumps(pack, indent=2, ensure_ascii=False) + "\n")

    print("{} {}: {} requirements".format("Updated" if args.update else "Created", out, len(rows)))
    if dropped:
        print("  no longer in the extraction (their tests now show under Other checks): " + ", ".join(dropped))
    return 0


if __name__ == "__main__":
    sys.exit(main())
