---
name: legacy-requirements-extraction
description: >-
  Extract a requirements spec collection (13 domain slices, manifest.json, requirements.json and a Business Spec) from a legacy application's source code (Lotus Notes .dxl, AB Suite .pmodel, MS Access, AS/400 (DDS, RPG and CL source), AS/400 with CA 2E / Synon model exports, COBOL, Java, .NET or Node.js) through the modernize_* tools on the user's OutSystems MCP. Use whenever the user points at legacy source and asks to extract, generate, derive or write its specs, requirements, business specification, documentation or "what the app does", or to analyse it before a migration, even if they never type /extract-requirements. Not for: building a new app from a brief or a design, with no legacy source -> outsystems-spec-driven-build or outsystems-design-to-app (outsystems plugin); an already-extracted spec collection to build from -> the /workflow-legacy-app command.
license: MIT
compatibility: Any Agent Skills host with an OutSystems MCP whose tenant is enabled for legacy extraction (the modernize_* tools). Needs a shell to zip a source tree and HTTP PUT a presigned upload. No scripts — pure guidance.
allowed-tools: Read Glob Bash Write Skill TodoWrite mcp__outsystems__auth_status mcp__plugin_outsystems_outsystems__auth_status mcp__outsystems__authenticate mcp__plugin_outsystems_outsystems__authenticate mcp__outsystems__modernize_session_start mcp__plugin_outsystems_outsystems__modernize_session_start mcp__outsystems__modernize_upload_url_create mcp__plugin_outsystems_outsystems__modernize_upload_url_create mcp__outsystems__modernize_source_upload mcp__plugin_outsystems_outsystems__modernize_source_upload mcp__outsystems__modernize_run_start mcp__plugin_outsystems_outsystems__modernize_run_start mcp__outsystems__modernize_run_get mcp__plugin_outsystems_outsystems__modernize_run_get mcp__outsystems__modernize_session_close mcp__plugin_outsystems_outsystems__modernize_session_close
metadata:
  version: "1.0.0"
  author: outsystems-r-and-d
---

# Legacy requirements extraction

The `/extract-requirements` command is the explicit entry point; this skill is
what runs whether the user typed the command or simply asked for the specs of
some legacy source ("use this source code and extract the specs"). Either way
the extraction runs on the **OutSystems legacy extraction service**, never by
reading the code and writing the spec yourself.

## Route first

| The user has | Run |
|---|---|
| Legacy source code (a tree, a zip, a `.dxl`) and wants its specs or requirements | **this skill** |
| A spec collection that is already extracted, to build from | the `/workflow-legacy-app` command |
| A request, brief or design for a new app, no legacy source | the `outsystems` plugin's Skill `outsystems-spec-driven-build` (a written brief) or `outsystems-design-to-app` (a design) |

When the plugin's `extract-requirements` command is installed, **follow its
steps exactly** (`detect`, `extract`, `review`, `report`, and its gate): it is
the source of truth for upload preparation, error codes, the review checklist
and the report. The flow below is the core of its `extract`
step, so a skills-only install can still run the extraction.

## Before the first call

