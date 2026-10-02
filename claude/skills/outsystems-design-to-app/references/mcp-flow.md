# OutSystems MCP — Mentor Flow Reference

This skill drives app generation via the **OutSystems MCP server** (`mcp__outsystems__*` tools). Server-side OML editing happens in a Mentor **session** — open it, load the app, prompt, poll, publish, close — using whatever session tools the connected MCP exposes. The steps below describe the *behaviour*; bind to the current tool names.

## Prerequisites

- `outsystems` MCP server connected in Claude Code (`mcp__outsystems__*` tools available)
- User authenticated — call `mcp__outsystems__auth_status` first; if expired, surface a re-auth prompt
- Target app exists in the OutSystems environment (use `app_list` to find it, or `app_create` to mint a new shell)

## Finding the App

```
app_list { search: "<app-name>" }
```

Returns `app_key` (UUID) — use this for all subsequent calls. If multiple results, confirm with the user before proceeding.

## Sending a Spec to Mentor

**First turn** — open a session, load the app, and send the spec:

```
mentor_start_session {}                                  # → sessionId
mentor_load_asset { sessionId, assetKey: "<app-key-uuid>" }
mentor_prompt { sessionId, message: "<SPEC_PREAMBLE><minified-spec-json>" }
```

`mentor_prompt` returns a `runId`. OML editing happens entirely server-side.

### The poll loop

The response is **terse by default** — `events: []` and `nextCursor: null` — while
`status`, `currentStep` and `message` advance on their own. Those three are enough to
decide whether to keep polling; ask for event bodies only when you need them.

```
LOOP:
  r = mentor_get_run { sessionId, runId: "<runId>" }
  # r: { status, currentStep?, message?, events, nextCursor,
  #      truncated, pollAfterMs, result?, error? }

  IF r.status is "succeeded":
    → Terminal. The run belongs to the still-open session (reuse sessionId to
      resume/publish) AND r.result carries validation, turn_error and the
      completion flags attemptedChange / changeApplied.
    → "succeeded" is NOT proof a change landed, and neither flag is either — see
      "The completion flags are not a write signal" below. Confirm by reading the
      model back. If Mentor replied with a plan and asked "Shall I proceed?", the
      turn applied nothing: send a follow-up prompt to execute.
    → BREAK loop.

  IF r.status is "failed" or "cancelled":
    → Terminal failure. The session stays open — resume it with another mentor_prompt
      (retry/continue); don't open a new session (that drops unpublished edits).
    → BREAK loop.

  # r.status is "running" or "cancelling" — both non-terminal:
  IF r.truncated is true:
    → More events remain past the returned span. Poll again IMMEDIATELY with
      cursor = r.nextCursor; do NOT sleep.
  ELSE IF draining with details:true AND r.nextCursor advanced:
    → Events are cursor-paged and batched, so drain polls are correctness,
      not waste. Poll again immediately.
  ELSE:
    → Drained (or polling terse for status only). Sleep
      max(r.pollAfterMs, ~30s). Re-read pollAfterMs from THIS response — it backs
      off as the run ages, so never cache the first value.
  → CONTINUE loop.
```

**Key rules:**
- Terminal statuses are lowercase — `succeeded` / `failed` / `cancelled`. `running` and
  `cancelling` are **non-terminal**: `cancelling` is a cancel in flight, so keep polling
  until it lands on `cancelled` rather than reporting the cancel as done.
- Pass `details: true` (optionally `events_limit`, default 20 / max 100) to populate
  `events` and `nextCursor`; carry the previous `nextCursor` forward as `cursor` on the
  next detailed poll (only pass `cursor` when polling with `details: true`). Individual
  event bodies over the inline byte cap come back as
  `{ _eventId, _originalBytes, _truncated: true }` — that per-event flag is a clipped
  body, not a short page.
- Top-level `truncated: true` means more events remain past the returned span — poll
  again immediately with the new `nextCursor` rather than sleeping. The same
  drain-don't-sleep rule holds while `nextCursor` keeps advancing on a `details: true`
  poll: the pause is for a poller that is waiting, not one that is draining. This is
  the rule `outsystems-spec-driven-build` and `outsystems-mentor-copilot` state in
  their own Step 5 / Step 4 — the three must not drift apart.
