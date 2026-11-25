---
description: "Extract a requirements spec collection from legacy sources (Notes .dxl / AB Suite .pmodel / MS Access / AS/400 (DDS, RPG and CL source) / AS/400 with CA 2E or Synon model exports / COBOL / Java / .NET / Node.js), the out-of-app port of the /extract-requirements workflow. Hands off to /workflow-legacy-app."
argument-hint: "<absolute path to the source tree or .dxl> [customer name]"
---

<!-- steps: detect, extract, review, report -->

# /extract-requirements — Claude Code host

The explicit entry point for Skill **`legacy-requirements-extraction`**, which also
triggers on its own whenever the user asks for the specs or requirements of some legacy
source code. Either way, run the steps below.

The same workflow id, step order and gate as `extract-requirements` in
[`app/lib/workflows.py`](../app/lib/workflows.py), which stays the **source of truth** for the
full node text — read it there if a step below is ambiguous. This file records only what
differs when you run in plain Claude Code instead of inside the app-generator chat UI.

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

Treat `$ARGUMENTS` as the source path and, if given, the customer name. Do not guess a
customer name — ask.

## Running the extraction in this host

The app runs the extractor as an in-process MCP server (`mcp__extractor__detect_source`,
`mcp__extractor__run_extraction`). Those tools do not exist here, and you do not need them:
the same pipeline is served remotely as the **`modernize_*` tools on the user's OutSystems
MCP**. Check that MCP's tool list at runtime and call the tools by their bare names. If
`modernize_session_start` is listed, use it; do not tell the user the extraction can't run.

1. `modernize_session_start` → `mentor_session_id`, `token`, `uploads`. Pass the id and
   token to every later call.
2. **Prepare the source, then upload it.** The upload leaves the machine, so send only
   what the extractor reads:
   - A Notes `.dxl`: strip the stored records first. The extractor reads the design (forms,
     views, agents, script libraries), not the data, and a real export is mostly customer
     records. The rule is the pipeline's own: every `<document>` / `<profiledocument>`, and
     every `<note>` whose `class` is `document` or `profiledocument`, keeps its tag and
     attributes and loses all its children. Run it as a script (it needs `python3`); if it
     fails, stop and tell the user. Never upload an unredacted `.dxl`. The prolog check
     refuses DTD entity declarations, which Domino never writes, so an entity bomb can't
     exhaust memory on an older Python. `<profiledocument key=...>` can still carry a user
     name, so don't claim the upload holds no personal data.

     ```python
     import sys, pyexpat, xml.etree.ElementTree as ET
     RECORDS = {"document", "profiledocument"}

     class Prolog(Exception): pass
     def deny(*_): raise ValueError("DTD entity declarations are not allowed in a DXL")
     def root(*_): raise Prolog
     guard = pyexpat.ParserCreate()
     guard.EntityDeclHandler, guard.StartElementHandler = deny, root
     with open(sys.argv[1], "rb") as f:
         try:
             guard.ParseFile(f)
         except Prolog:
             pass

     def is_record(el):
         tag = el.tag.rsplit("}", 1)[-1]
         return tag in RECORDS or (tag == "note" and (el.get("class") or "").strip().lower() in RECORDS)

     ET.register_namespace("", "http://www.lotus.com/dxl")
     tree = ET.parse(sys.argv[1])
     for el in tree.iter():
         if is_record(el):
             for child in list(el):
                 el.remove(child)
             el.text = el.tail = None
     if any(is_record(el) and (len(el) or el.text or el.tail) for el in tree.iter()):
         sys.exit("a record kept its body")
     tree.write(sys.argv[2], xml_declaration=True, encoding="utf-8")
     ```
   - A source tree: copy it into a fresh staging directory, replace each `.dxl` in the copy
     (match the extension in any case: `APP.DXL` is a Notes export too) with its redacted
     output (never keep the original next to it), and zip only the staging copy. Leave out
     symlinks, files outside the tree, and these directories:
     `.git`, `.venv`, `node_modules`, `__pycache__`, `generated-specs`, `.modernize`,
     `reports`, `agent-spec`, `previews`, `.chat_state`, `.claude` and `.cursor`
     (`.chat_state` can hold sign-in tokens).
   - `uploads` is `presigned`: call `modernize_upload_url_create` with the filename and
     `size_bytes`, the prepared file's exact size in bytes, then HTTP `PUT` its raw bytes
     to `upload_url` with the returned `headers` (just `Content-Length`, which `curl -T`
     and any other HTTP client set from the body). The URL is signed for that one size,
     so a body of any other length is refused with `403`: if the file changed, ask for a
     new URL instead of retrying. Never route the bytes through the conversation. Before
     sending anything, check that `upload_url` starts with `https://` and that its host
     is a name, not `localhost`, an IP address, or a private or link-local address. If it
     isn't, don't send the source: stop and report the URL's host.
   - Otherwise: `modernize_source_upload` with the prepared file as base64 `content_b64`.
     It is bounded by `max_inline_bytes`, so use it only for small files.
