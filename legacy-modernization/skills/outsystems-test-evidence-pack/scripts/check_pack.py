#!/usr/bin/env python3
"""A Test Evidence Pack is ready to ship: its ids are the spec's and its tests say what they prove.

Checks, mechanically, before the pack is run for the report or handed over:

* `requirements/requirements.json` lists each requirement once, by id, with its text;
  with `--requirements`, its ids and texts are exactly the extractor's, so the pack
  can't renumber, respell, drop or reword one;
* every screen a requirement names is in the `screens` map, and every `untestable`
  reason is a sentence, not a flag;
* every test carries exactly one test id of its own (`testId('TEST-007')`, a `TEST-`
  and three or more digits), and no two tests share one; a malformed one (`TEST-7`,
  `test-007`) fails. Requirement ids stay the extractor's: a requirement id in the
  `TEST-` family fails, since a tag couldn't tell the two apart;
* every tag on a test is a requirement id, matched exactly as spelled, `ACCESS` or the
  test's id; a respelling (`REQ-01`, `req-001`) is named with the id it should be, and any other
  tag (`@Access`, `@REQ-ABC`, `@smoke`) fails. The literal tags in the source are
  always read. The tags built at runtime (`req(v.id)` in a loop) come from
  `evidence/tests.json`, which `npm run list` writes from Playwright's own test list;
  when it is older than any test file or the config, the check fails rather than
  trust it. Without it the run says the runtime tags weren't counted;
* no `test.only` or `describe.only` is left in, which would run one test and pass;
* every requirement in a required tier (by default `functional`, and any requirement
  without a tier) has a test or an `untestable` reason. Other tiers, such as the
  business rules, are reported but may stay Not covered;
* every test names at least one step in Given / When / Then form (the `given` /
  `when` / `then` helpers, or `test.step('Given ...')`), because the evidence page
  reads them;
* at least one test is tagged `@ACCESS`, the signed-out check every pack carries;
* no `TODO(pack)` line is left in the README or `.env.example`.

It then prints, for each tier, how many requirements have a test, how many are
marked untestable, and how many are not covered yet, and the test id the next new
test takes. With `evidence/tests.json` the test ids are read from it, one per test
Playwright lists (a test declared in a loop is several); without it, from each
declaration in the source, and a `testId(...)` built at runtime isn't counted.

Usage:

    npm run list        # in the pack, after npm ci
    python3 check_pack.py <pack-dir> [--requirements <extractor requirements.json>]
                          [--require-tier functional ...]

Exit 1 on any failure. Standard library only, Python 3.8+.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import OrderedDict
from pathlib import Path
from typing import Dict, Iterable, List, Set, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent))
from scaffold_pack import TODO, extractor_requirements  # noqa: E402

DASHES = "-‐‑‒–—―−"
# A test declaration: test('title', ...), test.only / fixme / fail / slow / skip('title', ...).
# test.skip(condition, 'reason') inside a body isn't one: its first argument isn't a string.
DECLARATION = re.compile(r"(?m)^[ \t]*test(?:\.(?:only|fixme|fail|slow|skip))?\(\s*['\"`]")
STEP = re.compile(r"\b(?:given|when|then)\(\s*['\"`]|\btest\.step\(\s*['\"`](?:Given|When|Then)\b")
REQ_CALL = re.compile(r"\breq\(([^)]*)\)")
TEST_ID_CALL = re.compile(r"\btestId\(([^)]*)\)")
# A test's own id, as tests/support.ts's testId() writes it (TEST_ID there).
TEST_ID = re.compile(r"^TEST-[0-9]{3,}$")
TEST_FAMILY = "TEST"
STRING = re.compile(r"'([^'\\\n]*)'|\"([^\"\\\n]*)\"|`([^`\\\n]*)`")
TAG_LIST = re.compile(r"\btag\s*:\s*(\[[^\]]*\]|['\"`][^'\"`\n]*['\"`])")
ACCESS = "ACCESS"
ONLY = re.compile(r"\b(?:test|describe)(?:\.describe)?\.only\(")
REQUIRED_TIERS = ("functional",)
# A string or a comment; a comment is blanked before any tag is read (see uncommented).
COMMENT_OR_STRING = re.compile(r"""('(?:[^'\\\n]|\\.)*'|"(?:[^"\\\n]|\\.)*"|`(?:[^`\\]|\\.)*`)|//[^\n]*|/\*.*?\*/""", re.S)