- `succeeded` ≠ change applied, and `changeApplied` / `attemptedChange` do not settle it
  either — read the model back (see below) before reporting success.
- `pollAfterMs` is served per response and backs off with the run's age — observed
  doubling from 500 ms to a ~15–16 s ceiling within a single run (live: 2000 → 4000 →
  8000 → 16000), and `0` on the terminal poll. Honor it as a **floor to raise, never one to obey downward**, and sleep it
  **and at least ~30s** (upstream 0.16.0, verified 2026-08-26): each poll costs a whole
  model turn, so a served 500 ms figure is not one to chase. It changes as the run ages,
  so re-read it from every poll. The ~30s minimum is Mentor-only — `publish_status` and
  deploy polls run ~15s.
- Don't bare-sleep — use the harness background-task mechanism (e.g., `run_in_background` in Claude Code).

**Terminal states:** `succeeded`, `failed`, `cancelled`

On `succeeded`, `result` includes:
- `attemptedChange` / `changeApplied` — completion flags; see the rule below
- `validation` — `{ errorCount, warningCount, firstMessages }` from the build check
- `turn_error` — present when the turn did not finish its task
- `events` — cursor-paginated list of changes (populated only when polled with `details: true`)

The session (its `sessionId`) stays open for the next prompt or the publish — no token to echo.

### The completion flags are not a write signal

`status: succeeded` is genuinely not proof that a change landed — but
`changeApplied` is not a sound instrument to replace it with, because it has been
observed **reporting `true` on a turn that wrote nothing**. On 2026-08-26 two read-only
question turns, which asked for a value and were told to make no edits, both returned
`attempted_change: true` and `change_applied: true` (tenant-measured on the pre-session
tool surface, whose fields were snake_case;
`projects/portable-agent-skills/docs/adoption/deleterule-probe-verification.md`,
"One instrument caveat found on the way").

Re-running the same shape on 2026-08-27 returned the opposite —
`attempted_change: false, change_applied: false` on two read-only turns. So the flags
are not uniformly wrong; they are **inconsistent**, which for a gate is the same
problem. The failure mode that matters is the false positive: a turn that wrote nothing
reporting `changeApplied: true` passes the gate and gets reported as done.

So do not gate honest completion on them — **the completion flags are not a write
signal.** Check `validation` for the build's own verdict, and confirm any change you care about by **reading the model back** —
`context_entities` / `context_screens`, or a fresh read turn on a session that never
saw the writing session's OML.

### Follow-up turns — resume the same session

```
mentor_prompt { sessionId, message: "<next-batch-spec-or-refinement>" }
```

Just send another prompt on the same open `sessionId` — the loaded model and history carry forward. No token to track.

### Cancel a stuck run

```
mentor_cancel_prompt { sessionId, runId: "<runId>" }
```

The session stays open; you can prompt again.

## Publishing After Edits

After all Mentor turns succeed, publish the session (ships to the connected dev environment — no env selection):

```
mentor_publish { sessionId }
```

`mentor_publish` can also **refuse the session outright, and a refusal is not a publish to retry** (upstream 0.16.0, verified 2026-08-26). The refusal message names the reason and the fix, and the remedy is a further Mentor turn that completes the work — never a second `mentor_publish`, which re-asks the same incomplete session and gets the same refusal. A `succeeded` run carrying `turn_error` is the usual cause: it is not a finished task, so the publish has nothing complete to take.

Returns a `publicationKey` (fire-and-return). Poll with:

```
publish_status { publish_key: "<publicationKey>" }
```

Poll until `outcome` is `success` (with `status: Finished`) or `failed` — the mentor-publish key reports `outcome`/`status`, not the gateway `state` field. Publish polls follow their own cadence — ~15 s, not the Mentor ~30 s minimum. On success the app's `revision` has advanced; confirm the deployed inventory via `env_app` before reporting a change.

Then fetch the deployed runtime URL with `env_app` (use the dev `env_key` from `env_list`, and `key` = the application key) and report it to the user as a markdown link or bare URL — never wrap in backticks (disables terminal click-to-open). Promoting beyond dev is a separate `deploy_start` step.

