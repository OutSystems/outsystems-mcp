# Iterative deployments — update the same app, don't spawn new ones

**The trap:** Each time you run a build that targets "create app X", you get a brand new ODC asset (new URL, new app_key, revision = 1). After 10 iterations you have 10 apps cluttering your tenant, each abandoned at a different revision. Users get linkrot, demo URLs go stale.

**Why it matters for us:** when chaining `outsystems-spec-driven-build` (or `outsystems-design-to-app`) with `outsystems-change-planner` for iterative refinement, we want updates to land on the SAME asset — same URL, incrementing revision counter. The `outsystems-mentor-copilot` skills already handle this via session resumption, but the *greenfield* skills don't always preserve identity across runs.

## The pattern they use

`claude-oml-tool` solves this by pinning the OutSystems `eSpace.Key` (the asset's stable identifier) in a local file: `.keys/<AppName>.guid`. On every build:

1. If `.keys/<AppName>.guid` exists, load it and re-use that `eSpace.Key` — the SaveAs writes an OML with the same identity, ODC recognises it as the same asset.
2. If it doesn't exist, mint a new key, persist it, then proceed.

`GapFill.SaveAs` does the actual key-pinning during OML save.

## Translating to our Mentor-driven flow

We don't write OMLs directly. But we DO control which `app_key` we load into the Mentor session:

- The skill's Step 1 (Identify or create the app shell) currently has three paths: existing key from user, mint a new shell via `mentor_start_session` → `mentor_create_asset`, or have the user create one in Portal.
- For **iterative builds**, the FIRST run mints a shell (or uses an existing one). Every subsequent run on "the same app" must use the **same `app_key`** — that's the identity pin.

The catalog should already do this if used correctly, but it's worth flagging explicitly:

- ✅ Right: store the `app_key` of the app the first build created with `mentor_create_asset` in a per-app config (e.g., `~/.claude/cache/outsystems-spec-driven-build/<APP_NAME>/.app-key`) and re-use it for every subsequent build against `APP_NAME`.
- ❌ Wrong: every run calls `mentor_create_asset` with a fresh name (`HomeBanking_v1`, `HomeBanking_v2`, ...). New asset every time.

## What "Keep" vs "Replace" looks like across iterations

When iterating on the same `app_key`, **keep**:

- `eSpace.Key` (the identity pin)
- `AppName`
- Entities + their attributes (data model usually stable across iterations)
- REST/Service consume modules
- Theme module configuration
- External Library references

When iterating, **replace**:

- Every WebScreen construction (screens change a lot)
- Every screen-action / helper that's per-screen
- Menu blocks / sidebar blocks (chrome iterates)
- Per-screen chunk HTML

## The "delta protocol" — don't copy ops from previous_plan into delta

Their pipeline learned the hard way: when iterating, you don't restate previous operations in the new delta — you only specify the NEW changes. Duplicating ops causes id collisions and wastes context.

For us (Mentor-driven), the equivalent is: when resuming a Mentor session (another prompt on the same open session), the new prompt should describe what's CHANGING — not re-describe what's already in the app. Mentor's session memory carries the prior state.

In the spec.json: when an iteration is in flight, the spec section should mark which sections are "unchanged" (Mentor preserves them) vs "modified" / "new" (Mentor edits / adds).

## How this composes with `outsystems-change-planner`

The local-only `outsystems-change-planner` skill (in `~/.claude/skills/`, not in the public repo) is the natural home for iteration discipline:

- Phase 1 (brief + plan) should look up the `app_key` from the per-app config file, not mint a new one.
- Phase 2 (execute) loads the existing `app_key` into a Mentor session and sends a delta-style prompt.

## How to detect mistakes

If you find yourself with `HomeBanking_v1`, `HomeBanking_v2`, `HomeBanking_v3` in your tenant, you've broken the identity pin. The fix: pick the latest one, store its `app_key` in the per-app config, and pass it forward on the next run.

## Attribution

- [`claude-oml-tool/oml-tool/skills/odc/validated/iterative-deployments.md`](https://github.com/OutSystems/claude-oml-tool/blob/main/oml-tool/skills/odc/validated/iterative-deployments.md) — validated 2026-05-06
