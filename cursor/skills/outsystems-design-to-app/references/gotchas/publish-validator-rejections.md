# A publish can fail after Mentor reports success

**The trap:** Mentor finishes the turn and reports the app as built, but the publish then fails with an OutSystems build-engine code (`OS-*`, e.g. **OS-APPS-40028** "Input binary does not contain a valid OML", or an `OS-BEW-*` / `OS-DPL-*` code). Mentor's success means the model was accepted, not that the server-side publish validator will accept it.

**Why it matters:** a failed publish carrying an `OS-*` code is the build's own result. Re-publishing the same revision fails the same way, and "validator rejected, try again" tells the user nothing.

## What to do when a publish fails

1. Read `publish_logs` for the publication and find the `OS-*` code and its reason text.
2. Report the code and its likely cause in plain terms (which screen, widget or construct the reason names).
3. Do NOT blindly re-publish. Send Mentor a further turn on the same session that names the failing construct and asks it to fix it (and not to publish), then confirm with the user and publish once that turn is complete.

## Known construct to tell Mentor to avoid

- **Extra children on RadioGroup / ButtonGroup.** Both widgets are created with their own child items. Adding more items on top of the auto-created ones produces a duplicate-child OS-APPS-40028. Tell Mentor to reuse and edit the existing items rather than appending new ones.