There is no `Completed` value; polling for one never terminates.

`env_app { env_key, key }` — the application argument is **`key`**, not `application_key`, which the server rejects with `ValidationError: argument error: unknown parameter: application_key` (tenant-measured 2026-08-27). The reply carries `applicationKey`, `buildKey`, `deploymentKey`, `deploymentDateTime`, `name`, `revision` and `url`.

If a `publish_status` response ever carries **`indeterminate: true`** (the schema's Gateway-path flag), there is no observed outcome — **do NOT re-publish** (upstream 0.16.0, verified 2026-08-26). The server lost sight of the publish, which may still be building and may yet succeed. Re-poll `publish_status` with the `publicationKey`, or verify with `env_app`, then decide; a second `mentor_publish` while the first is still running is exactly what wedges the app.

On a genuinely terminal `failed` outcome, get diagnostics:

```
publish_logs { pub_key: "<publicationKey>" }
```

Surface the returned code (`OS-BEW-*` / `OS-DPL-*` are retried server-side, so a returned code means the retries were exhausted) rather than re-publishing.

## Getting Context (optional — for validation)

Before or after Mentor edits, inspect the app:

```
# Run in parallel for speed:
context_screens  { app: "<app-name>" }
context_entities { app: "<app-name>" }
context_actions  { app: "<app-name>" }
context_themes   { app: "<app-name>" }
```

## Full Example

```
# 1. Find the app
app_list { search: "BankingPortal" }
# → app_key: "abc-123-def"

# 2. Open a session, load the app, send entities + roles batch
mentor_start_session {}                                  # → sessionId
mentor_load_asset { sessionId, assetKey: "abc-123-def" }
mentor_prompt { sessionId, message: "<entities-spec>" }  # → runId: "run-1"
mentor_get_run { sessionId, runId: "run-1" }
# → poll until succeeded

# 3. Send screens batch on the same session
mentor_prompt { sessionId, message: "<screens-spec>" }   # → runId: "run-2"
mentor_get_run { sessionId, runId: "run-2" }
# → poll until succeeded

# 4. Publish (dev env), then close the session
mentor_publish { sessionId }                             # → publicationKey
publish_status { publish_key: "<publicationKey>" }
mentor_close_session { sessionId }

# 5. Get the runtime URL
env_list {}                                              # → dev env_key
env_app { env_key: "<env-key>", key: "abc-123-def" }
# → render `url` as a markdown link to the user
```

## Error Handling

| Error category | Action |
|---|---|
| `AuthError` | Call `mcp__outsystems__auth_status`; if expired, surface re-auth to the user; then retry the original call ONCE |
| Rejection naming `tenant_not_allowed` | An allowlist gate, NOT a lapsed sign-in (upstream 0.16.0, verified). The token is valid, so re-auth / re-registering / re-adding the server all fail identically while risking a working config. Confirm the configured host is the tenant meant (right account, wrong tenant returns this too); if it is, stop and say the tenant needs enabling — retry once only if the user says it was |
| `ValidationError` | Fix the prompt/spec and retry |
| `UpstreamError` | Transient — wait and retry once |
| `InternalError` | Report to user, don't retry |

## Session Lifecycle Notes

- Sessions auto-GC after **30 minutes idle**. Keep the session alive by issuing the next batch soon after the previous one succeeds; **close it explicitly** with `mentor_close_session` when done.
- The `sessionId` from `mentor_start_session` is the only handle you carry — there is no per-turn token to refresh.
- For long batches (entities → chrome → screens), send each as another `mentor_prompt` on the same session.

## Spec Preamble (use verbatim)

Prepend to every Mentor batch prompt:

```
Implement the following spec COMPLETELY. Do NOT stop until every item in the
acceptance_checklist at the end of the spec is satisfied. After all code
executions, verify each acceptance_checklist item by reading the app state —
if any item fails, fix it before finishing. Here is the spec:
```

This preamble was derived from field-tested Mentor failures where the agent stopped mid-build or skipped acceptance items. Removing it re-introduces those failures.