def key(token: str) -> Tuple[str, ...]:
    """What two spellings of one id share: `REQ-01`, `req‑1` and `REQ-001` all give (REQ, 1)."""
    parts = re.split("[" + DASHES + r"_.\s]+", token.strip().upper())
    return tuple(str(int(p)) if p.isdigit() else p for p in parts if p)


def strings(text: str) -> Iterable[str]:
    for m in STRING.finditer(text):
        yield next(g for g in m.groups() if g is not None)


def literal(argument: str) -> str:
    """The id a `testId(...)` argument names, when the whole argument is one plain string; "" otherwise.

    `testId('TEST-' + String(i))`, `testId(id)` and `` testId(`TEST-${n}`) `` are built at runtime, so
    their id is only known once Playwright lists the test.
    """
    m = STRING.fullmatch(argument.strip())
    found = next((g for g in m.groups() if g is not None), "") if m else ""
    return "" if "${" in found else found


def uncommented(source: str) -> str:
    """The source with every comment blanked, newlines kept, so a tag in `// TODO req('REQ-002')` or a
    commented-out test is no coverage and line numbers still hold. Strings are kept as they are."""
    return COMMENT_OR_STRING.sub(lambda m: m.group(1) or re.sub(r"[^\n]", " ", m.group(0)), source)


def is_test_family(tag: str) -> bool:
    """A tag that reads as a test id, well formed or not: `TEST-007`, `TEST-7`, `test-007`."""
    return key(tag)[:1] == (TEST_FAMILY,) or bool(re.match(r"(?i)test[0-9]", tag))


def tags_in(source: str) -> List[Tuple[int, str]]:
    """Every requirement tag and test id a spec file uses, with its line, as spelled (no leading @).

    A `testId(...)` built at runtime (anything but one plain string) is left to evidence/tests.json.
    """
    found = []
    for m in REQ_CALL.finditer(source):
        line = source.count("\n", 0, m.start()) + 1
        found += [(line, s) for s in strings(m.group(1))]
    for m in TEST_ID_CALL.finditer(source):
        line = source.count("\n", 0, m.start()) + 1
        found += [(line, literal(m.group(1)))] if literal(m.group(1)) else []
    for m in TAG_LIST.finditer(source):
        line = source.count("\n", 0, m.start()) + 1
        found += [(line, s[1:]) for s in strings(m.group(1)) if s.startswith("@")]
        # support.ts exports the access tag as a constant, so it's an identifier here, not a string.
        if re.search(r"(?<![\w'\"`@])ACCESS\b", m.group(1)):
            found.append((line, ACCESS))
    return found


def declarations(source: str) -> List[Tuple[int, str]]:
    """Each test declaration's line and text, up to the next declaration."""
    starts = [m.start() for m in DECLARATION.finditer(source)]
    return [(source.count("\n", 0, start) + 1, source[start:starts[i + 1] if i + 1 < len(starts) else len(source)])
            for i, start in enumerate(starts)]


def tests_without_steps(source: str) -> List[int]:
    """Lines of the test declarations whose body names no Given / When / Then step."""
    return [line for line, body in declarations(source) if not STEP.search(body)]


def declared_test_ids(source: str) -> List[Tuple[int, List[str], bool]]:
    """Per declaration: its line, the literal test ids it names, and whether it builds one at runtime."""
    out = []
    for line, body in declarations(source):
        ids = [tag for _, tag in tags_in(body) if is_test_family(tag)]
        # testId(id), testId(`TEST-${n}`) or testId('TEST-' + n): only known once Playwright lists the test.
        runtime = any(not literal(m.group(1)) for m in TEST_ID_CALL.finditer(body))
        out.append((line, ids, runtime))
    return out


