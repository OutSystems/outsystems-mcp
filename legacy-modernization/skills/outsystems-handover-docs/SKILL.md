---
name: outsystems-handover-docs
description: >-
  Close-out docs for a migration — re-derive extractor REQs ("Manage X records") into business capabilities with traceability, then author the two disjoint client documents: a forward-looking Business Specification (no build or design-tool language) and the build-state Implementation Report. Use when finishing a migration, re-deriving requirements into business terms, or writing/scrubbing the client document pair. Not for: report structure or PDF mechanics -> the reporter role playbook (app/prompts/reporter.md, shipped with this plugin).
license: MIT
compatibility: Designed for Claude Code with read access to the extractor spec collection. Uses the tenant only for the access check (sign in, read the tool list); the app revision arrives in the BuildReport handoff. One script, scripts/check_report_ids.py (Python 3.8+, standard library only), checks the Report cites the spec's ids unchanged.
allowed-tools: Read Write Glob Grep Bash
metadata:
  version: "1.1.0"
  author: outsystems-r-and-d
---

# OutSystems Handover Docs

A migration closes with **two documents for two audiences**, and the expensive
mistake is blurring them. Before either can be written, the extractor's
functional REQs have to become business capabilities — *"Manage
Request_Create records"* is a table operation, not a requirement.

The full playbook — the capability re-derivation with traceability, the
derived-rule provenance law, the disjointness contract, the scrub proof, and the
filename firewall — is in
**[OutSystems-Handover-Docs.md](./OutSystems-Handover-Docs.md)** in this folder.
**Read it before writing either document.**

The role playbooks this skill and that file name as `app/prompts/<role>.md` ship with
the plugin, not with this folder: read them as `${CLAUDE_PLUGIN_ROOT}/app/prompts/<role>.md`.
If `${CLAUDE_PLUGIN_ROOT}` doesn't resolve (Cursor doesn't set it), `Glob` for
`**/legacy-modernization/app/prompts/reporter.md`: first in your cwd, then under the
host's plugin directory (`~/.cursor/plugins`, `~/.claude/plugins`). A copy of this skill
on its own, outside the plugin, has no playbooks: say so rather than guessing their rules.

**Limited availability: check access first.** Legacy modernization isn't generally
available yet. Before anything else, sign in to the OutSystems MCP (see the plugin
README's [Authorize before you run](../../README.md#authorize-before-you-run)) and read
its tool list. If `modernize_session_start` isn't listed, tell the user, word for
word: *"Legacy modernization is in limited availability and isn't enabled for your tenant yet. Contact OutSystems if you'd like access."* Then stop.

## The five rules that matter most

1. **An extractor REQ is not a business requirement.** Re-frame each into a
   capability (`CAP-nn`) citing the originating REQ ids **and** the screen that
   delivers it. Keep `BR-nn` reserved for individually-identified business
   **rules** — that id space is reconciled one-to-one against test verdicts, so a
   capability wearing a `BR-` id corrupts the coverage table. The source ids
   themselves never change: the Report cites every id exactly as
   `requirements.json` spells it (`REQ-001`, never `REQ-01`), one per row, and
   `scripts/check_report_ids.py` in this folder proves it before rendering
   (with `--matrix`, also that each row links its Test Evidence Pack result,
   cites the pack's test ids (`TEST-007`) that prove it, and agrees with it).
   A Report covering several apps prefixes each test id with its app,
   `<App> TEST-007`, since each app's pack numbers its own.
   Every spec id, including a rule the Business Spec numbers outside
   `requirements.json`, sits in **one** requirements list, numbered
   `REQ-00001`, `REQ-00002`, … in a first Req ID column with a Type and a
   Source id column, and the Report's section 5 maps the Business Brief's table
   one for one, in the same order (`--spec` proves it); every row in both
   documents carries a short plain-English description a non-developer
   understands; and the Report ends with a per-requirement checklist
   (implemented? tested? with `X of N` totals).
2. **Derived rules ship labelled `(derived)` and stay proposals.** Lifecycle,
   locking, double-submit guard, idempotency, audit — real apps enforce rules the
   source never stated. Derive them, name the reasoning, and never present one as
   a source requirement until the user accepts it.
3. **The two documents are disjoint, and the Spec is the strict one.** The
   Business Specification says what the system is *expected to do*: no
   implementation/build/delivery language, no design-tool or design-option names
   (no "Figma", no "Option C"), no test verdicts. The Implementation Report says
   what was *built and drive-tested* at one revision. Prove the scrub with a
   `grep -ci` that returns 0 — don't assert it. Both walk the **same numbered
   skeleton** as the extractor's Business Spec (sections 0–9 plus appendix A,
   defined once in `app/prompts/reporter.md`), so "section 3" is the data model
   in every document; the Report-only parts never reach the Spec. They also
   share **one look and the same pictures** (data model, site map, app
   landscape, drawn with the same layout and legend), so planned and built
   compare box for box.
4. **Never name the Spec so a spec `Glob` mistakes it for source truth.** The
   tester and planner glob the extractor's spec collection for rules to test
   against; an agent-authored `<App>-Business-Spec.md` gets graded as the
   customer's own requirements. Write `<AppName>-business-brief.md` instead, and
   leave the extractor's `<Customer>-Business-Spec.md` untouched as an input.
5. **Both documents are opt-in.** Write them when the user asks for a report /
   spec / handoff — a finished build is not a reason to produce either. The one
   exception: when an OutSystems sign-in that worked earlier expires mid-run,
   write the Implementation Report without being asked, and don't wait for a
   revision nobody can read: name it `<AppName>-r<last verified revision>-at-expiry-report.md`
   (or `<AppName>-at-expiry-report.md` when no revision was ever verified).

## When to use

- Closing out a migration: turning extracted REQs into business capabilities,
  user journeys and business rules.
- Writing, splitting or scrubbing the client **Business Specification** and
  **Implementation Report** pair.
- A client asks to strip design/implementation references from the spec.

## When NOT to use

- **Report structure, screenshots, base64 image embedding, print CSS, diagram
  authoring, PDF rendering and QA** → `app/prompts/reporter.md` owns all of it.
- **Drive-testing and verdicts** (PASS / PARTIAL / NOT OBSERVABLE / FAIL, browser
  limits, what counts as evidence) → `app/prompts/tester.md`.
- **Fixing a defect you found while writing up** → **outsystems-ui-recipes** (a
  button that does nothing, a counter bound to a literal), **outsystems-css-theming**
  (a toolbar that clips or misaligns), **outsystems-auth-and-deploy** (an export
  that ignores filters or writes one row).
- **Mentor turn/session/publish discipline** → **outsystems-app-build**.
- The per-slice requirements **coverage matrix** and plan-item granularity →
  `app/prompts/planner.md`.
