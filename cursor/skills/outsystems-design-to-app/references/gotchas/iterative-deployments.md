# Iterative deployments — update the same app, don't spawn new ones

**The trap:** Each time you run a build that targets "create app X", you get a brand new ODC asset (new URL, new app_key, revision = 1). After 10 iterations you have 10 apps cluttering your tenant, each abandoned at a different revision. Users get linkrot, demo URLs go stale.

**Why it matters for us:** when you rebuild or refine the same design with this skill, updates should land on the SAME asset — same URL, incrementing revision counter. And the MCP cannot delete apps, so every stray asset stays in the tenant until someone removes it in the ODC Portal.

## Reuse the same app_key

- The skill has three paths to the target app, chosen in Step 1 and acted on at the start of Step 5: an existing app the user names (loaded into the Mentor session by its key), a new app created in the Mentor session from the tenant's "Template Web App" (after confirmation), or an app the user creates in ODC Studio.
- For **iterative builds**, the FIRST run creates the app (or uses an existing one). Every subsequent run on "the same app" loads the **same `app_key`** into its Mentor session — that's the identity pin.

- ✅ Right: note the `app_key` from the first build in the working folder (`design-to-app/<APP_NAME>/build-notes.md`) and load that same app for every subsequent build against `APP_NAME`.
- ❌ Wrong: every run creates a new app with a fresh name (`HomeBanking_v1`, `HomeBanking_v2`, ...). New asset every time.

## Describe only what changes

When the app already has the screens, a follow-up prompt on it describes only what's CHANGING, not what's already in the app: restating the whole app makes Mentor rebuild or duplicate existing screens and elements. Re-send the full spec only to an app whose earlier build didn't land (empty or never published).

## How to detect mistakes

If you find yourself with `HomeBanking_v1`, `HomeBanking_v2`, `HomeBanking_v3` in your tenant, you've broken the identity pin. The fix: pick the latest one, note its `app_key` in the working folder, and load it on the next run.