def test_id_problems(tests: List[Tuple[str, List[str], bool]]) -> Tuple[List[str], List[str]]:
    """FAIL lines for tests with no test id, two of them or one another test has; and the well-formed ids.

    `tests` holds (where, ids named, built at runtime) per test. A malformed id is reported with the tags.
    """
    fails = []  # type: List[str]
    owner = OrderedDict()  # type: Dict[str, str]
    for where, ids, runtime in tests:
        good = [i for i in ids if TEST_ID.match(i)]
        if not ids and not runtime:
            fails.append("{}: the test has no test id; give it one: {{ tag: [testId('TEST-nnn'), ...] }}".format(where))
        elif len(set(ids)) > 1:
            fails.append("{}: the test has {} test ids ({}); give it one".format(where, len(set(ids)), ", ".join(ids)))
        for i in dict.fromkeys(good):
            # Two tests in different describe blocks can share a file, line and title, so a shared id
            # fails even when the two read the same.
            if i in owner:
                fails.append("{}: test id {} is already {}'s; give this test the next free one".format(
                    where, i, "another test at the same place" if owner[i] == where else owner[i]))
            owner.setdefault(i, where)
    return fails, list(owner)


def next_test_id(ids: Iterable[str]) -> str:
    """The id a new test takes: one more than the highest in the pack, TEST-001 in an empty one."""
    highest = max((int(i.split("-", 1)[1]) for i in ids if TEST_ID.match(i)), default=0)
    return "TEST-{:03d}".format(highest + 1)


def listed_tests(pack: Path) -> List[Tuple[str, List[str]]]:
    """(where, tags) for every test in evidence/tests.json; ValueError when the file is malformed."""
    try:
        tests = json.loads((pack / "evidence" / "tests.json").read_text(encoding="utf-8"))
        return [("tests/{}:{} `{}`".format(t["file"], t["line"], t["title"]), [str(tag) for tag in t["tags"]])
                for t in tests]
    except (ValueError, KeyError, TypeError) as exc:
        raise ValueError("evidence/tests.json can't be read ({}); run `npm run list` again".format(exc))


def listed_tags(pack: Path) -> List[Tuple[str, str]]:
    """(where, tag) for every tag in evidence/tests.json; ValueError when the file is malformed."""
    return [(where.split(" `", 1)[0], tag) for where, tags in listed_tests(pack) for tag in tags]


def stale_list(pack: Path) -> str:
    """The newest test or config file evidence/tests.json is older than, or "" when it's current."""
    listed = (pack / "evidence" / "tests.json").stat().st_mtime
    inputs = [pack / "playwright.config.ts"] + sorted((pack / "tests").rglob("*.ts"))
    newer = [f for f in inputs if f.is_file() and f.stat().st_mtime > listed]
    return newer[0].relative_to(pack).as_posix() if newer else ""


