# OutSystems MCP — the Mentor call sequence for design-to-app

The generic rules (how a session works, how to poll a run, how to publish, how to handle errors, when to confirm) live in the **main `outsystems` skill**. This file only lays out the order of calls this skill makes and the facts specific to building from a design. Read the live `tools/list` before the first call: each tool's `description` and `inputSchema` are the source of truth, and the tools carry whichever prefix your toolset shows.

All of this happens in Step 5, after the Step 4 go/no-go: never before it.

## 1. Get the app into one session

**Existing app** (found in Step 1):

```
mentor_start_session {}                          # → sessionId
mentor_load_asset { sessionId, assetKey: app_key }
```

**New app** (the user already confirmed the creation in Step 1; restate it right before the call):

```
app_list { search: "Template Web App", detailed: true }   # pick the entry named exactly "Template Web App"
                                                 # → templateAssetKey (assetKey) + portfolioKey
mentor_start_session {}                          # → sessionId
mentor_create_asset { sessionId, assetType: "WebApplication", name: "<app-name>", templateAssetKey, portfolioKey }
                                                 # → applicationKey; the new app is already in this session
```

- **`portfolioKey` is required in practice** (the server answers "Portfolio ID is required" without it, though the schema marks it optional). Take the template's `portfolioKey` unless the user names another portfolio.
- **Never repeat a creation.** If `mentor_create_asset` times out or its result is lost, don't call it again: the app may exist without being visible anywhere yet. Ask the user to check ODC Studio for it first.
- Fallback: if there is no "Template Web App" or creation fails, the user creates the app in ODC Studio and publishes it once there; then find it with `app_list` and load it with `mentor_load_asset`.

## 2. Send the two batches on that session

```
mentor_prompt { sessionId, message: "<batch prompt> + <spec slice for batch 1>" }   # → runId
# poll to terminal, per the main skill; check whether Mentor published on its own
# confirm with the user, then publish (section 3) before batch 2

mentor_prompt { sessionId, message: "<batch prompt> + <spec slice for batch 2>" }
# poll to terminal, check for a self-publish, confirm, publish
```

The batch prompt and the two spec slices are defined in SKILL.md Step 5.

When a batch reaches terminal:
- **Did Mentor publish on its own?** Look in the turn's result and events for a publication key or a "published" message. If it did, don't publish again: tell the user, then poll that publication with `publish_status` to terminal.
- **A plan instead of a build.** If Mentor answered with a plan and "Shall I proceed?", the turn applied nothing. Reply on the same session: "Yes, apply all changes now, do not ask again, and do NOT publish."
- Everything else (reading the completion signals, retrying a failed turn) follows the main skill.

## 3. Publish

Each publish is a tenant write: confirm it with the user first, as the main skill requires. Publish the **session**:

```
mentor_publish { sessionId, comment }             # → publication key
# if it answers "deprecated ... Use mentor_prompt with the message \"Publish\" instead":
mentor_prompt { sessionId, message: "Publish" }   # → runId; poll to terminal like any turn
                                                  # its result names the publication key
publish_status { publication_id: <publication key> }   # poll until outcome is terminal
```

`tools/list` may still advertise `mentor_publish` after the server has retired it, so be ready for the fallback. The confirmation you already have covers it: it is the same publish.

After the final publish (the main skill covers `env_app` and the runtime URL):

```
app_logs { app: app_key, search: "Seed", stage: "Development" }   # timer SeedData should log success
```
