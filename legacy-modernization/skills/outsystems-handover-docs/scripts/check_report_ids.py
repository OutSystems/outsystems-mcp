#!/usr/bin/env python3
"""The Implementation Report cites the spec's requirement ids, unchanged.

The extraction writes one id per requirement into `requirements.json`
(`REQ-001`, `BR-418`, `RULE-012`, `NFR-03`, ...), and the Business Spec uses the
same ids. A reader holds the report beside the spec and looks each id up, so an
id the report renumbers (`REQ-01`), respells (`REQ‑001` with a non-ASCII dash)
or drops can no longer be checked against the spec.

This compares the two, mechanically:

* every spec id has exactly one row in section 5 (the requirements list, one
  table), a row in appendix A (traceability) and a row in appendix Z (the
  requirements checklist, the report's last section);
* section 5's requirements table numbers its rows in a `Req ID` column,
  `REQ-00001`, `REQ-00002`, ... in row order with no gap, gives each row a
  `Type` (functional requirement, business rule, non-functional, ...), and
  cites the spec id in a `Source id` column; with `--spec`, its rows are the
  Business Brief's section-5 rows one for one, in the same order, with the same
  Req ID, Type and Source id;
* every id a section-5, appendix-A or appendix-Z row cites is a spec id or a
  report-local `IN-nn` id; under section 5's Additions subsection only ids the
  spec doesn't have are allowed;
* every section-5 and appendix-Z row has a plain-English Description cell;
* each appendix-Z row's Implemented / Tested answer matches its section-5
  status and verdict, and the `Implemented: X of N` / `Tested: Y of M` totals
  line matches the rows;
* no section-5 row merges two ids (an appendix-A row may trace several), and no
  id anywhere in the report is a respelling of a family spec id (`REQ-001`); a
  native id that isn't in the spec fails where a row cites it.

Spec ids keep whatever prefix the extraction gives them (`REQ-001`,
`PMODEL-ORD100-0001`, `MSACCESS-RULE-0007`) and are matched as whole tokens,
exactly as spelled. An id listed under an entry's `merged` was folded into that
entry: the entry's row covers it, and a row may cite either or both.

Usage:

    python3 check_report_ids.py <requirements.json> <report.md> [--business-spec <Customer>-Business-Spec.md]
                                [--spec <business-brief.md> ...] [--matrix <pack>/evidence/summary.json]
                                [--figure]

`--business-spec` adds the ids the extractor's Business Spec numbers in its
section 5 table but `requirements.json` doesn't carry (some stacks number their
rules only there); they are spec ids like any other and need the same rows. For
an application split into business domains, pass the overview
(`<Customer>-Business-Spec.md`, whose section 5 and `Requirements to confirm`
table list every requirement) and each `domains/*/<...>-Business-Spec.md`. An overview
from an extraction older than those tables numbers nothing: pass only the domain specs.
Passed beside them anyway, it is skipped with a note in the OK line.

`--spec` passes the Business Brief. Its section 5 is numbered the same way
(checked too), and the report's section 5 must list exactly its rows, in its
order; a brief with no section-5 requirements table fails rather than passing
unmapped. It also adds the re-derived capability ids (`CAP-nn`) the brief defines
beyond `requirements.json`, so the report may cite them too. It admits no other
family: the reporter writes the brief and the report in the same turn, so a
brief must not be able to legitimise an id the spec doesn't have.

`--matrix` adds the Test Evidence Pack's run: its `evidence/summary.json`, the
full run (not a subset). Its matrix must have exactly one row per spec entry,
each section-5 row must link its matrix row (`traceability-matrix.html#req-<id>`)
as its evidence, and no section-5 Tested cell may contradict the run: PASS where
the run says Fail, Flaky, Blocked or Not covered, or FAIL where it says Pass.
It also checks the pack's test ids (`TEST-007`, one per test): every test in the
run has one; each section-5 row cites, beside its evidence, the id of every test
the run tags with that requirement and no test the run doesn't tag with it; and
no test id anywhere in the report is missing from the run or respelled
(`TEST-07`).

`--figure` also prints the report's requirements figure once every check
passes: `REQS IMPLEMENTED X of N (P%)`, the spec ids (every id requirements.json
and the Business Specs number) whose appendix-Z row answers Implemented Yes, over
every spec id. Report-local `IN-nn` and `CAP-nn` rows count in appendix Z's
totals line but not here. P is rounded DOWN to one decimal, so a figure below a
threshold never prints as reaching it. It is the number the page-1
`**P% REQs implemented** X of N` card shows (the check fails when that card says
otherwise), and the one the workflow's validator gate reads from the intermediate
Implementation Report (`implemented_figure`), so the gate and the report can't
disagree.

Exit 1 on any mismatch, or with one FAIL line when an input file can't be
read. Standard library only, Python 3.8+.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Set, Tuple

# The id families the extraction writes into requirements.json, plus the
# report-local IN- ids for an input without ids.
FAMILIES = ("REQ", "US", "FR", "CAP", "BR", "RULE", "NFR")
# Any dash-like character between prefix and number, or (for a known family
# written in capitals or title case) a space or nothing: a respelled id
# (`REQ‑001`, `Req 1`, `REQ001`) still has to be found to be flagged.
DASHES = "-‐‑‒–—―−"
# An id starts and ends where the token does: `MSACCESS-RULE-0002`, `REQ-001-v2`, `REQ-001a` and
# `PMODEL-ORD100-0001.v2` are other tokens, never `RULE-0002`, `REQ-001` or `PMODEL-ORD100-0001`.
# A dash or dot before or after the id still counts as punctuation when no word character follows it.
LEFT = r"(?<![" + DASHES + r"\w])(?<!\w\.)"
RIGHT = r"(?!\w)(?![" + DASHES + r".]\w)"
# A family id may follow a number and a dash, so a range (`REQ-01–REQ-02`) still shows both ends.
ANY_ID = re.compile(r"(?<!\w)(?<![A-Za-z][" + DASHES + r"])(?<!\w\.)([A-Za-z]{2,6})([" + DASHES + r"]| ?)([0-9]{1,4})"
                    + RIGHT)
LOCAL_ID = re.compile(r"^IN-[0-9]{2,}$")
# The running number of a section-5 requirements row: REQ-00001, REQ-00002, ...
REQ_NUMBER = "REQ-{:05d}"
# A Test Evidence Pack test's own id (the pack's testId()), as the report cites it; and any spelling of one.
TEST_ID = re.compile(r"^TEST-[0-9]{3,}$")
# Whole tokens only, like a spec id: `TEST-001-v2` and `TEST-001.extra` are other tokens, never `TEST-001`.
TEST_TOKEN = re.compile(LEFT + r"(TEST|test|Test)([" + DASHES + r"]| ?)([0-9]+)" + RIGHT)
# A Business Spec id outside the families above (`PMODEL-ORD100-0001`): one token with a digit.
SPEC_TOKEN = re.compile(r"^[A-Za-z][A-Za-z0-9]*(?:[-_.][A-Za-z0-9]+)+$")
# The appendix-Z answer each section-5 status and verdict maps to.
IMPLEMENTED = {"implemented, tested": "yes", "implemented, not tested": "yes", "changed": "yes",
               "partial": "partial", "deferred": "no", "not built": "no"}
TESTED = {"pass": "yes", "partial": "partial", "fail": "no", "not tested": "no", "not observable": "n/a"}
# Appendix Z's totals line: `Implemented: X of N. Tested: Y of M.`
TOTALS = re.compile(r"\bImplemented:\s*([0-9]+) of ([0-9]+)\W+Tested:\s*([0-9]+) of ([0-9]+)", re.I)
# The page-1 KPI card the requirements figure is shown on: `- **66% REQs implemented** 53 of 80 ...`.
REQS_CARD = re.compile(r"^\s*[-*+]\s+\*\*\s*~?([0-9]+(?:\.[0-9]+)?)\s*%\s*REQs implemented\s*\*\*(.*)$", re.I)
CARD_COUNT = re.compile(r"\b([0-9]+)\s*(?:of|/)\s*([0-9]+)\b")
Z_TITLE = re.compile(r"^(?:appendix\s+)?Z(?:[.):]|\s|$)", re.I)
FENCE = re.compile(r"^ {0,3}(`{3,}|~{3,})(.*)$")
HEADING = re.compile(r"^(#{1,6})\s+(.*?)\s*#*\s*$")
SEPARATOR_ROW = re.compile(r"^\|?\s*:?-{2,}:?\s*(\|\s*:?-{2,}:?\s*)*\|?\s*$")
PIPE = re.compile(r"(?<!\\)\|")
# Addresses keep their own spelling and are not citations: a link's target
# (`](#req-001)`), a URL, an in-page anchor, or a file name (`shots/req-002.png`).
ADDRESS = re.compile(
    r"\]\([^)]*\)"
    r"|\b[A-Za-z][A-Za-z0-9+.-]*://\S+"
    r"|(?<![\w&])#[\w-]+"
    r"|[\w./-]*\.(?:png|jpe?g|gif|svg|webp|pdf|md|html?|json|csv|xlsx?|txt|docx?)\b",
    re.I,
)


def canonical(prefix: str, number: str) -> Tuple[str, int]:
    """The key two spellings of one id share: `REQ-01`, `req‑1` and `REQ-001` all match."""
    return prefix.upper(), int(number)


def find_ids(text: str) -> List[Tuple[str, Tuple[str, int]]]:
    """Every id-shaped token in `text`, as spelled, with its canonical key.

    Without a dash, only a known family in capitals or title case counts, so
    "for us 2 regions" or "item 3" is not an id.
    """
    found = []
    text = ADDRESS.sub(" ", text)
    # Markdown escapes (`REQ\\-001`) render as the plain character, so they spell the same id.
    for m in ANY_ID.finditer(plain(text)):
        prefix, sep, number = m.groups()
        if not sep or sep == " ":
            if prefix.upper() not in FAMILIES or not (prefix.isupper() or prefix.istitle()):
                continue
        found.append((m.group(0), canonical(prefix, number)))
    return found


def read(path: Path) -> str:
    """A text input, BOM-tolerant; ValueError, with a readable reason, when it can't be read."""
    try:
        return path.read_text(encoding="utf-8-sig")
    except (OSError, UnicodeDecodeError) as exc:
        raise ValueError("{}: can't be read ({})".format(path.name, exc.strerror if isinstance(exc, OSError) else exc))


