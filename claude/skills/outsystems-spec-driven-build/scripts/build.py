#!/usr/bin/env python3
"""
outsystems-spec-driven-build driver.

This script does NOT call Mentor. Mentor is invoked via the OutSystems MCP
by the model loop. This script handles spec-side concerns only:

  list-questions   — emit the interview questions JSON for the
                     procedure to walk through with the user.
  assemble-spec    — given interview answers JSON, produce a
                     valid spec.md.
  validate-spec    — verify a spec.md has the required sections
                     and isn't trivially-empty.
  show-spec        — pretty-print a spec.md to stdout for user
                     confirmation before firing Mentor.
  build-prompt     — wrap a spec.md in the Mentor-prompt with
                     anti-failure guardrails baked in.
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

# Sections the spec validator enforces. The numbered prefixes match
# the canonical template in templates/spec-template.md. Order matters
# for the show-spec pretty-printer.
REQUIRED_SECTIONS = [
    "## 1. Overview",
    "## 2. Roles",
    "## 3. Data model",
    "## 4. Screens + RBAC",
    "## 8. Out of scope",
]

OPTIONAL_SECTIONS = [
    "## 5. Server actions",
    "## 6. Integrations",
    "## 7. UI/UX direction",
    "## 9. Acceptance criteria",
    "## 10. Notes for Mentor",
]


# --------------------------------------------------------------- Mentor prompt

# Guardrails appended to the spec when firing Mentor. Each line is
# derived from a real failure mode observed in field testing — see
# README + FIELD-FEEDBACK-LOG references below.
MENTOR_GUARDRAILS = """
# CRITICAL CONSTRAINTS — read before building

These constraints are derived from real Mentor failure modes observed
in field testing. Treat each as a HARD requirement, not a hint.

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

7. **Implement seed data via a `BootstrapData` server action** (idempotent)
   unless Section 8 explicitly excludes it. Customers want demos to
   "look real" on first open.

8. **Reserved theme class names — DO NOT USE.** Five class names —
   `main-content`, `sidebar`, `header`, `content`, `footer` — collide with
   OutSystemsUI's LayoutBlank theme rules. ALWAYS prefix with the app name
   (`banking-sidebar`, `dashboard-main-content`). For sidebar / header /
   footer markup, use prefixed semantic divs (e.g. `<div class="app-sidebar">`)
   not raw `<aside>` / `<nav>` / `<header>` / `<footer>`. For link colors,
   use `!important` to override the theme's
   `a { color: inherit !important }` rule. See
   `outsystems-design-to-app/references/gotchas/theme-collisions.md`.

9. **SVG icon color baking.** Every `<svg>` in a chunk has its color baked
   into a base64 background-image where `currentColor` resolves to BLACK
   and CSS rules like `.X svg { fill: ... }` do NOT apply. For ANY SVG
   inside a dark/coloured container (sidebar, primary button, coloured
   tile), set `fill="#fff"` (and `stroke="#fff"` for stroked icons)
   directly on the `<svg>` element. NEVER ship `<i class="ph ph-X">`
   font-icon markup — it does NOT render in ODC's SPA runtime; use inline
   `<svg>` only. See
   `outsystems-design-to-app/references/gotchas/svg-icon-baking.md`.

10. **TableRecords MUST have a non-empty Source.** Static-demo tables: seed
    via a Local Variable `List<Entity>` populated in OnInitialize using
    `ListAppend`, one append per intended row (8-15 records minimum per
    Section 7 / acceptance criteria), with realistic data. Data-backed
    tables: bind to an Aggregate. NEVER leave Source unset — published
    table renders "no records to display" even though the widget structure
    looks correct. See
    `outsystems-design-to-app/references/gotchas/tablerecords-seeding.md`.

