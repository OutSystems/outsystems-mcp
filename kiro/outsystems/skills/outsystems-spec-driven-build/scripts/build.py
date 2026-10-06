#!/usr/bin/env python3
"""
outsystems-spec-driven-build driver.

This script does NOT call Mentor. Mentor is invoked via the OutSystems MCP
by the model loop. This script handles spec-side concerns only:

  list-questions   — emit the interview questions JSON for the
                     procedure to walk through with the user.
  assemble-spec    — given interview answers JSON, produce a
                     valid spec.md.
  validate-spec    — check a spec.md before Mentor builds from it:
                     required sections, leftover placeholders, a
                     defined role for every screen, entities,
                     relationships and integrations.
  show-spec        — pretty-print a spec.md to stdout for user
                     confirmation before firing Mentor.
  build-prompt     — wrap a spec.md in the Mentor prompt with the
                     guardrails.
  render-report    — given the terminal Mentor run result +
                     the spec used, render a build-report.md.

Pure stdlib. No pip install.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path


# --------------------------------------------------------------------------- IO

SKILL_DIR = Path(__file__).resolve().parent.parent
QUESTIONS_PATH = SKILL_DIR / "templates" / "interview-questions.json"
TEMPLATE_PATH = SKILL_DIR / "templates" / "spec-template.md"
EXAMPLE_PATH = SKILL_DIR / "templates" / "example-spec.md"


# ---------------------------------------------------------- Required sections

# Sections the spec validator requires, by number and title, as in
# templates/spec-template.md.
REQUIRED_SECTIONS = [
    ("1", "Overview"),
    ("2", "Roles"),
    ("3", "Data model"),
    ("4", "Screens + RBAC"),
    ("8", "Out of scope"),
]

# Written by assemble-spec for a required interview answer that is missing;
# validate-spec fails on it.
NOT_PROVIDED = "(NOT PROVIDED — required)"

# --------------------------------------------------------------- Mentor prompt

# Guardrails appended to the spec when firing Mentor. Each one targets
# a mistake Mentor is known to make on greenfield builds.
MENTOR_GUARDRAILS = """
# CRITICAL CONSTRAINTS — read before building

Treat each constraint as a HARD requirement, not a hint.

1. **Respect the role-per-screen assignments in Section 4 EXACTLY.**
   Do NOT default screens to anonymous/public access. If Section 4
   says "Manager only", set the screen to require the Manager role.
   This is the single most common failure mode.

2. **Apply OutSystems UI to all screens.** Do NOT generate bare HTML
   layouts. Use OutSystemsUI patterns (Cards, Lists, Forms, Layout
   templates) wherever applicable.

3. **Use ODC terminology only.** Do NOT reference "Service Studio",
   "eSpace", or other OutSystems 11 concepts. The target is ODC.

4. **Respect Section 8 (Out of scope) absolutely.** If a feature is
   listed there, do NOT build it — even partially, even "just in
   case". Out-of-scope means out.

5. **Do NOT call `eSpace.AddDependency(globalKey)` from
   `applyModelApiCode`.** Known broken (NRE). If you need a referenced
   library, surface that requirement in the build report so the user
   can add it manually in Studio.

6. **Use the EXACT attribute types from Section 3.** If the spec says
   `Long Integer`, use `Long Integer`. Do NOT silently substitute
   `Integer` or auto-detect — type mismatches cause build failures
   downstream.

7. **Implement seed data via a `BootstrapData` server action** (idempotent:
   it inserts only when the tables are empty) unless Section 8 explicitly
   excludes it, and **make it run on its own**: call it from a Timer that
   runs when the app is published. An action nothing calls never runs,
   and the app opens with empty tables. Customers want demos to "look
   real" on first open.

8. **Do NOT publish the app in this turn.** Publishing is done
   separately, after the user confirms.

9. **At the end, summarize:** what was created (count of entities,
   screens, actions, roles), what was skipped (and why), and any
   manual steps the user needs to take (e.g. add a library via Studio).