def spec_ids(requirements_path: Path) -> Tuple[List[str], Dict[str, str]]:
    """The spec's ids in order, and each folded (`merged`) id -> the id of the entry it folded into.

    ValueError, with a readable reason, when the file can't be used.
    """
    text = read(requirements_path)
    try:
        data = json.loads(text)
    except ValueError as exc:
        raise ValueError("{}: can't be read as JSON ({})".format(requirements_path.name, exc))
    name = requirements_path.name
    if isinstance(data, list):
        rows = data  # a bare list of requirement objects, as the extractor's reader also accepts
    elif isinstance(data, dict) and "requirements" in data:
        rows = data["requirements"]
    elif isinstance(data, dict) and isinstance(data.get("by_tier"), dict) and all(
            isinstance(tier, list) for tier in data["by_tier"].values()):
        rows = [r for tier in data["by_tier"].values() for r in tier]
    else:
        raise ValueError("{}: expected a list of requirement objects, a `requirements` list or a `by_tier` "
                         "mapping of lists".format(name))
    if not isinstance(rows, list):
        raise ValueError("{}: `requirements` is a {}, not a list of requirement objects".format(
            name, type(rows).__name__))
    for index, row in enumerate(rows):
        if not isinstance(row, dict) or not isinstance(row.get("id"), str) or not row["id"].strip():
            raise ValueError("{}: requirement {} has no `id` string".format(name, index + 1))
        merged = row.get("merged", [])
        if not isinstance(merged, list) or not all(isinstance(m, str) and m.strip() for m in merged):
            raise ValueError("{}: requirement {} has a `merged` that is not a list of id strings".format(
                name, row["id"]))
    ids = list(dict.fromkeys(row["id"] for row in rows))
    if not ids:
        # Certifying a report against nothing would read as a pass.
        raise ValueError("{}: lists no requirement ids, so there is nothing to check the report against".format(name))
    parent_of = {m: row["id"] for row in rows for m in row.get("merged", []) if m not in ids}
    return ids, parent_of


