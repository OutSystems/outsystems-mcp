---
description: Design a legacy app for OutSystems — the design half of /workflow-legacy-app. About three options, a pause for a pick, then a pre-build design gate on the picked option. Does not build or publish.
argument-hint: spec collection folder (optional figma URL)
---

<!-- steps: design, selection, design_gate -->
# /generate-design-options

The design phase of `/workflow-legacy-app`, on its own. It reads the spec collection,
has the designer produce **about three** directions, **pauses for a pick**, then runs
the pre-build design gate on the picked option. It does not plan the build, call
Mentor, or publish.

Building the chosen design is `/workflow-legacy-app`, with the same spec paths and the
chosen design passed in as the supplied design (see "After the pick").

Every plugin file named here (`commands/`, `agents/`, `app/prompts/`) is under
`${CLAUDE_PLUGIN_ROOT}`.
If `${CLAUDE_PLUGIN_ROOT}` doesn't resolve (Cursor doesn't set it), `Glob` for
`**/legacy-modernization/commands/generate-design-options.md`: first in your cwd, then under the host's plugin
directory (`~/.cursor/plugins`, `~/.claude/plugins`), since the plugin is usually
installed outside your cwd. Read every plugin file named here under the root you find.

## Limited availability

**Limited availability: check access first.** Legacy modernization isn't generally
available yet. Before anything else, sign in to the OutSystems MCP (see the plugin
README's [Authorize before you run](../README.md#authorize-before-you-run)) and read
its tool list. If `modernize_session_start` isn't listed, tell the user, word for
word: *"Legacy modernization is in limited availability and isn't enabled for your tenant yet. Contact OutSystems if you'd like access."* Then stop.

## User input

```text
$ARGUMENTS
```

Read it for the spec collection path and an optional Figma URL. If the spec path
can't be pinned, say exactly what to attach and stop.

**A Figma URL here is the source design language, not a finished design.** The three
options are drawn from it: they keep its colours, type and components, and differ in
navigation. It is not mirrored as the one design, so the options and the pick still
happen. (To build a design you already have, skip this command and pass it to
`/workflow-legacy-app` as the supplied design.)

## Preflight

- **Frontier model recommended.** If this session is not already on the strongest
  model the harness offers, say so once. Do not refuse a cheaper model.
- **It does not build.** The OutSystems MCP is needed only for the access check above.
- **Design medium.** A Figma MCP is used when one is already connected. When it is
  not, the same three options are HTML/CSS mockups, one directory per option. Do not
  register a new server. The host substitutions are the table in
  `commands/workflow-legacy-app.md`.
- Delegate `designer`, then `reviewer`, then `tester`. A role that fails to launch
  runs inline from `app/prompts/<role>.md` — say which mode you used.

## Steps

1. **`design`** — `Task` the `designer` with the spec paths and, if one was given, the
   Figma URL **labelled as the source design language to draw about three options
   from, not a design to mirror** (so the designer's "Show a pasted design" rule in
   `app/prompts/designer.md` does not apply). Otherwise follow `app/prompts/designer.md`. About three options, at least
   one with a different navigation pattern, each in its own Figma page or its own
   directory, each covering a representative set of screens (about two or three per
   option). Emit the design options as soon as they exist.
2. **`selection`** — print each option (name, navigation pattern, where to open it)
   and wait for the user to pick. No QA runs before the pick, so the choice is fast.
3. **`design_gate`** — mandatory, on the **picked** option only. `reviewer` scores
   spec and screen coverage. `tester` runs visual QA (typos, clipping, spacing,
   empty data). Any fail goes back to the designer, who fixes the picked option and
   re-emits it; the pick stands. Both gates run again until both pass, the same
   loop as `/workflow-legacy-app`'s pre-build gate. Then **stop**: do not start a
   build in this command.

## Progress

Re-emit this block on every transition:

```markdown
## /generate-design-options progress
- specs: ‹path›
- design: pending|running|done — options: ‹n›
- selection: pending|waiting|picked — option: …
- design_gate: pending|running|done — reviewer: … tester: …
```

## After the pick

- Build it with `/workflow-legacy-app`, passing **the same spec paths**, the target app
  name, and the chosen option (its Figma URL or its directory) as the supplied design.
  The spec paths carry the full scope: every requirement and screen, not only the two or
  three screens the option drew. Its `designer` role shows a supplied design rather than
  generating new options (`agents/designer.md`, and "Show a pasted design" in
  `app/prompts/designer.md`), and draws the remaining screens in the chosen direction.
- The `outsystems` plugin's `outsystems-design-to-app` and `outsystems-spec-driven-build`
  build from a design or a written spec with no legacy context. They don't score the build
  against the extracted requirements, so don't use them to build from these specs.