"""


# --------------------------------------------------------------------------- Q


def cmd_list_questions(args: argparse.Namespace) -> int:
    """Emit the interview questions JSON to stdout."""
    if not QUESTIONS_PATH.exists():
        print(f"questions file missing: {QUESTIONS_PATH}", file=sys.stderr)
        return 1
    sys.stdout.write(QUESTIONS_PATH.read_text("utf-8"))
    return 0


# --------------------------------------------------------------------- Assemble


def _as_bullets(answer: str) -> list[str]:
    """One bullet per line: `Name: text` or `Name (text)` becomes `- **Name**: text`.
    Names are single words, as OutSystems names are, so a sentence such as
    "No anonymous access anywhere: ..." stays a plain bullet."""
    out: list[str] = []
    for line in answer.splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith(("- ", "* ")):
            out.append("- " + line[2:].strip())
            continue
        m = re.match(r"^([A-Za-z]\w{0,40})\s*:\s*(.+)$", line)
        if not m:
            m = re.match(r"^([A-Za-z]\w{0,40})\s*\((.+)\)\.?$", line)
        if m:
            out.append(f"- **{m.group(1).strip()}**: {m.group(2).strip()}")
        else:
            out.append(f"- {line}")
    return out


def _as_screen_table(answer: str) -> list[str]:
    """`Screen | purpose | roles` lines become table rows; a line without
    pipes becomes a row with an empty role, which validation then reports."""
    rows = ["| Screen | Purpose | Accessible by (roles) |", "|---|---|---|"]
    for line in answer.splitlines():
        line = line.strip().lstrip("-* ").strip()
        if not line:
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        cells = (cells + ["", "", ""])[:3]
        rows.append("| " + " | ".join(cells) + " |")
    return rows


def cmd_assemble_spec(args: argparse.Namespace) -> int:
    """Given an answers JSON (one key per question id) and an output path, assemble a spec.md
    in the layout of templates/spec-template.md."""
    answers_path = Path(args.answers)
    output_path = Path(args.output)

    if not answers_path.exists():
        print(f"answers file not found: {answers_path}", file=sys.stderr)
        return 1
    answers = json.loads(answers_path.read_text("utf-8"))
    questions = json.loads(QUESTIONS_PATH.read_text("utf-8"))
    required = {q["id"] for q in questions["questions"] if q.get("required")}

    def ans(qid: str) -> str:
        value = str(answers.get(qid, "") or "").strip()
        if value:
            return value
        return NOT_PROVIDED if qid in required else "(None provided.)"

    # Title: the app name from the target-app answer ("TaskTracker (new)"),
    # else the first word of the purpose, as in "TaskTracker. Internal team ...".
    m = re.match(r"\s*([A-Za-z]\w*)", str(answers.get("app_shell") or "")) \
        or re.match(r"\s*([A-Za-z]\w*)", str(answers.get("purpose") or ""))
    name = m.group(1) if m else "Unnamed"
    out: list[str] = [f"# App Spec: {name}", ""]

    def section(heading: str, body: list[str]) -> None:
        out.extend([heading, ""] + body + ["", "---", ""])

    section("## 1. Overview", [
        f"**Purpose:** {ans('purpose')}", "",
        f"**Target app:** {ans('app_shell')}", "",
        f"**Style direction:** {ans('style_direction')}",
    ])
    roles = ans("roles")
    section("## 2. Roles", _as_bullets(roles) if roles != NOT_PROVIDED else [roles])
    entities = ans("entities")
    enums = ans("enums")
    section("## 3. Data model", (
        ["### Entities", ""]
        + (_as_bullets(entities) if entities != NOT_PROVIDED else [entities])
        + ["", "### Static enums", ""]
        + (_as_bullets(enums) if not enums.startswith("(") else [enums])
    ))
    screens = ans("screens_and_rbac")
    section("## 4. Screens + RBAC",
            _as_screen_table(screens) if screens != NOT_PROVIDED else [screens])
    section("## 5. Server actions", [ans("actions")])
    section("## 6. Integrations", [ans("integrations")])
    section("## 8. Out of scope", [ans("out_of_scope")])
    section("## 9. Acceptance criteria", [ans("acceptance")])
    section("## 10. Notes for Mentor", [ans("mentor_notes")])

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(out), encoding="utf-8")
    print(f"wrote {output_path} ({output_path.stat().st_size / 1024:.1f} KB)")
    return 0


# --------------------------------------------------------------------- Validate

# Role names a screen may use without defining them in section 2.
BUILTIN_ROLES = {"anonymous", "allauthenticated"}


def _sections(text: str) -> dict[str, str]:
    """Map section number ("1", "2", ...) to its body, from `## N. Title` headings."""
    found: dict[str, str] = {}
    matches = list(re.finditer(r"^## (\d+)\.[^\n]*$", text, re.M))
    for i, m in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        found.setdefault(m.group(1), text[m.end():end])
    return found


def _content(body: str) -> str:
    """Section body without rules (`---`) and blockquoted guidance."""
    lines = [l for l in body.splitlines()
             if l.strip() != "---" and not l.lstrip().startswith(">")]
    return "\n".join(lines).strip()


def _table_rows(body: str) -> list[list[str]]:
    """Data rows of the markdown tables in a body (header and separator rows dropped)."""
    def is_sep(cells: list[str]) -> bool:
        return all(re.fullmatch(r":?-{3,}:?", c) for c in cells if c)

    blocks: list[list[list[str]]] = [[]]
    for line in body.splitlines():
        s = line.strip()
        if s.startswith("|"):
            blocks[-1].append([c.strip() for c in s.strip("|").split("|")])
        elif blocks[-1]:
            blocks.append([])
    rows: list[list[str]] = []
    for block in blocks:
        if len(block) >= 2 and is_sep(block[1]):
            block = block[2:]
        rows.extend(r for r in block if not is_sep(r))
    return rows


def _norm(name: str) -> str:
    return re.sub(r"[^a-z0-9]", "", name.lower())


def _template_placeholders() -> set[str]:
    if not TEMPLATE_PATH.exists():
        return set()
    return set(re.findall(r"<[^<>\n]+>", TEMPLATE_PATH.read_text("utf-8")))


def _defined_roles(body: str) -> list[str]:
    names = re.findall(r"^\s*[-*]\s+\*\*([^*]+)\*\*", body, re.M)
    if not names:
        names = re.findall(r"^\s*[-*]\s+([A-Za-z][\w ]{0,40}?)\s*:", body, re.M)
    return [n.strip() for n in names]


def _entity_body(body: str) -> str:
    """Section 3 without its Static enums part."""
    return re.split(r"^###\s+Static enums", body, maxsplit=1, flags=re.M)[0]


def _screen_roles(cell: str) -> list[str]:
    """`Engineer (own tasks), EngineeringManager (all)` -> ['Engineer', 'EngineeringManager']."""
    cell = re.sub(r"\([^)]*\)", "", cell)
    parts = re.split(r",|/|;|&|\band\b", cell)
    return [p.strip() for p in parts if p.strip()]


def cmd_validate_spec(args: argparse.Namespace) -> int:
    """Check a spec before Mentor builds from it. Errors fail (exit 1); warnings are printed only."""
    spec_path = Path(args.spec)
    if not spec_path.exists():
        print(f"spec not found: {spec_path}", file=sys.stderr)
        return 1
    text = spec_path.read_text("utf-8")
    sections = _sections(text)
    errors: list[str] = []
    warnings: list[str] = []

    # Required sections present and not trivially empty.
    for num, title in REQUIRED_SECTIONS:
        body = sections.get(num)
        if body is None:
            errors.append(f"## {num}. {title}: missing")
        elif len(_content(body)) < 50:
            errors.append(f"## {num}. {title}: too short (under 50 characters)")
        elif "(NOT PROVIDED" in body:
            errors.append(f"## {num}. {title}: a required answer was not provided")

    # Placeholders left from the template, anywhere in the spec.
    left = sorted(p for p in _template_placeholders() if p in text)
    if left:
        errors.append("unfilled template placeholders: " + ", ".join(left[:8])
                      + (" ..." if len(left) > 8 else ""))

    # Roles (section 2).
    roles = _defined_roles(sections.get("2", ""))
    known = {_norm(r) for r in roles} | BUILTIN_ROLES
    if "2" in sections and not roles:
        errors.append("## 2. Roles: no roles found (list each as `- **RoleName**: what they can do`)")

    # Entities and relationships (section 3).
    if "3" in sections:
        ent_body = _entity_body(sections["3"])
        ent_rows = [r for r in _table_rows(ent_body) if r and r[0]]
        ent_bullets = re.findall(r"^\s*[-*]\s+\S", ent_body, re.M)
        n_entities = len(ent_rows) or len(ent_bullets)
        if n_entities == 0:
            errors.append("## 3. Data model: no entities found (one table row or bullet per entity)")
        rel_cells = [r[2] for r in ent_rows if len(r) > 2]
        has_rel = any(_norm(c) not in ("", "none", "na") for c in rel_cells) or re.search(
            r"\bFK\b|→|->|foreign key|references|belongs to", ent_body, re.I)
        if n_entities >= 2 and not has_rel:
            warnings.append("## 3. Data model: two or more entities but no relationships stated")

    # Screens and the role of each one (section 4).
    if "4" in sections:
        # Rows still holding template placeholders are reported as placeholders above.
        screen_rows = [r for r in _table_rows(sections["4"])
                       if r and r[0] and not r[0].startswith("<")]
        if not screen_rows:
            errors.append("## 4. Screens + RBAC: no screens found (one table row per screen)")
        for row in screen_rows:
            screen, cell = row[0], (row[-1] if len(row) > 1 else "")
            names = _screen_roles(cell)
            if not names:
                errors.append(f"## 4. Screens + RBAC: screen '{screen}' has no role")
                continue
            unknown = [n for n in names if _norm(n) not in known]
            if unknown:
                errors.append(f"## 4. Screens + RBAC: screen '{screen}' names role(s) not defined "
                              f"in ## 2. Roles: {', '.join(unknown)}")

    # Integrations (section 6) and the target app line.
    if "6" not in sections or not _content(sections["6"]):
        warnings.append("## 6. Integrations: missing or empty; write \"None\" if there are none")
    if "**Target app:**" not in text:
        warnings.append("## 1. Overview: no `**Target app:**` line (the app name, new or existing)")

    if errors:
        print(f"spec validation FAILED: {len(errors)} error(s), {len(warnings)} warning(s)")
    else:
        print(f"spec validation OK: {len(warnings)} warning(s)")
    for e in errors:
        print(f"  ✗ ERROR  {e}")
    for w in warnings:
        print(f"  ⚠ WARN   {w}")
    if errors:
        print()
        print("Fix the spec or restart the interview to fill missing sections.")
        return 1
    return 0


# --------------------------------------------------------------------- Show


def cmd_show_spec(args: argparse.Namespace) -> int:
    """Pretty-print a spec to stdout for user confirmation."""
    spec_path = Path(args.spec)
    if not spec_path.exists():
        print(f"spec not found: {spec_path}", file=sys.stderr)
        return 1
    text = spec_path.read_text("utf-8")
    # Add a header banner
    print("=" * 70)
    print(f" SPEC PREVIEW — {spec_path.name}")
    print("=" * 70)
    print()
    print(text)
    print()
    print("=" * 70)
    print(f" END SPEC ({spec_path.stat().st_size / 1024:.1f} KB)")
    print("=" * 70)
    return 0


# --------------------------------------------------------------- Build prompt


def cmd_build_prompt(args: argparse.Namespace) -> int:
    """Wrap a spec in the Mentor-prompt with anti-failure guardrails."""
    spec_path = Path(args.spec)
    if not spec_path.exists():
        print(f"spec not found: {spec_path}", file=sys.stderr)
        return 1
    spec_text = spec_path.read_text("utf-8")

    parts = [
        "Build the following OutSystems application from this spec. "
        "Apply the constraints at the bottom EXACTLY.",
        "",
        "---",
        "",
        spec_text,
        "",
        "---",
        "",
        MENTOR_GUARDRAILS,
    ]
    sys.stdout.write("\n".join(parts))
    return 0


# ------------------------------------------------------------ Render report


def _extract_text(events: list) -> str:
    """Pull the human-readable answer out of the Mentor event stream.

    Events may arrive as dicts OR as JSON strings (the current MCP returns them
    as strings); the streamed answer is the concatenation of `text` chunks whose
    msgType is 'text'. Tolerates the older {kind, content} shape too."""
    chunks: list[str] = []
    for ev in events or []:
        if isinstance(ev, str):
            try:
                ev = json.loads(ev)
            except (json.JSONDecodeError, ValueError):
                continue
        if not isinstance(ev, dict):
            continue
        kind = (ev.get("msgType") or ev.get("MsgType") or ev.get("kind")
                or ev.get("type") or "")
        if kind in ("text", "message", "response", "assistant_message"):
            content = ev.get("text")
            if content is None:
                content = ev.get("content") or ""
            if isinstance(content, list):
                for c in content:
                    if isinstance(c, dict) and "text" in c:
                        chunks.append(c["text"])
            elif isinstance(content, str):
                chunks.append(content)
    return "".join(chunks).strip()


def cmd_render_report(args: argparse.Namespace) -> int:
    """Render a Markdown build report from the terminal Mentor run result + the spec used."""
    spec_path = Path(args.spec)
    result_path = Path(args.result)
    output_path = Path(args.output)

    if not spec_path.exists():
        print(f"spec not found: {spec_path}", file=sys.stderr)
        return 1
    if not result_path.exists():
        print(f"result not found: {result_path}", file=sys.stderr)
        return 1

    spec_text = spec_path.read_text("utf-8")
    raw = json.loads(result_path.read_text("utf-8"))

    if "result" in raw and isinstance(raw["result"], dict):
        terminal = raw["result"]
        status = raw.get("status", "unknown")
    else:
        terminal = raw
        status = raw.get("status", "succeeded")

    events = raw.get("events", [])
    summary = terminal.get("summary") or terminal.get("message") or ""
    if not summary:
        summary = _extract_text(events)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    md: list[str] = []
    md.append(f"# Spec-driven build report")
    md.append("")
    md.append(f"- **Run ID:** `{args.run_id or '-'}`")
    md.append(f"- **App:** `{args.app_key or '-'}`")
    md.append(f"- **Status:** `{status}`")
    md.append(f"- **Generated:** {datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}")
    md.append(f"- **Spec file:** `{spec_path}`")
    md.append("")
    md.append("## Mentor's build summary")
    md.append("")
    md.append(summary.strip() if summary else "_(no summary returned — inspect the raw result)_")
    md.append("")

    md.append("## Spec used (for reference)")
    md.append("")
    md.append("<details>")
    md.append("<summary>Click to expand the full spec</summary>")
    md.append("")
    md.append(spec_text)
    md.append("")
    md.append("</details>")
    md.append("")

    output_path.write_text("\n".join(md), encoding="utf-8")
    print(f"wrote {output_path} ({output_path.stat().st_size / 1024:.1f} KB)")
    return 0


# --------------------------------------------------------------- arg dispatch


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="build.py", description=__doc__)
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("list-questions", help="Emit the interview questions JSON")

    sp = sub.add_parser("assemble-spec", help="Assemble a spec.md from interview answers JSON")
    sp.add_argument("--answers", required=True, help="Path to a JSON object with answers keyed by question id")
    sp.add_argument("--output", required=True, help="Path to write spec.md")

    sp = sub.add_parser("validate-spec", help="Check a spec.md before Mentor builds from it")
    sp.add_argument("--spec", required=True)

    sp = sub.add_parser("show-spec", help="Pretty-print a spec.md for user confirmation")
    sp.add_argument("--spec", required=True)

    sp = sub.add_parser("build-prompt", help="Wrap a spec.md in the Mentor-prompt with anti-failure guardrails")
    sp.add_argument("--spec", required=True)

    sp = sub.add_parser("render-report", help="Render a Markdown build report from the terminal Mentor run result")
    sp.add_argument("--spec", required=True)
    sp.add_argument("--result", required=True)
    sp.add_argument("--output", required=True)
    sp.add_argument("--app-key")
    sp.add_argument("--run-id")

    args = p.parse_args(argv)
    if args.cmd == "list-questions":
        return cmd_list_questions(args)
    if args.cmd == "assemble-spec":
        return cmd_assemble_spec(args)
    if args.cmd == "validate-spec":
        return cmd_validate_spec(args)
    if args.cmd == "show-spec":
        return cmd_show_spec(args)
    if args.cmd == "build-prompt":
        return cmd_build_prompt(args)
    if args.cmd == "render-report":
        return cmd_render_report(args)
    return 1


if __name__ == "__main__":
    sys.exit(main())