def defined_in(markdown: str) -> List[Tuple[str, Tuple[str, int]]]:
    """Ids a spec markdown file names in a known family, as spelled there, with their keys."""
    found = {}  # type: Dict[str, Tuple[str, int]]
    for line in strip_fences(markdown.splitlines()):
        for token, key in find_ids(line):
            if key[0] in FAMILIES:
                found.setdefault(token, key)
    return list(found.items())


def strip_fences(lines: Iterable[str]) -> List[str]:
    """Blank every line inside a fenced code block, keeping line numbers.

    A fence closes only on the opener's character, at least as long, with
    nothing after it, so a ```` block can show a ``` example (CommonMark).
    """
    out, opener = [], None  # type: List[str], Optional[str]
    for line in lines:
        m = FENCE.match(line)
        if opener is None:
            if m:
                opener = m.group(1)
            out.append("" if m else line)
            continue
        if m and m.group(1)[0] == opener[0] and len(m.group(1)) >= len(opener) and not m.group(2).strip():
            opener = None
        out.append("")
    return out


def cells(row: str) -> List[str]:
    row = row.strip()
    if row.startswith("|"):
        row = row[1:]
    if row.endswith("|"):
        row = row[:-1]
    return [c.strip() for c in re.split(r"(?<!\\)\|", row)]


def table_rows(lines: List[str]) -> Tuple[Dict[int, int], Dict[int, List[str]], Dict[int, int]]:
    """Line number -> table number for every GFM table body row, with or without leading pipes,
    table number -> its lower-cased header cells, and separator line number -> table number.

    A table starts at a header line with a pipe followed by a separator row, and
    runs until a line without an unescaped pipe.
    """
    rows = {}  # type: Dict[int, int]
    headers = {}  # type: Dict[int, List[str]]
    separators = {}  # type: Dict[int, int]
    inside, table = False, 0
    for no, line in enumerate(lines, 1):
        text = line.strip()
        if inside and PIPE.search(text) and not HEADING.match(text):
            rows[no] = table
            continue
        inside = (no >= 2 and PIPE.search(text) is not None and SEPARATOR_ROW.match(text) is not None
                  and PIPE.search(lines[no - 2].strip()) is not None)
        table += inside
        if inside:
            headers[table] = [visible(c).lower() for c in cells(lines[no - 2])]
            separators[no] = table
    return rows, headers, separators


def column(header: List[str], name: str) -> Optional[int]:
    """The index of the first header cell that starts with `name`, or None."""
    return next((i for i, h in enumerate(header) if re.sub(r"[`*_]", "", h).startswith(name)), None)


def plain(cell: str) -> str:
    """A cell as it renders: no emphasis or code marks, no inline HTML (a status badge), no escapes.

    Underscore emphasis (`_x_`, `__x__`) goes only where it opens and closes at a word's edge, so
    an underscore inside an id (`INV_LINE_CHK`, `ORD_CHK`) stays.
    """
    text = re.sub(r"(?<!\w)(__?)(?=\S)(.+?)(?<=\S)\1(?!\w)", r"\2", re.sub(r"[`*]|<[^>]*>", "", cell))
    return re.sub(r"\\(.)", r"\1", text).strip()


def visible(cell: str) -> str:
    """The text a reader sees in a cell: a link's label without its target, as rendered."""
    return re.sub(r"[\[\]]", " ", plain(ADDRESS.sub(" ", cell))).strip()


def ids_in_cell(cell: str) -> List[str]:
    return [token for token, _ in find_ids(cell)]


class Row:
    def __init__(self, line_no: int, ids: List[str], addition: bool, table: int, row_cells: List[str]) -> None:
        self.line_no = line_no
        self.ids = ids
        self.addition = addition
        self.table = table
        self.cells = row_cells
        self.first = row_cells[0]
        self.id_index = 0

    def cell(self, index: Optional[int]) -> str:
        """A cell as the reader sees it: a link counts by its label, never by its target."""
        return visible(self.cells[index]) if index is not None and index < len(self.cells) else ""


def id_column(header: List[str]) -> int:
    """The cell that cites the spec id: `Source id` in a table numbered by a `Req ID` column, else the first."""
    if column(header, "req id") is not None:
        source = column(header, "source id")
        if source is not None:
            return source
    return 0


def section_rows(lines: List[str], section: str, body_rows: Dict[int, int],
                 headers: Optional[Dict[int, List[str]]] = None) -> Optional[List[Row]]:
    """Table body rows of a `##` section whose number is `section`, or None when the section is absent.

    Each row carries the ids its id cell names (the first cell, or the `Source id` cell of a table
    numbered by a `Req ID` column; none for an unnumbered row) and its table; rows under a `###`
    heading that mentions "Addition" are flagged as additions.
    """
    rows = []  # type: List[Row]
    found, inside = False, False
    addition_level = 0  # the level of the open Additions heading, 0 when none is open
    pattern = re.compile(r"^(?:appendix\s+|section\s+)?" + re.escape(section) + r"(?:[.):]|\s|$)", re.I)
    for no, line in enumerate(lines, 1):
        h = HEADING.match(line)
        if h:
            level, title = len(h.group(1)), h.group(2).strip()
            if level <= 2:
                inside = level == 2 and bool(pattern.match(title))
                found = found or inside
                addition_level = 0
            elif inside and (not addition_level or level <= addition_level):
                # A heading nested under Additions stays inside it; a sibling or parent ends it.
                addition_level = level if "addition" in title.lower() else 0
            continue
        if not inside or no not in body_rows:
            continue
        row_cells = cells(line)
        index = id_column((headers or {}).get(body_rows[no], []))
        row = Row(no, [], bool(addition_level), body_rows[no], row_cells)
        row.id_index = index
        row.first = row_cells[index] if index < len(row_cells) else ""
        row.ids = ids_in_cell(visible(row.first))
        rows.append(row)
    return rows if found else None


def is_spec_token(text: str) -> bool:
    """A native id shape (`PMODEL-ORD100-0001`, `MSACCESS-RULE-0007`): one token with a digit."""
    return bool(SPEC_TOKEN.match(text)) and re.search(r"[0-9]", text) is not None