def check(pack: Path, extractor: Path = None, required_tiers: Iterable[str] = REQUIRED_TIERS
          ) -> Tuple[List[str], Dict[str, object]]:
    fails = []  # type: List[str]
    path = pack / "requirements" / "requirements.json"
    try:
        spec = json.loads(path.read_text(encoding="utf-8-sig"))
        rows = spec["requirements"]
        screens = spec.get("screens", {})
        assert isinstance(rows, list) and isinstance(screens, dict)
    except (OSError, ValueError, KeyError, TypeError, AssertionError) as exc:
        return ["requirements/requirements.json can't be read as a pack's requirements ({})".format(exc)], {}

    ids = []  # type: List[str]
    known = set()  # type: Set[str]
    for index, row in enumerate(rows):
        rid = row.get("id") if isinstance(row, dict) else None
        if not isinstance(rid, str) or not rid.strip():
            fails.append("requirements.json: requirement {} has no id".format(index + 1))
            continue
        if rid in ids:
            fails.append("requirements.json: {} is listed twice".format(rid))
        ids.append(rid)
        known.add(rid)
        known.update(m for m in row.get("merged", []) if isinstance(m, str))
        for sid in row.get("screens", []):
            if sid not in screens:
                fails.append("requirements.json: {} names screen {}, which isn't in the `screens` map".format(rid, sid))
        for reserved in [rid] + [m for m in row.get("merged", []) if isinstance(m, str)]:
            if is_test_family(reserved):
                fails.append("requirements.json: {}{} is in the TEST- family test ids use; a tag couldn't tell "
                             "the two apart".format(rid, "" if reserved == rid else " merges " + reserved))
        reason = row.get("untestable")
        if reason is not None and (not isinstance(reason, str) or len(reason.split()) < 3):
            fails.append("requirements.json: {} `untestable` must say why, in a sentence".format(rid))
    for sid, screen in screens.items():
        if not isinstance(screen, dict) or not screen.get("name") or "route" not in screen:
            fails.append("requirements.json: screen {} needs a `name` and a `route` (null when not built)".format(sid))

    if extractor is not None:
        try:
            source = extractor_requirements(extractor)
        except ValueError as exc:
            fails.append(str(exc))
            source = []
        source_ids = [r["id"] for r in source]
        missing = [i for i in source_ids if i not in ids]
        extra = [i for i in ids if i not in source_ids]
        if missing:
            fails.append("ids the extraction has and the pack doesn't: " + ", ".join(missing))
        if extra:
            fails.append("ids the pack has and the extraction doesn't: " + ", ".join(extra))
        texts = {r["id"]: r.get("text") for r in rows if isinstance(r, dict)}
        for r in source:
            if r["id"] in texts and texts[r["id"]] != r["text"]:
                fails.append("{}: its text differs from the extraction's; keep it unchanged".format(r["id"]))

    by_key = {}  # type: Dict[Tuple[str, ...], str]
    for i in known:
        by_key.setdefault(key(i), i)
    specs = sorted((pack / "tests").rglob("*.spec.ts")) if (pack / "tests").is_dir() else []
    if not specs:
        fails.append("tests/ holds no *.spec.ts files")
    sources = {f.relative_to(pack).as_posix(): uncommented(f.read_text(encoding="utf-8")) for f in specs}
    for name, text in sources.items():
        for line in tests_without_steps(text):
            fails.append("{}:{}: the test names no Given / When / Then step".format(name, line))
        for m in ONLY.finditer(text):
            fails.append("{}:{}: {} runs only this test; remove it".format(
                name, text.count("\n", 0, m.start()) + 1, m.group(0)[:-1]))

    # A pack scaffolded before test ids: `--update` never rewrites its helpers or scripts, so say which to copy.
    # Each marker is only in the new file: the old build-matrix.mjs already said `testId` (an HTML report link).
    stale = [name for name, marker in (("tests/support.ts", "export function testId"),
                                       ("scripts/build-matrix.mjs", "TEST_ID"), ("scripts/run.mjs", "TEST-"))
             if (pack / name).is_file() and marker not in (pack / name).read_text(encoding="utf-8")]
    if stale:
        fails.append("{} predate{} test ids; copy {} from the skill's template/, then give each test its id".format(
            ", ".join(stale), "s" if len(stale) == 1 else "", "it" if len(stale) == 1 else "them"))

    tags = [("{}:{}".format(name, line), tag) for name, text in sources.items() for line, tag in tags_in(text)]
    listed = (pack / "evidence" / "tests.json").is_file()
    per_test = None  # type: object
    if listed:
        newer = stale_list(pack)
        if newer:
            fails.append("evidence/tests.json is older than {}; run `npm run list` again".format(newer))
        try:
            per_test = [(where, [t for t in test_tags if is_test_family(t)], False)
                        for where, test_tags in listed_tests(pack)]
            tags += listed_tags(pack)
        except ValueError as exc:
            fails.append(str(exc))
    if per_test is None:
        # Without Playwright's own list, one test per declaration; an id built at runtime is not counted.
        per_test = [("{}:{}".format(name, line), ids, runtime)
                    for name, text in sources.items() for line, ids, runtime in declared_test_ids(text)]
    id_fails, test_ids = test_id_problems(per_test)  # type: ignore[arg-type]
    fails += id_fails
    tagged = set()  # type: Set[str]
    has_access = False
    reported = set()  # type: Set[str]
    for where, tag in tags:
        if tag == ACCESS:
            has_access = True
        elif TEST_ID.match(tag) and tag not in known:
            continue
        elif tag in known:
            tagged.add(tag)
        elif tag in reported:
            continue
        elif is_test_family(tag):
            fails.append("{}: test id {} is malformed; a test id is TEST- and three or more digits (TEST-007)".format(
                where, tag))
        elif key(tag) in by_key:
            fails.append("{}: tag {} is a respelling of {}; use the id exactly".format(where, tag, by_key[key(tag)]))
        else:
            fails.append("{}: tag {} isn't a requirement id in requirements.json, or ACCESS".format(where, tag))
        reported.add(tag)
    if specs and not has_access:
        fails.append("no test is tagged @ACCESS: every pack checks what a signed-out visitor is offered")

    for doc in ("README.md", ".env.example"):
        p = pack / doc
        if p.is_file():
            for n, text in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
                if TODO in text:
                    fails.append("{}:{}: still says {}".format(doc, n, TODO))

    required = set(required_tiers)
    tiers = OrderedDict()  # type: Dict[str, Dict[str, int]]
    missing = []  # type: List[str]
    for row in rows:
        if not isinstance(row, dict) or "id" not in row:
            continue
        tier = row.get("tier") or "untiered"
        t = tiers.setdefault(tier, {"total": 0, "covered": 0, "untestable": 0, "not_covered": 0})
        t["total"] += 1
        if {row["id"], *row.get("merged", [])} & tagged:
            t["covered"] += 1
        elif row.get("untestable"):
            t["untestable"] += 1
        else:
            t["not_covered"] += 1
            if tier in required or tier == "untiered":
                missing.append(row["id"])
    if missing and specs:
        fails.append("{} required requirement{} with no test and no `untestable` reason: {}".format(
            len(missing), "" if len(missing) == 1 else "s", ", ".join(missing)))
    counts = {"tiers": tiers, "listed": int(listed), "test_ids": len(test_ids), "next_test_id": next_test_id(test_ids),
              # Ids a loop builds at runtime are only known from evidence/tests.json, so the next id may be taken.
              "runtime_ids": int(any(runtime for _where, _ids, runtime in per_test)),  # type: ignore[union-attr]
              "covered": sum(t["covered"] for t in tiers.values()),
              "untestable": sum(t["untestable"] for t in tiers.values()),
              "not_covered": sum(t["not_covered"] for t in tiers.values()), "total": len(ids)}
    return fails, counts


