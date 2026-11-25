---
description: >-
  Build the Legacy Modernization Toolkit overview report: a one-page HTML explainer of the stages, quality gates, human checkpoints, sources, skills and commands. Pass a question to get a short answer plus the matching section.
argument-hint: optional question (e.g. "which legacy languages are supported?")
---

# /how-it-works

The explicit entry point for Skill **`legacy-modernization-overview`**, which
also loads on its own whenever a user asks how this toolkit works. Load the
skill now and follow its steps on this input:

```text
$ARGUMENTS
```

- **Nothing was given:** build the full overview report, open it, and add two
  or three sentences in chat on what the toolkit does.
- **A question was given:** answer it in chat in a few sentences, then build
  the page trimmed to the intro and the section that answers it.

Build only the report. Don't start an extraction, a design or a build from
this command.