def to_confirm_rows(lines: List[str], body_rows: Dict[int, int]) -> List[Row]:
    """Table body rows under a `Requirements to confirm` heading (any level), up to the next heading at or above it."""
    rows = []  # type: List[Row]
    level = 0  # the level of the open heading, 0 when none is open
    for no, line in enumerate(lines, 1):
        h = HEADING.match(line)
        if h:
            if level and len(h.group(1)) > level:
                continue
            # A section number or bold/code marks may sit before the words (`### 9.1 **Requirements to confirm**`).
            title = re.sub(r"^[\d.\s*_`]+", "", h.group(2)).lower()
            level = len(h.group(1)) if title.startswith("requirements to confirm") else 0
        elif level and no in body_rows:
            row_cells = cells(line)
            rows.append(Row(no, [], False, body_rows[no], row_cells))
    return rows


def requirement_tables(lines: List[str], body_rows: Dict[int, int]) -> Set[int]:
    """Numbers of the tables whose nearest heading above them mentions requirements."""
    found, title = set(), ""  # type: Set[int], str
    for no, line in enumerate(lines, 1):
        h = HEADING.match(line)
        if h:
            title = h.group(2).lower()
        elif no in body_rows and "requirement" in title:
            found.add(body_rows[no])
    return found


def business_spec_ids(path: Path, requirements: Path, split: bool = False) -> Optional[List[str]]:
    """The ids the first cell of an extractor Business Spec's `| ID | ...` requirement table rows names, in order.

    Those tables are section 5's and, on a split application's overview, the `Requirements to confirm`
    one that lists the requirements no domain can claim yet. None for a split application's overview
    (`split`: domain specs were passed too) with no ID table under a requirements heading or with a
    Domains column: one written
    before the extractor added those tables numbers nothing (another ID table, a glossary say, doesn't
    change that), and its domain specs carry the ids. ValueError when
    the file isn't one: a Business Brief (it would turn the reporter's own ids into spec ids), a file
    outside the spec collection, or any other file with neither table.
    """
    home = requirements.resolve().parent
    where = path.resolve().parent
    if path.name.lower().endswith("-business-brief.md"):
        raise ValueError("{}: is a Business Brief, not the extractor's Business Spec; pass it with --spec".format(
            path.name))
    if where != home and where.parent != home / "domains":
        raise ValueError("{}: is not in the spec collection beside {} (or under its domains/), so it isn't the "
                         "extractor's Business Spec".format(path.name, requirements.name))
    lines = strip_fences(read(path).splitlines())
    body_rows, headers, separators = table_rows(lines)
    id_tables = {table for table, header in headers.items()
                 if header and re.sub(r"[`*_]", "", header[0]).strip() == "id"}
    rows = [row for row in (section_rows(lines, "5", body_rows) or []) + to_confirm_rows(lines, body_rows)
            if row.table in id_tables]
    headed = {row.table for row in (section_rows(lines, "5", separators) or []) + to_confirm_rows(lines, separators)}
    if not rows and id_tables & headed:
        # A header-only ID table under the right heading: nothing left to confirm, so zero ids.
        return []
    if not rows:
        # An older overview may hold other ID tables (a glossary); only an ID table under a heading about
        # requirements, or one with the to-confirm table's Domains column, is a current overview whose
        # heading drifted, and that still fails.
        current = id_tables & requirement_tables(lines, body_rows) or any(
            column(headers[table], "domains") is not None for table in id_tables)
        overview = where == home and (home / "domains").is_dir()
        if split and overview and not current:
            return None
        # A flat spec, a domain spec, and a drifted heading have no other file to pass instead.
        if id_tables and not (overview and not current):
            raise ValueError("{}: has an ID table that is not under a section-5 or Requirements to confirm "
                             "heading; fix the heading".format(path.name))
        # An older overview passed without its domain specs is the one case with a file to pass instead.
        advice = "; pass each domains/*/ Business Spec" if overview else ""
        raise ValueError("{}: has no section-5 or Requirements to confirm table headed ID, so it numbers no "
                         "requirements{}".format(path.name, advice))
    return list(dict.fromkeys(visible(row.first) for row in rows if is_spec_token(visible(row.first))))


def last_section(lines: List[str]) -> str:
    """The title of the report's last `#`/`##` heading."""
    titles = [h.group(2) for h in map(HEADING.match, lines) if h and len(h.group(1)) <= 2]
    return titles[-1] if titles else ""