def main(argv: List[str] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("pack", type=Path)
    parser.add_argument("--requirements", type=Path, help="the extractor's requirements.json to match")
    parser.add_argument("--require-tier", action="append", dest="tiers", metavar="TIER",
                        help="a tier whose every requirement needs a test or an untestable reason "
                             "(default: functional; repeat for more)")
    args = parser.parse_args(argv)
    fails, counts = check(args.pack, args.requirements, args.tiers or REQUIRED_TIERS)
    for f in fails:
        print("FAIL " + f)
    if counts and not counts["listed"]:
        print("NOTE tags were read from the source only, so tags built at runtime aren't counted; "
              "run `npm run list` in the pack for the full set.")
    for tier, t in counts.get("tiers", {}).items():
        print("{}: {covered} of {total} have a test, {untestable} are marked untestable, "
              "{not_covered} are not covered yet.".format(tier, **t))
    if counts:
        print("Test ids: {} test{} named; a new test takes {}.".format(
            counts["test_ids"], "" if counts["test_ids"] == 1 else "s", counts["next_test_id"]))
        if counts["runtime_ids"]:
            print("NOTE a test builds its id at runtime and evidence/tests.json is missing, so {} may already be "
                  "taken; run `npm run list` in the pack and check again before using it.".format(
                      counts["next_test_id"]))
    if fails:
        print("{} problem{}.".format(len(fails), "" if len(fails) == 1 else "s"))
        return 1
    print("OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