- **The OutSystems MCP must be authenticated before anything else.** Attaching
  the server is not signing in to it, and an unauthenticated OutSystems MCP
  usually lists none of its real tools, often only `authenticate` or
  `auth_status`. So a missing tool is an authentication question first. Call
  `auth_status` when it is listed; when `authenticate` is listed, run it and
  give the user the sign-in link it returns. On `AuthError`, re-authenticate
  once and retry the original call. **Still not authenticated → make it the
  first line of your reply**: "The OutSystems MCP is not authenticated, so
  the extraction cannot run." Then say how to sign in on this host (Claude Code:
  `/mcp`, pick the `outsystems` server, Authenticate; elsewhere, the host's MCP
  settings for that server), that the session must be **restarted after
  signing in** (a session keeps the failed connection it started with), and
  stop. See [Authorize before you run](../../README.md#authorize-before-you-run).
  Never report an unauthenticated server as a missing feature, a disabled
  tenant or an outage, and never work around it.
- **Check the installed skills are current.** Plugin version of this copy: `3.0.1`.
  Read the latest released version from the plugin's `.claude-plugin/plugin.json`:
  `gh api repos/OutSystems/outsystems-mcp/contents/legacy-modernization/.claude-plugin/plugin.json --jq .content | base64 --decode`,
  or, without `gh`, `curl -fsSL https://raw.githubusercontent.com/OutSystems/outsystems-mcp/main/legacy-modernization/.claude-plugin/plugin.json`.
  If its `version` is newer than this copy's, say so once, right after the authentication check:
  the version loaded, the version current, and how to update on this host. On
  Claude Code that is `claude plugin marketplace update outsystems`, then
  `claude plugin update legacy-modernization@outsystems`; on other hosts,
  the plugin README's update table. An update takes effect in a **new** session.
  Then carry on: an old copy still runs, the user just loses what changed. If
  neither command can reach the repo, say the check was skipped and carry on.
- **Find the source.** Name the absolute path of the most specific directory
  (or single file) holding ONE application's sources. Ambiguous or absent →
  ask the user exactly what to point at; do not guess.
- **Never split a full-stack repo into two runs.** A backend (Java, .NET,
  Node.js) with its own front end (Angular, React, Vue) alongside it, for
  example a `package.json` beside a `pom.xml`, is still ONE application and
  gets ONE run, pointed at the directory that holds both, which is often the
  repo root. Detection picks the backend stack for that tree, so pass
  `source: auto` to `modernize_run_start` and don't override `source` to
  force the front-end stack.
  Nothing downstream merges two spec collections for one app, so a split run
  gives two incomplete specs instead of one complete one. Separate
  applications in one repo (independent services, each with its own UI and
  data) are still one run each, per the bullet above. A front end in a
  separate repo is not covered by one run: say so and ask the user what to
  attach. Don't guess. When the backend was detected, don't wait on the
  answer: run the backend alone, and name the missing front end as a gap in
  the report. Attaching it later means a new run on one directory that holds
  both.
- **Ask for the customer name** if the user did not give one. Do not invent it.
- **Then check the tool list.** Authenticated and `modernize_session_start` is
  listed → use the tools below by their bare names. Authenticated but it is not
  listed → the tenant has no access yet. Tell the user, in these words:
  *"Legacy modernization is in limited availability and isn't enabled for your tenant yet. Contact OutSystems if you'd like access."* Then stop.
  No OutSystems MCP attached at all → say so and point at the plugin README's
  [If OutSystems MCP is not installed](../../README.md#if-outsystems-mcp-is-not-installed).
  In every one of these cases, never hand-write a spec collection: the next
  workflow trusts it.
- **Confirm the tenant** when more than one OutSystems MCP is attached; the
  extraction runs, and its upload lands, on whatever tenant that server points at.

## The flow

1. `modernize_session_start` → `mentor_session_id`, `token`, `uploads`. Pass the
   id and token to every later call.
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
   - A single file that is not a `.dxl` goes as it is.
   - `uploads` is `presigned` → `modernize_upload_url_create` with the filename and
     `size_bytes` (the prepared file's exact size in bytes), then HTTP `PUT` its raw
     bytes to `upload_url` with the returned `headers` (just `Content-Length`). The URL
     is signed for that one size, so a body of any other length is refused with `403`:
     ask for a new URL instead of retrying. A missing `size_bytes` is `bad_size`.
     Otherwise → `modernize_source_upload` with base64 `content_b64`, small files only
     (`max_inline_bytes`). Never route the bytes through the conversation. Before sending
     anything, check that `upload_url` starts with `https://` and that its host is a name,
     not `localhost`, an IP address, or a private or link-local address. If it isn't,
     don't send the source: stop and report the URL's host.
3. `modernize_run_start` with `source_ref`, `customer` and `source` (`auto` unless
   you know the stack) → `run_id`. For a redacted `.dxl`, also pass `client` (the
   Domino organisation: read it from the original export before redacting, or ask the
   user). The default is headless: the service authors the whole spec, so nothing
   comes back for you to write.
4. Poll `modernize_run_get` every 15 to 30 seconds, passing back its `cursor`,
   until `done`.
   Between polls, wait with the host's background mechanism and end the turn (the
   main `outsystems` skill's rule: no bare `sleep`), and give the user one line per
   pause. Poll from this conversation: the `status-watcher` agent has no
   `modernize_*` tools.
   `succeeded` and `gates_failed` both publish a spec; anything
   else is an error to report with its `code`. Then read `analysis` and
   `analysis_complete`. `standard` means standard analysis (the extractor's own
   parsers plus the LLM) wrote the spec; with AWS Transform off, every COBOL, Java,
   .NET and Node.js run is `standard` (a stack that doesn't run this analysis carries
   no `analysis`). `analysis_complete: true` means it read every program with nothing
   skipped, so the spec is complete. `standard` with `analysis_complete` not `true` is
   a structural, incomplete spec even on `succeeded`: report it as structural, name
   the causes listed in `analysis_incomplete` (on the result when it carries them,
   otherwise in the published `manifest.json`), and never present it as a complete
   spec. Re-running takes the same path, so don't. There is no engine to pick: never
   ask for AWS credentials or offer AWS Transform. On `gates_failed`, report the run's `failed_checks` when present;
   without them, say which checks failed isn't available (the gate reports never
   leave the service).
5. Get the spec zip into a file: download `os_spec_url` (same `https://` and host
   check as `upload_url`) with a 50 MiB cap (`curl --max-filesize 52428800`), or
   decode `spec_zip_b64`, refusing it before decoding if it is longer than
   69,905,130 characters (50 MiB once decoded). Unpack it under the working
   directory, one folder per run, `./generated-specs/<customer>/<extraction_id>/`
   (the `extraction_id` `modernize_run_start` and `modernize_run_get` return), so a
   second run for the same customer never clashes with the first, with this script,
   never a bare `unzip`: at most 500 regular files and 50 MiB unpacked, no links,
   devices or members outside the directory. It unpacks into a temporary directory
   and creates the run folder only when every check passed, and refuses if it
   already exists, so nothing is ever overwritten: a refused archive never creates
   the run folder and leaves every existing file untouched (only an empty parent
   folder may remain on a customer's first run): report the refusal and delete
   nothing. Save the script as `unpack_spec.py` and run
   `python3 unpack_spec.py <spec.zip> ./generated-specs/<customer>/<extraction_id>`
   (the second argument is the run folder itself, not its parent).

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
6. `modernize_session_close` on **every** path once a session exists — after the
   download, and also when you give up. It deletes the uploaded source.

Treat the session `token`, `upload_url` and `os_spec_url` as credentials: use
them, never print them or put them in a report. On `tenant_not_enabled` or
`stack_not_enabled`, don't retry: say which tenant or stack, and stop.

## After the run

Check the collection is complete — the 13 slices (`00-overview.md` …
`12-unknowns.md`), `manifest.json`, `requirements.json` and the Business Spec,
each non-empty — and that entity and screen names come from the source. A run with
`analysis: standard` and `analysis_complete` not `true`, a degraded run (a
non-empty `analysis_incomplete` list, whatever `analysis` says), a warning that says
"Do not report this run as a complete spec", or `gates_failed` is not complete, however the
files look: say so first, quote each warning, and quote the `failed_checks` when
the run has them (otherwise say which checks failed isn't available). Any other
warning is quoted, but it doesn't make the spec incomplete.

When the source has a front end, compare its routes with the screens in
`02-screens.md` and `requirements.json`. If the spec has no screens, or far
fewer than the front end's routes, say so in the report: name the framework
and roughly how many routes you see in the source, and say that a build from
this spec with `/workflow-legacy-app` will be missing those screens. Don't
split the source and don't re-run: neither gives a longer screen list.
When the front end is in a separate repo that wasn't attached, say so too:
the spec has none of its screens, and a build from this spec will be missing
them.

Then print the absolute path of every artifact, the Business Spec first, and point
the user at `/workflow-legacy-app` to build the app from this extraction (telling it
when the spec is a structural one).

### Open the Business Spec PDF on the canvas

The Business Spec PDF is what a person actually reads, so put it in front of
them. When the host has a canvas or preview surface, open the PDF there, next to
the conversation, not just as a link in the chat:

| Host | Where the PDF goes |
|---|---|
| A chat UI with a Files or document canvas | the canvas's own open-file tool, with the PDF's path |
| Cursor, Kiro and other VS Code-based IDEs | open the PDF in an editor tab with its absolute path, or in the simple browser panel with its file URI |
| Any host with a browser MCP (Claude Code, Codex, …) | navigate the browser page to the PDF's file URI; browsers render PDFs natively |
| No canvas, preview or browser surface | print the path only, and say there is no surface to open it on |

- Build the file URI with the platform's own conversion, for example
  `python3 -c 'import pathlib,sys; print(pathlib.Path(sys.argv[1]).resolve().as_uri())' "<path>"`,
  never by putting `file://` in front of the path: a Windows drive letter, a
  space or a `#` in the path would break the URI. Editor open-file tools take
  the plain absolute path.
- No PDF in the collection (for example after `pdf_unavailable`): open the
  Business Spec markdown instead, and say the PDF is missing.
- Say the PDF is open only when the host's tool confirmed it. If opening failed,
  say so and fall back to the printed path.
- Opening it never replaces printing the paths: do both.