def figure_pct(done: int, total: int) -> float:
    """`done` of `total` as a percentage rounded DOWN to one decimal: 189 of 199 is 94.9, never 95."""
    return (1000 * done // total) / 10 if total else 0.0


def check(requirements: Path, report: Path, specs: Iterable[Path] = (),
          business_specs: Iterable[Path] = (), matrix: Optional[Path] = None) -> Tuple[List[str], str]:
    problems, summary, _ = _check(requirements, report, specs, business_specs, matrix)
    return problems, summary


def _check(requirements: Path, report: Path, specs: Iterable[Path] = (), business_specs: Iterable[Path] = (),
           matrix: Optional[Path] = None) -> Tuple[List[str], str, Optional[Tuple[int, int]]]:
    """`check`, plus the requirements figure `(X, N)` over the spec ids (None without an appendix Z)."""
    problems = []  # type: List[str]
    figure = None  # type: Optional[Tuple[int, int]]
    try:
        expected, parent_of = spec_ids(requirements)
        # The pack is built from requirements.json alone, so only these ids can have a matrix row.
        packed = list(expected)
        business_specs = list(business_specs)
        domains = requirements.resolve().parent / "domains"
        split = any(spec.resolve().parent.parent == domains for spec in business_specs)
        skipped = []  # type: List[str]
        for business_spec in business_specs:
            numbered = business_spec_ids(business_spec, requirements, split)
            if numbered is None:
                skipped.append(business_spec.name)
                continue
            expected += [rid for rid in numbered if rid not in expected and rid not in parent_of]
    except ValueError as exc:
        return [str(exc)], "", None
    by_key = {}  # type: Dict[Tuple[str, int], str]
    for rid in list(expected) + list(parent_of):
        found = find_ids(rid)
        # Only an id that is one family token as a whole (`REQ-001`) has respellings to catch;
        # `MSACCESS-RULE-0001` merely contains `RULE-0001`.
        if len(found) == 1 and found[0][0] == rid:
            by_key.setdefault(found[0][1], rid)
    known_set = set(expected) | set(parent_of)
    expected_set = set(expected)
    # Every spec id, whatever its prefix, is matched first as a whole token, exactly as spelled.
    spelled = re.compile(LEFT + "(?:" + "|".join(
        re.escape(rid) for rid in sorted(known_set, key=len, reverse=True)) + ")" + RIGHT)
    try:
        for spec in specs:
            # A brief adds only capability ids of its own (CAP-nn); any other family, or a
            # respelling of a spec id it quotes, is not the spec's and stays unknown.
            for token, key in defined_in(read(spec)):
                if key[0] == "CAP" and key not in by_key:
                    by_key[key] = token
                    known_set.add(token)
        lines = strip_fences(read(report).splitlines())
    except ValueError as exc:
        return [str(exc)], "", None
    name = report.name
    body_rows, headers, _ = table_rows(lines)

    def classify(token: str) -> Optional[str]:
        """Why a cited id is wrong, or None when it is a spec or report-local id."""
        if token in known_set or LOCAL_ID.match(token):
            return None
        found = find_ids(token)
        twin = by_key.get(found[0][1]) if found and found[0][0] == token else None
        if twin:
            return "respells spec id {} as {}".format(twin, token)
        return "cites {}, which is not in the spec{}".format(
            token, "" if found else " (if the Business Spec numbers it, pass --business-spec)")

    def native_ids(cell: str) -> List[str]:
        """Id-shaped tokens no family pattern reads as a whole (an unknown `MSACCESS-RULE-0099`)."""
        return [t for t in re.findall(r"[A-Za-z][\w.-]*[A-Za-z0-9]", ADDRESS.sub(" ", cell))
                if is_spec_token(t) and [tok for tok, _ in find_ids(t)] != [t]]

    # Rows whose first cell is checked here; the prose scan below reads their other cells.
    row_lines = {}  # type: Dict[int, int]
    spec_rows = {}  # type: Dict[str, Dict[str, Row]]
    for label, section in (("section 5", "5"), ("appendix A", "A"), ("appendix Z", "Z")):
        rows = section_rows(lines, section, body_rows, headers)
        if rows is None:
            problems.append("{}: no {} heading (`## {}. ...`)".format(name, label, section))
            continue
        for row in rows:
            # Only what the reader sees counts: a link's target or an anchor is an address, not a citation.
            first = visible(row.first)
            row.ids = spelled.findall(first) + ids_in_cell(spelled.sub(" ", first))
        # An unknown native id is a citation only in a requirements table: one headed by an id
        # column, or one that already cites a known id. Another table's first column is just text.
        cites = {row.table for row in rows if row.ids} | {
            row.table for row in rows if re.search(r"\bids?\b", re.sub(r"[`*_]", "", headers.get(row.table, [""])[0]))}
        for row in rows:
            if row.table in cites:
                row.ids += native_ids(spelled.sub(" ", visible(row.first)))
        seen = {}  # type: Dict[str, int]
        spec_rows[section] = {}
        # The requirements and traceability tables are the ones whose rows cite ids; another
        # table in the section (a per-app summary, say) has none and isn't checked row by row.
        id_tables = {row.table for row in rows if row.ids}
        listed = sorted({row.table for row in rows if row.ids and not row.addition})
        if section != "A" and len(listed) > 1:
            problems.append("{}: {} splits the spec ids over {} tables; keep every id in one list".format(
                name, label, len(listed)))
        described = set()  # type: Set[int]
        for row in rows:
            if not row.ids:
                if row.table in id_tables and not row.addition:
                    problems.append("{}:{} ({}): a row with no spec id ({}); every row cites one, or sits under "
                                    "Additions".format(name, row.line_no, label, row.first or "empty"))
                continue
            row_lines[row.line_no] = row.id_index
            where = "{}:{} ({})".format(name, row.line_no, label)
            if section != "A" and not row.addition:
                index = column(headers.get(row.table, []), "description")
                if index is None:
                    if row.table not in described:
                        problems.append("{}: the table has no Description column; every requirement says in plain "
                                        "English what it is".format(where))
                    described.add(row.table)
                # An id, any id, says what the requirement is no better than a blank does.
                elif not re.sub(r"[\W_]", "", " ".join(
                        t for t in re.findall(r"\S+", row.cell(index)) if not is_spec_token(t.strip(".,;:()")))):
                    problems.append("{}: {} has no description".format(where, row.ids[0]))
            # A folded id stands for the entry it folded into, so a row may list it beside its parent.
            if len({parent_of.get(token, token) for token in row.ids}) > 1 and section != "A":
                problems.append("{}: one row merges {}; give each id its own row".format(where, ", ".join(row.ids)))
            for token in row.ids:
                rid = parent_of.get(token, token)
                if row.addition:
                    # An addition is work the spec didn't ask for: a spec id, or a respelling of one, isn't one.
                    if rid in expected_set:
                        problems.append("{}: {} is a spec id; it belongs in the requirements list, not under Additions"
                                        .format(where, token))
                    else:
                        why = classify(token)
                        if why and why.startswith("respells"):
                            problems.append("{}: {}".format(where, why))
                    continue
                why = classify(token)
                if why:
                    problems.append("{}: {}".format(where, why))
                    continue
                if section != "A" and seen.get(rid, row.line_no) != row.line_no:
                    problems.append("{}: {} already has a row at line {}".format(
                        where, token if rid == token else "{} (folded into {})".format(token, rid), seen[rid]))
                seen.setdefault(rid, row.line_no)
                spec_rows[section].setdefault(rid, row)
        missing = [rid for rid in expected if rid not in seen]
        if missing:
            shown = ", ".join(missing[:20]) + (" and {} more".format(len(missing) - 20) if len(missing) > 20 else "")
            problems.append("{}: {} of {} spec ids have no {} row: {}".format(
                name, len(missing), len(expected), label, shown))
    numbered = requirement_list(name, lines, body_rows, headers, problems)
    if numbered is not None:
        for spec in specs:
            try:
                brief_lines = strip_fences(read(spec).splitlines())
            except ValueError as exc:
                problems.append(str(exc))
                continue
            brief_rows, brief_headers, _ = table_rows(brief_lines)
            before = len(problems)
            planned = requirement_list(spec.name, brief_lines, brief_rows, brief_headers, problems)
            if planned:
                problems += same_list(name, numbered, spec.name, planned)
            elif len(problems) == before:
                # --spec promises the 1:1 mapping: a brief it can't read that from must not pass quietly.
                problems.append("{}: no section-5 requirements table (`## 5.` heading, then `| Req ID | Type | "
                                "Source id | Description |` with rows); the report could not be mapped to it".format(
                                    spec.name))
    if "Z" in spec_rows:
        found, figure = checklist(name, lines, headers, spec_rows.get("5", {}), spec_rows["Z"], expected_set)
        problems += found
    if matrix is not None:
        try:
            problems += matrix_check(matrix, expected, packed, parent_of, spec_rows.get("5", {}), headers, name, lines)
        except ValueError as exc:
            problems.append(str(exc))

    # Prose, captions, other tables and a row's other cells: a respelled id anywhere still breaks the lookup.
    for no, line in enumerate(lines, 1):
        # Addresses go first, so blanking an id inside a URL can't leave a piece of it to read as prose.
        if no in row_lines:
            row_cells = cells(line)
            line = "|".join(row_cells[:row_lines[no]] + row_cells[row_lines[no] + 1:])
        text = spelled.sub(" ", ADDRESS.sub(" ", line))
        for token, key in sorted(set(find_ids(text))):
            twin = by_key.get(key)
            if twin and token not in known_set:
                problems.append("{}:{}: respells spec id {} as {}".format(name, no, twin, token))

    summary = ("{} spec ids{}, each with one described section-5 row, an appendix-A row and a matching appendix-Z "
               "checklist row, spelled as the spec spells them{}").format(
        len(expected), " (plus {} folded into them)".format(len(parent_of)) if parent_of else "",
        "; each links its Test Evidence Pack matrix row, cites the test ids that prove it and agrees with its "
        "result" if matrix is not None else "")
    if skipped:
        summary += ("; skipped {}: an overview from before the extractor numbered requirements in it, so only "
                    "the domain specs were read").format(", ".join(skipped))
    return problems, summary, figure


def requirement_list(name: str, lines: List[str], body_rows: Dict[int, int], headers: Dict[int, List[str]],
                     problems: List[str]) -> Optional[List[Tuple[int, str, str, str]]]:
    """Section 5's numbered requirements rows, as `(line, Req ID, Type, Source id)`, in order.

    Adds a problem when the table has no Req ID, Type or Source id column, when a Req ID breaks the
    `REQ-00001`, `REQ-00002`, ... sequence, or when a row has no Type. None when section 5 or its
    requirements table is missing (reported elsewhere).
    """
    rows = section_rows(lines, "5", body_rows, headers)
    if not rows:
        return None
    tables = [t for t in dict.fromkeys(row.table for row in rows if not row.addition)]
    if not tables:
        return None
    # The requirements table is the one numbered by Req ID, else the first (pre-numbering) table.
    table = next((t for t in tables if column(headers.get(t, []), "req id") is not None), tables[0])
    header = headers.get(table, [])
    req, kind, source = column(header, "req id"), column(header, "type"), column(header, "source id")
    missing = [label for label, index in (("Req ID", req), ("Type", kind), ("Source id", source)) if index is None]
    if missing:
        problems.append("{}: the section-5 requirements table has no {} column; it starts `| Req ID | Type | "
                        "Source id | Description |`, numbered REQ-00001, REQ-00002, ... in order".format(
                            name, " or ".join(missing)))
        return None
    listed = []  # type: List[Tuple[int, str, str, str]]
    for row in (r for r in rows if r.table == table and not r.addition):
        number = REQ_NUMBER.format(len(listed) + 1)
        got = row.cell(req)
        where = "{}:{} (section 5)".format(name, row.line_no)
        if got != number:
            problems.append("{}: Req ID is {!r}, expected {}; number the rows REQ-00001 upward, in order, with no "
                            "gap or repeat".format(where, got, number))
        if not row.cell(kind):
            problems.append("{}: {} has no Type; say what kind of requirement it is (functional requirement, "
                            "business rule, non-functional, ...)".format(where, number))
        listed.append((row.line_no, got, re.sub(r"\s+", " ", row.cell(kind)).lower(),
                       re.sub(r"\s+", " ", row.cell(source))))
    return listed


def same_list(name: str, report: List[Tuple[int, str, str, str]], brief_name: str,
              brief: List[Tuple[int, str, str, str]]) -> List[str]:
    """The report's section-5 rows are the brief's, one for one and in the same order."""
    problems = []  # type: List[str]
    for (line, rid, kind, source), (_, b_rid, b_kind, b_source) in zip(report, brief):
        if (rid, kind, source) != (b_rid, b_kind, b_source):
            problems.append("{}:{} (section 5): row {} is {} {} ({}), but {} section 5 has {} {} ({}) there; list "
                            "the brief's rows one for one, in its order".format(
                                name, line, rid, source or "no source id", kind or "no type", rid, brief_name,
                                b_rid, b_source or "no source id", b_kind or "no type"))
            break
    if len(report) != len(brief):
        problems.append("{}: section 5 lists {} requirements but {} section 5 lists {}; the report maps the brief's "
                        "table one for one".format(name, len(report), brief_name, len(brief)))
    return problems


def checklist(name: str, lines: List[str], headers: Dict[int, List[str]], listed: Dict[str, Row],
              ticked: Dict[str, Row], spec: Set[str]) -> Tuple[List[str], Tuple[int, int]]:
    """Appendix Z closes the report, lists exactly the section-5 rows, and each answer and the totals agree.

    Also returns the requirements figure: the spec ids whose row answers Implemented Yes, over every spec id.
    """
    problems = []  # type: List[str]
    spec_done = 0
    if not Z_TITLE.match(last_section(lines)):
        problems.append("{}: appendix Z (the requirements checklist) must be the report's last section".format(name))
    # Spec ids missing from either side are already reported; this catches IN-nn and CAP-nn rows.
    for rid in listed:
        if rid not in ticked and rid not in spec:
            problems.append("{}:{} (section 5): {} has no appendix Z row; the checklist lists every requirement in "
                            "section 5".format(name, listed[rid].line_no, rid))
    for rid in ticked:
        if rid not in listed and rid not in spec:
            problems.append("{}:{} (appendix Z): {} has no section-5 row; the checklist only restates section 5"
                            .format(name, ticked[rid].line_no, rid))
    counts = {"implemented": [0, 0], "tested": [0, 0]}  # type: Dict[str, List[int]]
    unreadable = set()  # type: Set[Tuple[int, str]]
    for rid, row in ticked.items():
        where = "{}:{} (appendix Z)".format(name, row.line_no)
        source = listed.get(rid)
        for answer_col, status_col, mapping, allowed in (("implemented", "status", IMPLEMENTED, "Yes, Partial or No"),
                                                         ("tested", "tested", TESTED, "Yes, Partial, No or n/a")):
            index = column(headers.get(row.table, []), answer_col)
            if index is None:
                problems.append("{}: the checklist has no {} column".format(where, answer_col.capitalize()))
                continue
            said = row.cell(index)
            answer = said.lower()
            if answer not in set(mapping.values()):
                problems.append("{}: {} {} is {!r}; answer {}".format(where, rid, answer_col, row.cell(index), allowed))
                continue
            counts[answer_col][0] += answer == "yes"
            spec_done += answer_col == "implemented" and answer == "yes" and rid in spec
            counts[answer_col][1] += answer != "n/a"
            if not source:
                continue
            index = column(headers.get(source.table, []), status_col)
            if index is None:
                if (source.table, status_col) not in unreadable:
                    problems.append("{}:{} (section 5): the requirements table has no {} column, so the checklist "
                                    "can't be checked against it".format(name, source.line_no, status_col.capitalize()))
                unreadable.add((source.table, status_col))
                continue
            want = leading_term(source.cell(index), mapping)
            if want is None:
                problems.append("{}:{} (section 5): {} {} is {!r}, not one of: {}".format(
                    name, source.line_no, rid, status_col, source.cell(index),
                    ", ".join(sorted({k.upper() if mapping is TESTED else k.capitalize() for k in mapping}))))
            elif want != answer:
                problems.append("{}: {} {} says {} but its section-5 row says {}".format(
                    where, rid, answer_col, said, want.capitalize() if want != "n/a" else want))
    figure = (spec_done, len(spec))
    problems += reqs_card(name, lines, figure)
    totals = checklist_totals(lines)
    if totals is None:
        problems.append("{}: appendix Z has no `Implemented: X of N. Tested: Y of M.` totals line".format(name))
        return problems, figure
    for key, said in (("implemented", totals[:2]), ("tested", totals[2:])):
        if tuple(said) != tuple(counts[key]):
            problems.append("{}: appendix Z says {} {} of {}, but its rows count {} of {}".format(
                name, key, said[0], said[1], *counts[key]))
    return problems, figure


def reqs_card(name: str, lines: List[str], figure: Tuple[int, int]) -> List[str]:
    """The page-1 `**P% REQs implemented** X of N` card shows the requirements figure, when the report has one."""
    problems = []  # type: List[str]
    done, total = figure
    exact = 100.0 * done / total if total else 0.0
    for no, line in enumerate(lines, 1):
        m = REQS_CARD.match(line)
        if not m:
            continue
        shown = float(m.group(1))
        count = CARD_COUNT.search(visible(m.group(2)))
        # The card may round down (66% for 66.25%), never up: 95% for 189 of 199 would show a gate pass.
        if (count and (int(count.group(1)), int(count.group(2))) != figure) or not 0 <= exact - shown < 1:
            problems.append("{}:{}: the REQs implemented card says {}{}, but appendix Z's spec-id rows count {} of {} "
                            "({:g}%)".format(name, no, m.group(1) + "%",
                                             " ({} of {})".format(*count.groups()) if count else "",
                                             done, total, figure_pct(done, total)))
    return problems


def checklist_totals(lines: List[str]) -> Optional[Tuple[int, int, int, int]]:
    """Appendix Z's `Implemented: X of N. Tested: Y of M.` totals, or None when the line is missing."""
    prose, inside = [], False  # type: List[str], bool
    for line in lines:
        h = HEADING.match(line)
        if h and len(h.group(1)) <= 2:
            inside = bool(Z_TITLE.match(h.group(2)))
        elif inside and not PIPE.search(line):
            prose.append(line)
    m = TOTALS.search(visible(" ".join(prose)))
    if not m:
        return None
    implemented, listed, tested, driven = map(int, m.groups())
    return implemented, listed, tested, driven


def implemented_figure(requirements: Path, report: Path, specs: Iterable[Path] = (),
                       business_specs: Iterable[Path] = ()) -> Tuple[Optional[Tuple[int, int]], List[str]]:
    """The report's requirements figure `(X, N)`, and the FAIL lines.

    X counts the spec ids (requirements.json plus the ids `business_specs` number) whose
    appendix-Z row answers Implemented Yes (Implemented, tested / Implemented, not tested /
    Changed), and N is every spec id; report-local `IN-nn` / `CAP-nn` rows don't count. It is
    the page-1 "REQs implemented" card and the number the workflow's validator gate reads
    from the intermediate Implementation Report. It is only returned for a report that passes
    `check`, which proves every spec id has exactly one appendix-Z row agreeing with section 5.
    A report that fails returns `(None, problems)`.
    """
    problems, _, figure = _check(requirements, report, list(specs), list(business_specs))
    if problems:
        return None, problems
    return figure, []


# A section-5 Tested verdict and the pack verdicts that contradict it: PASS needs every tagged
# test to have run and passed. Anything else is the reporter's judgement (a Flaky run read as
# PARTIAL, a Blocked one as NOT OBSERVABLE).
CONTRADICTS = {"pass": {"Pass (partial)", "Fail", "Flaky", "Blocked", "Not covered"}, "fail": {"Pass", "Pass (partial)"}}


def matrix_check(path: Path, expected: List[str], packed: List[str], parent_of: Dict[str, str],
                 listed: Dict[str, "Row"], headers: Dict[int, List[str]], name: str,
                 lines: Optional[List[str]] = None) -> List[str]:
    """The pack's matrix lists the requirements.json entries (`packed`) once each, and section 5 links and agrees.

    `expected` adds the ids only a Business Spec numbers: a matrix row for one is fine, a missing one is not
    reported, since the pack can't have it. Each row also cites the test ids that prove it, and `lines` (the
    report, fences blanked) cites no test id the run doesn't have.
    """
    try:
        data = json.loads(read(path))
    except ValueError as exc:
        raise ValueError("{}: can't be read as the pack's summary.json ({})".format(path.name, exc))
    rows = data.get("requirements") if isinstance(data, dict) else None
    if not isinstance(rows, list) or not all(isinstance(r, dict) and isinstance(r.get("id"), str) for r in rows):
        raise ValueError("{}: has no `requirements` list with an `id` on each, so it isn't the pack's "
                         "summary.json".format(path.name))
    if data.get("subset"):
        raise ValueError("{}: is a subset run ({}); pass the full run's evidence/summary.json".format(
            path.name, ", ".join(map(str, data["subset"]))))
    problems = []  # type: List[str]
    verdicts = {}  # type: Dict[str, str]
    proven_by = {}  # type: Dict[str, List[str]]
    # A test tagged with two requirements sits under both rows: count it once (its report link is Playwright's id).
    tests = list({(t.get("report") or "", t.get("title") or "", t.get("file") or "", t.get("id") or ""): t
                  for t in [t for row in rows for t in (row.get("tests") or []) if isinstance(t, dict)]
                  + [t for t in (data.get("other") or []) if isinstance(t, dict)]}.values())
    unnamed = [t for t in tests if not TEST_ID.match(str(t.get("id") or ""))]
    if unnamed:
        problems.append("{}: {} of {} tests in the run have no test id (`{}`); give each test testId('TEST-nnn'), "
                        "check the pack with check_pack.py and run it again".format(
                            path.name, len(unnamed), len(tests), unnamed[0].get("title", "untitled")))
    run_ids = {str(t["id"]) for t in tests if t not in unnamed}
    for row in rows:
        rid = parent_of.get(row["id"], row["id"])
        proven_by.setdefault(rid, [])
        for t in row.get("tests") or []:
            if isinstance(t, dict) and str(t.get("id") or "") in run_ids and t["id"] not in proven_by[rid]:
                proven_by[rid].append(t["id"])
        if rid not in expected:
            problems.append("{}: the matrix has a row for {}, which is not in the spec".format(path.name, row["id"]))
        elif rid in verdicts:
            problems.append("{}: the matrix has two rows for {}".format(path.name, rid))
        verdicts.setdefault(rid, str(row.get("verdict", "")))
    missing = [rid for rid in packed if rid not in verdicts]
    if missing:
        problems.append("{}: {} of {} spec ids have no matrix row: {}; rebuild the pack from the same "
                        "requirements.json".format(path.name, len(missing), len(packed), ", ".join(missing[:20])))
    terms = {term: term for term in TESTED}
    for rid, row in listed.items():
        if rid not in verdicts:
            continue
        where = "{}:{} (section 5)".format(name, row.line_no)
        # The anchor ends where the id does: `#req-RULE-12` is not a link to RULE-1's row.
        if not re.search(r"traceability-matrix\.html#req-" + re.escape(rid) + RIGHT, "|".join(row.cells)):
            problems.append("{}: {} doesn't link its evidence; cite its matrix row "
                            "(traceability-matrix.html#req-{})".format(where, rid, rid))
        index = column(headers.get(row.table, []), "tested")
        said = leading_term(row.cell(index), terms) if index is not None else None
        if said in CONTRADICTS and verdicts[rid] in CONTRADICTS[said]:
            problems.append("{}: {} is {} here, but the Test Evidence Pack's run says {}".format(
                where, rid, said.upper(), verdicts[rid]))
        # The tests that prove it, by the ids the matrix and the HTML report show them under.
        cited = list(dict.fromkeys(m.group(0) for m in TEST_TOKEN.finditer(" ".join(visible(c) for c in row.cells))
                                   if TEST_ID.match(m.group(0))))
        for tid in cited:
            if tid in run_ids and tid not in proven_by.get(rid, []):
                problems.append("{}: cites {} for {}, but the run doesn't tag {} with {}".format(
                    where, tid, rid, tid, rid))
        missing = [tid for tid in proven_by.get(rid, []) if tid not in cited]
        if missing:
            problems.append("{}: {} doesn't cite {}, the test{} the Test Evidence Pack's run proves it with; name "
                            "each test id beside its evidence".format(
                                where, rid, ", ".join(missing), "" if len(missing) == 1 else "s"))
    by_number = {int(tid.split("-", 1)[1]): tid for tid in run_ids}
    for no, line in enumerate(lines or [], 1):
        # As a reader sees it: `TEST\-099` renders as TEST-099, so it is checked as one.
        for m in TEST_TOKEN.finditer(visible(line)):
            token = m.group(0)
            if TEST_ID.match(token):
                if token not in run_ids:
                    problems.append("{}:{}: cites test {}, which isn't in the Test Evidence Pack's run".format(
                        name, no, token))
            elif (m.group(1) == "TEST" or m.group(2) not in ("", " ")) and int(m.group(3)) in by_number:
                problems.append("{}:{}: respells test id {} as {}".format(name, no, by_number[int(m.group(3))], token))
    return problems


def leading_term(cell: str, vocabulary: Dict[str, str]) -> Optional[str]:
    """The mapped value of the vocabulary term a cell starts with; a reason may follow it (`PARTIAL (one region)`)."""
    text = re.sub(r"\s+", " ", cell.lower()).strip()
    for term in sorted(vocabulary, key=len, reverse=True):
        if text == term or (text.startswith(term) and not text[len(term)].isalnum()):
            return vocabulary[term]
    return None


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("requirements", type=Path, help="the extraction's requirements.json")
    parser.add_argument("report", type=Path, help="the Implementation Report markdown")
    parser.add_argument("--spec", type=Path, action="append", default=[],
                        help="a Business Brief whose re-derived CAP-nn ids the report may cite")
    parser.add_argument("--business-spec", type=Path, action="append", default=[],
                        help="the extractor's Business Spec; ids its section-5 table numbers are spec ids too")
    parser.add_argument("--matrix", type=Path,
                        help="the Test Evidence Pack's evidence/summary.json; section 5 must link and agree with it")
    parser.add_argument("--figure", action="store_true",
                        help="also print the report's requirements figure: spec ids implemented, over every spec id")
    args = parser.parse_args(argv)
    problems, summary = check(args.requirements, args.report, args.spec, args.business_spec, args.matrix)
    for p in problems:
        print("FAIL " + p)
    if problems:
        if summary:  # empty when an input file itself couldn't be read
            print("{} mismatch(es) between the spec and the report".format(len(problems)))
        return 1
    print("OK " + summary)
    if args.figure:
        figure, _ = implemented_figure(args.requirements, args.report, args.spec, args.business_spec)
        if figure is not None:
            print("REQS IMPLEMENTED {} of {} ({:g}%)".format(figure[0], figure[1], figure_pct(*figure)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
