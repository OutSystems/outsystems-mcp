# Spec-driven build report

> Illustrative skeleton — `scripts/build.py render-report` produces
> the actual report Markdown directly. This file is documentation
> only; it isn't read at runtime.

- **Run ID:** `{{run_id}}`
- **App:** `{{app_key}}`
- **Status:** `{{status}}`
- **Generated:** {{timestamp}}
- **Spec file:** `{{spec_path}}`

## Mentor's build summary

{{mentor_summary}}

## Next steps

1. **Publish the changes** — publish the Mentor session via the MCP's
   Mentor publish tool, then poll publish status (manual confirm).
2. **Generate tests** — run `outsystems-mentor-copilot` with the
   `test-generation` task.
3. **Visualize** — `outsystems-app-architecture` for the graph view.
4. **Document** — `outsystems-app-documentation` for the handoff doc.
5. **Gate the deploy** — `outsystems-deploy-preview` before promotion.

## Spec used (for reference)

<details>
<summary>Click to expand the full spec</summary>

{{spec_text}}

</details>
