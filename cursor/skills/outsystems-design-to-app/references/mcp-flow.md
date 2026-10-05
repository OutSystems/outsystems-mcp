# OutSystems MCP — the Mentor call sequence for design-to-app

This skill drives app generation through the **OutSystems MCP server** (`mcp__outsystems__*` tools). The generic rules (how a session works, how to poll a run, how to publish, how to handle errors, when to confirm) live in the **main `outsystems` skill**, and this file does not restate them. It only lays out the sequence this skill uses and the few facts specific to building from a design.

Read the live `tools/list` before the first call. Each tool's `description` and `inputSchema` are the source of truth. Installed through the plugin, the tools are named `mcp__plugin_outsystems_outsystems__<tool>`; registered directly, `mcp__outsystems__<tool>`.

## 1. Get the app into one session

**Existing app** (found with `app_list { search: "<app-name>" }`):

```
mentor_start_session {}                          # → sessionId
mentor_load_asset { sessionId, assetKey: app_key }
```

**New app** (only after the user confirms the creation, see SKILL.md Step 1):

```
app_list { search: "Template Web App", detailed: true }   # → templateAssetKey (assetKey) + portfolioKey
mentor_start_session {}                          # → sessionId
mentor_create_asset { sessionId, assetType: "WebApplication", name: "<app-name>", templateAssetKey, portfolioKey }
                                                 # → applicationKey; the new app is already in this session
```

- Use the tenant's **"Template Web App"**, not the built-in default template. The default pins outdated OutSystems UI / Charts / Maps versions, the first publish then fails at the draft-save step, and Mentor cannot repoint the pins.
- **`portfolioKey` is required in practice** (the server answers "Portfolio ID is required" without it, though the schema marks it optional). Take the template's `portfolioKey` unless the user names another portfolio.
- A session holds **one** app. Don't load another app into it, and don't create in one session and load in another.
- A new app shows up in `app_list`, `app_info`, `app_refs` and the context lookups **only after its first publish**.
- The MCP cannot delete apps, so check `app_list` for the name before creating, and never "retry" a creation by creating again.
- Fallback: if there is no "Template Web App" or creation fails, the user creates the app in ODC Studio and you load it with `mentor_load_asset`.

## 2. Send the two batches on that session

```
mentor_prompt { sessionId, message: "<batch prompt> + <batch 1: entities + roles + seed>" }   # → runId
# poll the run to terminal, per the main skill
# confirm with the user, then publish (section 3) before batch 2

mentor_prompt { sessionId, message: "<batch prompt> + <batch 2: screens + theme + charts + chrome>" }
# poll to terminal, confirm, publish
```

The batch prompt is the single block in SKILL.md Step 5. Prepend it verbatim to both batches.

Poll each run to terminal as the main skill describes (status watcher where the harness has it; only the statuses the live `mentor_get_run` schema lists), then read the whole turn back from `cursor: 0`.

### What to check when a batch reaches terminal

- **`succeeded` means the turn ended, not that the change landed.** Read the completion signals and `validation` first.
- **The completion flags are not a write signal on their own.** `changeApplied` / `attemptedChange` are unreliable in both directions. Confirm the changes you care about by reading the model back: `context_entities` / `context_screens` after a publish, or a read-only question turn on the same session ("… change nothing and do NOT publish").
- **A plan instead of a build.** If Mentor answered with a plan and "Shall I proceed?", the turn applied nothing. Reply on the same session: "Yes, apply all changes now, do not ask again, and do NOT publish."
- **A failed or timed-out turn** ends neither the session nor its committed state: retry in the same session with a narrower, more concrete prompt. Don't cancel a turn whose edits you want, since a cancelled turn's own edits don't land.

## 3. Publish, then verify

Each publish is a tenant write: confirm it with the user first. Publish the **session** (never an app key):

```
mentor_publish { sessionId, comment }        # → publication key; poll publish_status to terminal
# if it answers "deprecated ... Use mentor_prompt with the message \"Publish\" instead":
mentor_prompt { sessionId, message: "Publish" }   # → runId; poll to terminal like any turn
```

`tools/list` may still advertise `mentor_publish` after the server has retired it, so be ready for the fallback. The confirmation you already have covers the fallback: it is the same publish. A `"Publish"` turn yields a publication key: poll `publish_status` with it until `outcome` is terminal (`success` with `status: Finished`), then confirm the revision advanced with `app_info` / `env_app`. A refusal is answered by a further Mentor turn, never a second publish; an unobserved outcome is re-polled or checked, never re-published.

After the final publish:

```
env_app { env_key, key: app_key }    # the argument is `key`; `application_key` is rejected
                                     # env_key: from the publish result, or the development environment in env_list
app_logs { app: app_key, search: "Seed", stage: "Development" }   # each seed timer should log "finished successfully"
```

Give the user the `url` from `env_app` as a link (not wrapped in backticks). On a terminal publish failure, read `publish_logs` and surface the returned code rather than re-publishing.

Release the session with `mentor_close_session` once the work is published and the user is done; releasing discards anything unpublished.
