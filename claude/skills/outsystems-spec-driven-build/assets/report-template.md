# Spec-driven build report

> Illustrative skeleton — `scripts/build.py render-report` produces
> the actual report Markdown directly. This file is documentation
> only; it isn't read at runtime.

- **App:** `{{app_key}}`
- **Generated:** {{timestamp}}
- **Spec file:** `{{spec_path}}`

## Mentor turn: build

- **Run ID:** `{{run_id}}`
- **Status:** `{{status}}`
- **Landed:** {{yes_or_no}} ({{reason}})
- **Result file:** `{{result_path}}`

{{mentor_summary}}

## Mentor turn: fix 1

(only when a fix turn was sent; same fields as above)

## Spec used (for reference)

<details>
<summary>Click to expand the full spec</summary>

{{spec_text}}

</details>