3. `modernize_run_start` with `source_ref`, `customer` and `source` (`auto` unless you know the
   stack) → `run_id`. For a redacted `.dxl`, also pass `client` (the Domino organisation:
   read it from the original export before redacting, or ask the user). Redaction removes
   most of the evidence the service would infer it from. The default is headless: the service
   authors the whole spec, Business Spec included, so no authoring round trip comes back to
   you. There is no engine choice to pass; the service picks the analysis for the stack.
4. Poll `modernize_run_get` every 15 to 30 seconds, passing back its `cursor`, until `done`.
   A run takes about 10 minutes, so polling faster only adds tool calls. When it is done,
   read `status`: `succeeded` and `gates_failed` both go to step 5 (a `gates_failed`
   collection is still published, and `review` needs it). `input_required` happens only
   with `caller_authored=true`: it is a checkpoint, not an error, so keep the session open,
   author the `request` and call `modernize_run_start` again with `step_responses` (see `extract` below).
   Anything else is an error below.
5. On success, get the spec zip into a file: download `os_spec_url` (a presigned GET, held
   to the same `https://` and host check as `upload_url`) with a 50 MiB cap (`curl
   --max-filesize 52428800`), or decode `spec_zip_b64`, refusing it before decoding if it is
   longer than 69,905,130 characters (50 MiB once decoded). Then unpack it into the working
   directory, one folder per run, `./generated-specs/<customer>/<extraction_id>/` (the
   `extraction_id` `modernize_run_start` and `modernize_run_get` return), so a second run for
   the same customer never clashes with the first, with the script below, never a bare
   `unzip`: it allows at most 500 regular files and 50 MiB unpacked, counted while writing,
   and refuses links, devices and any member that would land outside the directory. It
   unpacks into a temporary directory and creates the run folder only when every check
   passed, and refuses if it already exists, so nothing is ever overwritten: a refused
   archive never creates the run folder and leaves every existing file untouched (only an
   empty parent folder may remain on a customer's first run): report the refusal and delete
   nothing. That directory is what `review` reads. If the download fails, poll
   `modernize_run_get` again for a freshly signed `os_spec_url` before giving up: closing
   the session deletes the published zip too. Save the script as `unpack_spec.py` and run
   `python3 unpack_spec.py <spec.zip> ./generated-specs/<customer>/<extraction_id>` (the
   second argument is the run folder itself, not its parent).

   ```python
   import os, shutil, stat, sys, tempfile, zipfile
   from pathlib import Path
   MAX_FILES, MAX_BYTES = 500, 50 * 1024 * 1024

   src, dest = Path(sys.argv[1]), Path(os.path.abspath(sys.argv[2]))
   if src.stat().st_size > MAX_BYTES:
       sys.exit("the spec zip is over 50 MiB")
   dest.parent.mkdir(parents=True, exist_ok=True)
   tmp = Path(tempfile.mkdtemp(dir=dest.parent)).resolve()
   try:
       with zipfile.ZipFile(src) as zf:
           members = [m for m in zf.infolist() if not m.is_dir()]
           if len(members) > MAX_FILES:
               sys.exit("the spec zip has more than 500 files")
           for m in members:
               if stat.S_IFMT(m.external_attr >> 16) not in (0, stat.S_IFREG):
                   sys.exit(f"not a regular file: {m.filename}")
               if not (tmp / m.filename).resolve().is_relative_to(tmp):
                   sys.exit(f"outside the directory: {m.filename}")
           written = 0
           for m in members:
               target = (tmp / m.filename).resolve()
               target.parent.mkdir(parents=True, exist_ok=True)
               with zf.open(m) as r, open(target, "wb") as w:
                   while chunk := r.read(1 << 16):
                       written += len(chunk)
                       if written > MAX_BYTES:
                           sys.exit("the spec zip unpacks to more than 50 MiB")
                       w.write(chunk)
       try:
           dest.mkdir()
       except FileExistsError:
           sys.exit(f"the run folder already exists, not overwritten: {dest}")
       for entry in tmp.iterdir():
           entry.rename(dest / entry.name)
   finally:
       shutil.rmtree(tmp, ignore_errors=True)
   ```
6. `modernize_session_close`. It deletes the uploaded source, so call it on **every** path
   once a session exists: after the download, and also when you give up (an error, a
   download that still fails after a fresh URL, a fallback). Ignore an `unknown_session`
   from the close.

Treat the session `token`, `upload_url` and `os_spec_url` as credentials: use them, never
print them or put them in a report. Errors the tools return by name:
- `tenant_not_enabled`: don't retry. Give the user the limited-availability
  message below, word for word.
- `stack_not_enabled`: this service doesn't take that stack yet. Say which stack, then use
  the fallbacks below.
- `too_many_sessions` (on start): retry shortly.
- `direct_upload_unavailable` (from `modernize_upload_url_create`): this service takes inline
  uploads only. Send the file with `modernize_source_upload` instead, but only if the
  prepared file fits the session's `max_inline_bytes`. If it doesn't, this session has no
  upload method that can take it: say so, close the session and use the fallbacks below.
- `bad_size` (from `modernize_upload_url_create`): the call went out without the file's exact
  size. Read the prepared file's size in bytes, pass it as `size_bytes`, and ask again.
- `storage_unavailable` or `service_unavailable`: a temporary fault on the service. Retry
  shortly, once or twice, then report it and use the fallbacks below.
- `upload_missing`: the PUT didn't land. PUT again to a fresh `upload_url`, then start the run.
- `source_too_large` or `source_unparseable`: resending the same bytes won't help, and a
  `size_bytes` over the cap is refused before a URL is signed. Ask the user for a smaller
  or re-exported source.
- `analysis_incomplete` or `pdf_unavailable` (a terminal poll): the service couldn't finish
  the analysis or render the Business Spec PDF. Don't retry the same source; report it and use
  the fallbacks below.
- `run_lost` or `run_failed` (a terminal poll): the session is still good. Start the run
  again with the same `source_ref`; this is a new parse, not a resume. If the error says
  the source did not survive, upload again in this session first. Retry once at most.
- `too_many_runs`: from `modernize_run_start`, the session is at its run cap, so close it, open
  a new session, upload again and start the run once more. As a terminal poll (the run stayed
  queued too long) the session is fine: start the run again.
- `unknown_session`: the session is gone. Open a new one, upload again and start the run once
  more. A second failure is a real failure: report it and use the fallbacks below.
- `gates_failed`: download it (step 5) and review it, but the collection is incomplete.
  Report the run's `failed_checks` when it carries them. Without `failed_checks`, say which
  checks failed isn't available: the gate reports stay on the service and aren't in the spec
  zip. Never present it as a complete spec.
- `warnings` on a finished run: quote each one in the report. A warning that says "Do not
  report this run as a complete spec" makes the spec incomplete, whatever `analysis` says:
  the extractor ends each of its incomplete-run warnings (standard analysis, degraded run)
  with that sentence. Name the causes from `analysis_incomplete` when the result carries
  them. Any other warning (a simplified or skipped PDF) never makes the spec incomplete.
- A finished run with a non-empty `analysis_incomplete` list, whatever `analysis` says, is
  incomplete: a pass fell short. The usual case is a Notes, AB Suite, MS Access or AS/400
  run, which has no `analysis` field, that degraded past part of its derived layer. Name the
  causes and never present it as a complete spec.
- `analysis: standard` on a finished run (`succeeded` or `gates_failed`): standard analysis
  (the extractor's own parsers plus the LLM) wrote the spec. With AWS Transform off, every
  COBOL, Java, .NET and Node.js run comes back `standard`; a stack that doesn't run this
  analysis carries no `analysis`. Then read `analysis_complete`: `true` means standard
  analysis read every program with nothing skipped, so the spec is complete. Not `true`
  means the spec is structural and incomplete even when its status is `succeeded`:
  download and review it, say it's structural in the report, name the causes listed in
  `analysis_incomplete` (on the result when it carries them, otherwise in the published
  `manifest.json`), and never present it as a complete spec. Don't re-run it: the same
  source takes the same path.

**If the OutSystems MCP has no `modernize_*` tools**, check sign-in first: an OutSystems
MCP that isn't signed in, or a session started before sign-in, lists no tools either. Not
signed in → say so, tell the user how to sign in (Claude Code: `/mcp`, pick the
`outsystems` server, Authenticate; elsewhere, the host's MCP settings for that server) and
to start a new session afterwards, and stop. See
[Authorize before you run](../README.md#authorize-before-you-run). Only when the MCP is
signed in, in a session started after sign-in, and still lists no `modernize_*` tools is
the tenant without access yet: the extraction isn't missing from this host, it runs as
those tools. Tell the user, in these words: *"Legacy modernization is in limited availability and isn't enabled for your tenant yet. Contact OutSystems if you'd like access."* Then stop: without access,
don't fall back to a prior spec collection or a draft.

**If the service doesn't take the source's stack** (`stack_not_enabled`), fall back in
this order:

1. **The user already has an extracted spec collection** (the 13 domain slices +
   `manifest.json` + `requirements.json` + Business Spec, from a prior run). Point the
   `review` step at it and continue.
2. **Neither** → stop and say so. Do NOT hand-write a spec collection: a fabricated
   `requirements.json` is worse than no extraction, because the next workflow trusts
   it. What you MAY offer instead is a plainly-labelled **agent-derived requirements
   draft**: read the sources yourself and produce requirements where every single item
   carries a source citation (`path/file.ext:line`); anything uncited is marked
   `(proposed)`. Label the deliverable as agent-derived — it is an input for human
   review, never a substitute for the pipeline's spec collection, and `/workflow-legacy-app`
   must be told which kind of input it is getting.

## Steps

**1. `detect`** — Find the source. Look at `$ARGUMENTS` first, then the working directory for
an attached tree or `.dxl`. Name the **absolute** path of the most specific directory holding
ONE app's sources. A backend with its own front end is one app and one run: pass the
directory that holds both and don't split it, and don't re-run to get a longer screen list.
Detection picks the backend stack for that tree, so pass `source: auto` to
`modernize_run_start` and don't override `source` to force the front-end stack. A front end in a separate repo is not covered by one
run: say so and ask the user what to attach. Don't guess. When the
backend was detected, don't wait on the answer: run the backend alone, and name the
missing front end as a gap in the report. Attaching it later means a new run on one
directory that holds both.
If it is ambiguous or absent, stop and tell the user exactly what to
attach — do not proceed on a guess.

**2. `extract`** — Run it through the `modernize_*` tools (above), or, when the service doesn't
take the stack, the user supplies a prior run's output (fallback 1) and you read it. On the remote path the service authors every step itself; the notes below apply
when you author the steps yourself. With `modernize_run_start` and `caller_authored=true`, a run
that needs you ends `status=input_required` with a `request` to author and an opaque
`pending_step` token (`step-1`, `step-2`, and so on). Call `modernize_run_start` again with
`step_responses` mapping that token to your answer, keep every earlier token's answer in the
map, and poll the new run. `unknown_step` means you answered a token the service never
issued. Two source families behave differently and the difference matters:

- **Notes (.dxl) / AB Suite (.pmodel) / MS Access / AS/400 (DDS, RPG and CL source) /
  AS/400 with a CA 2E or Synon model export**: the first step's `request` carries the parsed facts. Author the
  answer **strictly from those facts**, following its `response_schema` exactly. Never
  invent an entity, screen or rule the facts do not support. On a local run the same step
  is `status=enrichment_required` with an `enrichment-request.json`; re-run with
  `--enrichment-response`. Rejected twice → fall back to `deterministic=true` /
  `--deterministic` and **record the downgrade** in the report.
- **COBOL / Java / .NET / Node.js**: the service runs standard analysis itself, from the
  raw source. There is no engine to pick: never ask the user for AWS credentials and never
  offer AWS Transform as a fix. A run capped by its budget (`budget_exhausted: true`) or
  refused with `stack_not_enabled` is a shortfall to record, not a thing to work around.

**3. `review`** — This is yours, and it is the step that catches real problems. Verify the
published version directory has all **13 domain slices** (`00-overview.md` …
`12-unknowns.md`), `manifest.json`, `requirements.json` and the Business Spec, each
non-empty. Read `manifest.json` and `requirements.json` and check the entity and screen names
genuinely come from the sources — not from the model's imagination. A spec is
**incomplete** when it is an incomplete standard analysis (`analysis: standard` and
`analysis_complete` not `true`), a degraded run (a non-empty `analysis_incomplete` list,
whatever `analysis` says), or a run whose warnings say "Do not report this run as a complete
spec". Read the structured fields first; the extractor ends each of its incomplete-run
warnings with that sentence, so it also catches a degraded run that carries no
`analysis_incomplete`. An incomplete spec fails a check here even when its gates are green, and it never
passes the gate, whatever the pass rate: name it as a structural or degraded spec, name the
causes and quote each warning. Any other warning is quoted in the report and fails no check.

Then read the Business Spec and check it is **business-only**: what is expected, and nothing
about how it will be built. No OutSystems/ODC constructs, no technology or architecture
choices, no code, no build steps, no migration plan, phases or effort, no "what we do next".
One labelled section is the exception: the extractor's **Recommended migration**, a suggestion
for the business to review. Everything inside it is allowed: the suggested apps and their waves,
the diagram of how they connect, the libraries and the kind of each app (web, mobile, workflow,
AI agent), and whatever else the section holds, such as user groups, a size table, the first
go-live and risks. The same content anywhere else in the spec is leakage.
**Every main Business Spec** should carry that section, whatever the number of domains (the
per-domain and application-wide reports don't). A missing section is a **recorded finding**, not
a failing check: the spec came from an extractor that predates the section and a re-run can't add
it, so leave it out of the pass rate, never loop back to `extract` for it, and name it in the
report with the durable fix in the extractor. It comes in one of two forms, both valid: the ordered plan
(apps, waves and the diagram) when enough domains link to each other, or a short form that says
to **migrate it as one app**, followed by the other OutSystems assets to consider (libraries,
workflows, AI agents).
Implementation leakage is a **failing check** — name the section and the leaked content, and
record that the durable fix belongs in the extractor's Business Spec generation, not in a
hand-edit of the output.

**4. `report`** — When the source has a front end, compare its routes with the screens in
`02-screens.md` and `requirements.json`. If the spec has no screens, or far fewer than the
front end's routes, say so in the report: name the framework and roughly how many routes you
see in the source, and say that a build from this spec with `/workflow-legacy-app` will be
missing those screens. Don't split the source and don't re-run: neither gives a longer
screen list. When the front end is in a separate repo that wasn't attached, say so too: the
spec has none of its screens, and a build from this spec will be missing them.

There is no built-in Files canvas here, so `mcp__preview__show_file` has
no substitute: **print the absolute path of every artifact** the run produced — the
Business Spec first, then all 13 slices, then `manifest.json`, `requirements.json` and, on a
local run, `pipeline-events.jsonl` (the remote spec zip doesn't carry it). Do not summarise a subset; the user has to be able to open each
one. Printed paths are the floor, not a fallback to reach for only when nothing better
exists: when this host has a canvas-equivalent surface — most harnesses put one on the
right-hand side of the window (a side canvas, an IDE preview panel, an artifact-publishing
tool) — **open the Business Spec there**, not just in a chat-inline preview, so it stays
visible next to the conversation; prefer the PDF over the markdown when both exist, since
that's the one artifact a human reader actually opens. Then state: detected stack,
customer, version directory, domain count, REQ counts per tier, gate status (with
`failed_checks` on `gates_failed`), the run's `analysis` and `analysis_complete`, every
warning, and any enrichment downgrade or capped run. When the spec is incomplete
(`analysis: standard` without `analysis_complete: true`, a non-empty `analysis_incomplete`
list whatever `analysis` says, or a warning that says "Do not report this run as a complete
spec"), lead with it, before the summary, right after the `gates_failed` verdict when the run
has one: say the spec is incomplete (structural for a standard analysis, degraded otherwise),
name the causes and quote every warning. Tell `/workflow-legacy-app` it's building from an
incomplete spec. Name every recorded
finding (a main Business Spec without the Recommended migration section, with the fix in the
extractor). Close by pointing at
`/workflow-legacy-app` to build the app from this extraction.

## Gate — after `review`

Pass when the artifact/gate checklist is at **≥ 95 %** *and* the run status is `succeeded`
*and* the spec is not incomplete (see `review`), which never passes whatever it scores.
On FAIL, loop back to `extract` — fix the input path, re-author the enrichment response, or
fall back to deterministic — up to **5** re-runs. Report `pass_rate_pct` and `reruns_used` on
every crossing.

If the extract carried `budget_exhausted: true`, the loop must **switch path** (offline /
deterministic) rather than repeat a capped live analysis run. When no offline path exists for that
stack, stop looping, go to `report`, and record the shortfall.

An incomplete spec (an incomplete standard analysis, a degraded run with a non-empty
`analysis_incomplete` list whatever `analysis` says, or a run whose warnings say "Do not report
this run as a complete spec") never passes the gate, whatever its status, and a re-run takes the same path.
Don't loop on it: go to `report` and lead with it.

A main Business Spec without the Recommended migration section is a recorded
finding, not a failing check: it is not in the pass rate and is never a reason to loop.

## Tracking progress without the app's canvases

| in the app | here |
|---|---|
| `mcp__workflow__update_workflow` (the live flowchart) | a **Progress** checklist you restate in every reply, one line per step with its state |
| `mcp__plan__update_plan` | the native `TodoWrite` tool |
| `mcp__preview__show_file` | print the absolute path, and open the Business Spec (PDF preferred) on the host's canvas-equivalent when one exists — most harnesses put this on the right-hand side of the window (a side canvas, an IDE preview panel, an artifact-publishing tool), not just a chat-inline preview |
| `mcp__extractor__*` | the **`modernize_*`** tools on the user's OutSystems MCP (above). If those are absent too, check sign-in first (above); signed in, in a session started after sign-in, and still absent means the tenant has no access yet: give the limited-availability message (above) and stop |

Keep the checklist honest: a step that was skipped says skipped, and the gate's
`pass_rate_pct` is a number you computed, not a vibe.