11. **At the end, summarize:** what was created (count of entities,
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


def cmd_assemble_spec(args: argparse.Namespace) -> int:
    """Given an answers JSON (one key per question id) and an output path, assemble a spec.md."""
    answers_path = Path(args.answers)
    output_path = Path(args.output)

    if not answers_path.exists():
        print(f"answers file not found: {answers_path}", file=sys.stderr)
        return 1
    answers = json.loads(answers_path.read_text("utf-8"))
    questions = json.loads(QUESTIONS_PATH.read_text("utf-8"))

    # Group answers by section heading
    sections: dict[str, list[str]] = {}
    for q in questions["questions"]:
        ans = answers.get(q["id"], "").strip()
        if not ans:
            if q.get("required"):
                ans = "(NOT PROVIDED — required section; spec is incomplete)"
            else:
                ans = "None"
        # Find the canonical section heading
        section = q["writes_to"]
        sections.setdefault(section, []).append(ans)

    # Assemble in canonical order
    out_lines: list[str] = [f"# App Spec: {answers.get('purpose', 'Unnamed').split('.')[0][:60]}", ""]
    canonical_order = [
        ("## 1. Overview",       ["purpose", "app_shell", "style_direction"]),
        ("## 2. Roles",          ["roles"]),
        ("## 3. Data model",     ["entities", "enums"]),
        ("## 4. Screens + RBAC", ["screens_and_rbac"]),
        ("## 5. Server actions", ["actions"]),
        ("## 6. Integrations",   ["integrations"]),
        ("## 8. Out of scope",   ["out_of_scope"]),
        ("## 9. Acceptance criteria", ["acceptance"]),
        ("## 10. Notes for Mentor",   ["mentor_notes"]),
    ]
    for heading, q_ids in canonical_order:
        out_lines.append(heading)
        out_lines.append("")
        for qid in q_ids:
            ans = answers.get(qid, "").strip() or "(None provided.)"
            out_lines.append(ans)
            out_lines.append("")
        out_lines.append("---")
        out_lines.append("")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(out_lines), encoding="utf-8")
    print(f"wrote {output_path} ({output_path.stat().st_size / 1024:.1f} KB)")
    return 0


# --------------------------------------------------------------------- Validate


def cmd_validate_spec(args: argparse.Namespace) -> int:
    """Check that a spec has the required sections and they aren't trivially empty."""
    spec_path = Path(args.spec)
    if not spec_path.exists():
        print(f"spec not found: {spec_path}", file=sys.stderr)
        return 1
    text = spec_path.read_text("utf-8")

    issues: list[str] = []
    for section in REQUIRED_SECTIONS:
        if section not in text:
            issues.append(f"  ✗ MISSING: {section}")
            continue
        # Check the section has content (more than 50 chars between this heading and the next ##)
        idx = text.find(section)
        rest = text[idx + len(section):]
        next_heading = re.search(r"\n## ", rest)
        body = rest[:next_heading.start()] if next_heading else rest
        body_stripped = body.strip()
        if len(body_stripped) < 50:
            issues.append(f"  ✗ TOO SHORT: {section} (body is <50 chars)")
        if "(NOT PROVIDED" in body or "<APP_NAME>" in body or "<EntityName>" in body:
            issues.append(f"  ✗ UNFILLED PLACEHOLDER: {section}")

    # Check for app shell key
    if "**App shell key:**" in text:
        shell_line = next((l for l in text.split("\n") if "**App shell key:**" in l), "")
        rest = shell_line.split("**App shell key:**", 1)[1].strip()
        # Strip any (commentary) trailing text
        first_token = rest.split()[0] if rest else ""
        # Loose UUID-ish check
        if not re.match(r"^[0-9a-fA-F]{8}-", first_token):
            issues.append(
                f"  ⚠ App shell key looks invalid: '{first_token[:40]}...'. "
                "Should be a UUID created from ODC Portal first."
            )

    if issues:
        print(f"spec validation FAILED ({len(issues)} issue(s)):")
        for i in issues:
            print(i)
        print()
        print("Fix the spec or restart the interview to fill missing sections.")
        return 1

    print(f"spec validation OK — all {len(REQUIRED_SECTIONS)} required sections present and non-trivial.")
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

    md.append("## Next steps")
    md.append("")
    md.append("Review the build in ODC Portal or Studio. If it looks correct:")
    md.append("")
    md.append(
        "1. **Publish the changes.** Publish the Mentor session via the MCP's "
        "Mentor publish tool (it ships to the connected dev environment), then "
        "poll its publish status to a terminal state. **Never auto-publish** — "
        "a human reviews and confirms first. To promote beyond dev, gate with "
        "`outsystems-deploy-preview`."
    )
    md.append("")
    md.append("2. **Generate tests** for the actions just created:")
    md.append("   - Run `outsystems-mentor-copilot` with the `test-generation` task on this app.")
    md.append("3. **Visualize what was built:**")
    md.append("   - Run `outsystems-app-architecture` on this app to see the structure as a graph.")
    md.append("4. **Generate documentation:**")
    md.append("   - Run `outsystems-app-documentation` on this app for a Markdown handoff doc.")
    md.append("5. **Gate the deploy:**")
    md.append("   - Run `outsystems-deploy-preview` before promoting to Test.")
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

    sp = sub.add_parser("validate-spec", help="Check a spec.md has required sections + non-trivial content")
    sp.add_argument("--spec", required=True)

    sp = sub.add_parser("show-spec", help="Pretty-print a spec.md for user confirmation")
    sp.add_argument("--spec", required=True)

    sp = sub.add_parser("build-prompt", help="Wrap a spec.md in the Mentor-prompt with anti-failure guardrails")
    sp.add_argument("--spec", required=True)
    sp.add_argument("--app-key", help="App shell key (for reference in the prompt)")

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
