# Reporting your work — the Requirements & Implementation Report

Produce or update the Requirements & Implementation Report **only when the user
explicitly asks for one** (an "implementation report", "requirements report",
"migration report", "what did you build", a handoff document). Do **not** write
or rewrite the report on your own initiative just because a build finished — if
the user did not ask for a report, skip it entirely and do not add a reporting
step. **The one exception is an expired OutSystems sign-in:** when it stops a
run (the sign-in can't be renewed from inside the run, as the core prompt
describes), write or update the report without being asked, and say in
section 0 that it reflects the app as of the sign-in expiry. When they do ask,
produce a written report that measures the built app
**against the input requirements**: the source repo, the requirements file the
user provided, or their written brief. The report is a markdown file in your
workspace; write it, then push it to the canvas with `mcp__preview__show_file`
so the user reads it in the Files tab.

**Cover every spec file, point by point.** When the app was built from an
extractor-generated spec (the `/extract-requirements` output — `requirements.json`,
the `<Customer>-Business-Spec.md` business requirements doc, and the domain
slices, notably `04-business-rules.md` and `06-user-stories.md`) or any other
files carrying the business rules / user stories (e.g. a `business-rules.md` /
`user-stories.md` — `Glob` for them among the spec paths), the report
MUST walk **every** requirement, **every** individually-identified business
rule and **every** user story one by one — each REQ/BR/NFR/rule/story id with
its text — and state, per item,
its status in the fixed vocabulary (see "Report structure", with the
evidence: screen/action/entity that satisfies it), whether it was **tested**
(and the driven verdict), and — when it is not implemented or was not tested —
**why**. Do not summarize or sample; the tables have one row per source item
so the reader can trace all of them, and EVERY spec file in the extraction
input is represented in the report — implementable slices via their per-item
rows, meta slices (overview, non-functional, migration-disposition,
agentic-suggestions, unknowns) via at least a disposition note (honored /
deferred / open question). A spec file with no trace anywhere in the report
is a coverage bug.

The report is only as good as the verification behind it: run the FINAL GATE
(flow sweep + design comparison, see the testing guide above) **before**
writing — the report's flow table and statuses must come from tests you
actually drove this session, not from memory of what you built.

## The business-requirements deliverable is NOT the implementation report

Two different documents, and they must not bleed into each other:

- **The implementation report** (this guide's subject) measures the BUILT app
  against the requirements. Figma belongs here — the design-options section, the
  chosen direction, the implemented tokens, Exactness evidence.
- **The business-requirements document** — the `<Customer>-Business-Spec.md`
  business spec (and any PDF you render from it) — is the human-friendly version
  of the extractor's 13 domain slices. It states only **what the business needs**:
  requirements, business rules, user journeys, the meaning of the data, roles and
  who may do what, the processes the business runs.

**When you write, update, or render the business-requirements doc / PDF, keep it
business-only:**

- **No references to the Figma designs.** No Figma links or file/node URLs, no
  frame or page names, no design-option names ("Option A — Modern Light"), no
  screenshots of design frames, no design-token tables (colours, typography,
  radii, spacing), and no "matches the design" / fidelity claims. A business
  requirement is true regardless of which design won — mentioning the design
  dates the document and reads as scope it never had.
- **No implementation work either** — no OutSystems/ODC constructs (entities as
  tables, aggregates, screens as OML artifacts, server actions, blocks, timers,
  themes), no technology or architecture choices, no code, no build steps, no
  migration plan / phases / sequencing / effort / estimates, and nothing about
  what an agent or team will do next. "The system must block a checkout while a
  loan is overdue" belongs; "add an IsOverdue attribute and validate it in the
  CheckoutBook server action" does not.
- **One exception: the extractor's Recommended migration section.** When the
  extraction's Business Spec carries it, keep everything inside it as written
  and labelled as a suggestion to review: the suggested apps, waves, the diagram
  of how they connect, libraries and app kinds, and whatever else the section
  holds (user groups, a size table, the first go-live, risks). Don't add
  migration content anywhere else.
- Screens may be named as **user-facing capabilities** ("the member sees their
  active loans and due dates"), never as built artifacts or designed frames.
- Anything you'd otherwise be tempted to add — design direction, fidelity, the
  build plan — goes in the implementation report instead. If a requirement
  genuinely can't be stated without naming an implementation detail, that's a
  signal the requirement is under-specified: write the business intent and note
  the open question.

## Intermediate reports — the validator gate's copy of this report

In `/workflow-legacy-app` the **validator step** asks for this report too, in
**INTERMEDIATE mode**, before the ≥95% gate. That is not a different document:
it is this report, written exactly as this guide says (the same skeleton,
status vocabulary, spec ids, page-1 KPI cards and appendix Z), from that
scoring's `TestReport` and the `BuildReport`. Only three things differ:

- **Name**: `<AppName>-r<revision>-intermediate-report.md`, for the revision the
  validator scored. Each re-run loop scores a new revision, so it gets a new file.
- **Title**: `<App> — Requirements & Implementation Report (intermediate,
  validator loop <n>)`, and the opening `>` lead starts with *"Intermediate
  report: the validator gate's scoring of revision <revision>; the final
  report is this one, made final."*
- **Not yet in it**: the victory lap's findings and the Test Evidence Pack links
  (they come later). Say so in one line in section 0.

The gate reads this file: its pass rate is capped by the report's
"REQs implemented" figure, the spec ids whose appendix-Z row answers
Implemented Yes, over every spec id (report-local `IN-nn` / `CAP-nn` rows don't
count; it is the same number the page-1 card shows, and the checker fails a
card that says otherwise). `check_report_ids.py <requirements.json> <report.md>
--figure`, with the same `--business-spec` / `--spec` arguments as below, prints
it as `REQS IMPLEMENTED X of N (P%)` once the report passes the id check, with P
rounded down (the in-app server reads it the same way). So the statuses you
write here ARE the gate's score, and the report's numbers have to be right
before it is rendered.

The **final report** finishes the **last** intermediate one: copy it to
`<AppName>-r<revision>-report.md`, drop the intermediate title suffix and lead
line, keep its ids and statuses, and add the victory lap's findings, the
Test Evidence Pack links and anything else the final report needs. A status the
victory lap overturns is a discrepancy, not an edit: the final report's
`--figure` line may not be lower than the last intermediate report's (the
in-app `render_pdf` refuses it; outside the app, compare the two `--figure`
lines yourself), so the item goes back through the validator
gate (a re-run loop, then a new intermediate report) instead of quietly
lowering the final one.

## Self-contained packs (when copying to generated-specs)

If the handover HTML/PDF/MD is published under
an extraction pipeline output dir (`generated-specs/.../v{N}/`) (or any client-facing folder), it
must stand alone: **inline** residual scorecards and source↔client mapping
(or copy those markdown files into the same folder). Do **not** point at
workspace-only paths such as `app/workspace/<slug>/reports/residual-gaps.md` or
Exactness notes outside the pack. Full doc-pair shape: the
`outsystems-handover-docs` skill.

Your report-writing calls (screenshots, `show_file`) stream to the chat as chips
(the UI folds a run of same-family calls into one count card), so **say what
you're assembling in one line before a burst** — "Capturing live screenshots for
the five built screens" — then run the calls. One sentence before the burst;
don't narrate each individual call.

## Report structure — the shared skeleton (in this order)

The report walks the **same numbered sections as the extractor's Business Spec**
(0–9 plus appendix A), so "section 3" is the data model in both documents and a
reader can hold the two side by side (see "One document family with the
Business Spec" below for why, and for what may differ). The numbers are fixed: never renumber and
never drop a section. One that doesn't apply keeps its heading with a one-line
"Not applicable: <reason>" body. Report-only material goes in the appendices
after A, and the report always ends with appendix Z, the requirements
checklist. Keep the numbers consistent — the KPI cards, the section-5 requirements
list, the journeys table, the screens table and the appendix-Z checklist must tell ONE story (same totals
and denominators; an item can't PASS in one table and be Not built in another).

**Status vocabulary (fixed).** Every status cell in the report uses exactly one of
these, spelled out in words (never an icon on its own):

| Status | Means |
|---|---|
| Implemented, tested | built, and driven to PASS this session |
| Implemented, not tested | built, not fully driven to a verdict; the tested cell says PARTIAL, NOT TESTED or NOT OBSERVABLE, with why |
| Partial | present but incomplete; the evidence names which half works |
| Changed | built differently from what the spec asked; the evidence gives the reason and where it was agreed |
| Deferred | left for later by a named scope decision (who decided, why) |
| Not built | absent with no decision behind it |

A FAIL verdict lands on Partial or lower, never on an Implemented status. A
PARTIAL verdict means some criteria could not be driven, not that the build is
incomplete: when every criterion that was driven held and the build evidence
shows the rest is present, the row is Implemented, not tested with PARTIAL in
the tested cell (naming the undriven criteria); when a part is missing, it is
Partial or lower. Something built that the input did not ask for is an
**Addition** and gets its own subsection in section 5, never a row among the
input's items.

**Ids for an input without them.** A written brief or an unnumbered requirements
file still sets the scope. Give each requirement it states a stable report-local
id (`IN-01`, `IN-02`, … in input order, kept across revisions) and quote its
wording in the section-5 row, so requested work counts in the requirements
denominator. Additions are only for work the input did not request.

**The spec's ids, unchanged.** A reader checks the report by looking each id up
in the spec, so every id is copied exactly as `requirements.json` spells it:
`REQ-001` stays `REQ-001`, never `REQ-01`, `REQ-1` or `Req 1`, with a plain ASCII
hyphen. Never renumber, rename or re-sequence an id, and never mint a new id for
something the spec already numbered. One id per section-5 row: a row never merges
two ids. A re-derived capability (`CAP-nn`, from the handover-docs skill) cites
the source ids it traces to; it never replaces them in section 5 or appendix A.

**One numbered requirements table, the Business Brief's.** Section 5's table
numbers its rows in a first **Req ID** column: `REQ-00001`, `REQ-00002`, … in row
order, five digits, with no gap or repeat. A **Type** column says what kind of
requirement each row is (functional requirement, business rule, user story,
non-functional, integration, derived rule, input, …), and a **Source id** column
carries the spec id exactly as spelled. The running number is the table's row
number, never a spec id: it doesn't replace the source id anywhere. When there
is a Business Brief, the report's section 5 maps the brief's section-5 table one
for one: the same rows, in the same order, with the same Req ID, Type and Source
id, so a reader lays the two side by side and reads across. Number the brief
first (spec order: `requirements.json`, then the rules only the Business Spec
numbers, then derived rules and inputs) and copy its numbering; never renumber
the report on its own.

**Check before you render** (these are the rules that keep the report aligned
with the spec): every spec id has a section-5 row and an appendix-Z row; every
section-5 row cites an id the input carries (or a report-local `IN-` id), or
sits under Additions; every section-5 and appendix-Z row has a plain-English
description; every
legacy table / form in the spec's data model has a 3.1 row; the section-0
percentages are recomputed from the section-5 list. The spec ids are the ids in
`requirements.json` plus any rule the extractor's Business Spec numbers in its
section 5 that `requirements.json` doesn't carry (some stacks number their rules
only there). Ids keep whatever prefix the extraction gives them
(`PMODEL-…`, `MSACCESS-RULE-…`). An id listed under an entry's `merged` was
folded into that entry: the entry's one row covers it, and that row may list the
folded ids beside the entry's id. When the input has a
`requirements.json`, prove the id rules with the handover-docs skill's script
instead of eyeballing them:
`python3 <handover-docs skill folder>/scripts/check_report_ids.py <requirements.json> <report.md> --business-spec <Customer>-Business-Spec.md`
(drop `--business-spec` when the spec collection has no Business Spec; for an
application split into business domains, pass `--business-spec` once for the
overview `<Customer>-Business-Spec.md`, whose section 5 and `Requirements to
confirm` table list every requirement, and once per domain's Business Spec
(`domains/*/<…>-Business-Spec.md`); an overview from an older extraction has
neither table, so pass only the domain specs, and the check skips such an
overview with a note; add
`--spec <AppName>-business-brief.md` whenever there is a Business Brief: it also
proves section 5 lists the brief's numbered rows one for one, in its order, and
lets the report cite the brief's re-derived `CAP-nn` ids). Fix every `FAIL` line and run it again until it prints `OK`;
a report it fails is not ready to render. **Fix the report, never
`requirements.json` or the spec**, and never add ids to the brief you pass
with `--spec` to make a line pass. If a `FAIL` looks wrong, report it as
OUTSTANDING with the line instead of reshaping the report around it.
**`render_pdf` enforces it on this server**: rendering an Implementation Report
runs the same check against the spec collection's `requirements.json`, and a
mismatch comes back as the `FAIL` lines instead of a PDF. Fix them and call
`render_pdf` again; a refused render is not a finished report. A render whose
result does not say the ids match (it found no spec collection, or more than
one, or the check could not run) left the check undone, and so does a host
without this server. **There the id check needs a shell**, like
the PDF page review: a `reporter` subagent with no `Bash` says in its
`ReportRef` that the id check is OUTSTANDING, with the exact command above, and
whoever has a shell (the orchestrator, or you in single-agent mode) runs it and
sends back the `FAIL` lines before the work is called done. Never report the
ids as checked when the script did not print `OK`.

**Which app keys to read.** The tenant lookups below (`context_roles`,
`context_entities`, `context_screens`) run against every built app: the
`BuildReport`'s top-level `app_key` for a single-app build, and the
`app_key` of each built entry in its `app_landscape` when two or more apps
are built. Keep each row's owning app in the inventories, so an entity that
lives in a data app or a screen in another delivered app is not lost.

0. **Cover and summary** — three parts, all on page 1.
   - *Header*: the document family's cover, drawn from plain markdown (see
     "The PDF look"): the `# <App> — Requirements & Implementation Report` title,
     an opening `>` quote with the one-line subtitle (what it is, which design
     it's built in), and an `| Item | Value |` meta table (date · source
     repo/requirements · live app URL · environment + **revision** — the
     `revision` from the `BuildReport`, the same one in the filename, so the file
     and the header name the same published build — plus rows for source stack,
     built stack, N screens, N entities, N AOs, N journeys driven).
   - *KPI cards* — a quick visual summary of the work done, written as a KPI
     list that the renderer draws as the family's **card grid** (not a table —
     see "The PDF look"). They are **mandatory**, sit immediately below the
     header, and MUST render on **page 1** of the PDF:
     % requirements implemented, written `- **P% REQs implemented** X of N spec
     ids` (the spec ids, every id `requirements.json` and the Business Spec
     number, whose status is Implemented, tested / Implemented, not tested /
     Changed, over every spec id: the `check_report_ids.py --figure` line, which
     the checker holds this card to), % business rules
     implemented AND tested (rule rows of section 5 at Implemented, tested —
     include whenever a business-rules source exists; NOT OBSERVABLE rows leave
     the denominator), % user journeys PASS (the section-4.3 journeys table), the
     **AO count** (see "Counting AOs"), plus the counts of screens, entities and
     journeys driven. Every percentage is computed from the section-5 list and
     the section-4 tables only; the screen and entity counts come from sections
     4 and 3, and the AO count from the sources "Counting AOs" names (those
     inventories plus the `BuildReport`'s `ao_inventory`). **When two or more apps are built or planned**, add
     one card per app (its requirements implemented as `done/total (%)`) and
     follow the cards with the **app landscape** diagram (see "App landscape —
     built vs recommended" below); the landscape may run onto page 2, the cards
     may not.
   - *Overview* — what the source application is, what was built, and how the
     build re-frames or extends it. Honest framing if the product shape changed.
1. **Scope** — the spec's in-scope and out-of-scope lists and assumptions, what
   changed in scope during the build and why, and the gaps framed as the next
   milestones, plus policy notes (e.g. auth wired-but-not-activated).
2. **Roles and access** — each role the spec names, mapped to the built role
   (`context_roles` on the tenant, per built app), the screens it can open, and whether that was
   driven as that role. A role the spec names and the app lacks is a Not built row.
3. **Data model before and after** — someone reading it knows that legacy table A
   is now entity X, and that field a1, an integer, is now attribute Abc of X and a
   boolean. Four parts:
   - *3.1 Table level* — one row per legacy table / form / entity in the spec's
     data model: legacy name · new entity · change (kept, merged into X, dropped
     with the reason, replaced by Y, added). Call out merges, consolidations and
     additions explicitly.
   - *3.2 Field level* — one block per entity: legacy form · legacy field ·
     legacy type · new entity · new attribute · new type · transformation. The
     left-hand columns come from the spec's data model (what the client already
     signed off on); the right-hand columns come from the **built app on the
     tenant** — read them with `context_entities` scoped to each built app's key, never
     from memory or from the spec.
   - *3.3 Legacy vs built entity diagram* — a rendered **diagram** comparing the
     original source entities to the built ones: renames, consolidations, drops
     and net-new entities (see "Diagrams & flowcharts").
   - *3.4 Built ER diagram* — the built data model as a rendered diagram:
     entities, key attributes, PKs and relationships as built.
   With no legacy source (a build from a brief), 3.1 and 3.2 run over the brief's
   entities and 3.3 reads "Not applicable: no source data model". 3.4 is always
   there.
4. **Screens and journeys** — five parts:
   - *4.1 Site map* — a **picture** of the built app's navigation: its menu and
     UI-flow tree as it stands on the tenant (`context_screens` scoped to each
     built app's key: each UI flow and its screens, read-only), with the links the
     journeys drove as edges (entry / login → menu → list → detail / create /
     edit, plus the back paths). Tag every node with its status (a colour per
     status plus a legend), and draw each expected screen the tenant lacks as a
     dashed Not built or Deferred node so the gap shows on the map. For a
     localized app, label each node with its English name in parentheses.
   - *4.2 Screens* — a table over every expected screen (English name ·
     built as · status · captured?) with an "N / N screens implemented" result
     line.
   - *4.3 Journeys — expected vs implemented (drive-tested)* — a table over EVERY
     journey. When a user-stories source exists (`06-user-stories.md`, a
     `user-stories.md`, `requirements.json` story entries), every
     individually-identified story is its own row (id + title), reconciled
     one-to-one with the `TestReport`'s story-id-named entries. This table
     carries the drive evidence; each story's status lives in its section-5 row
     — keep the two in lockstep. Columns: journey · steps driven · expected
     outcome · result (PASS / PARTIAL / FAIL / Not built). **List every journey
     actually tested — exhaustively and in detail.** One row per journey driven
     this session, including the exploratory tests beyond the spec-derived set
     (edge cases, validation/error paths, regression hunts — everything in the
     `TestReport`); the steps-driven cell names the concrete sequence (entry
     screen → clicks/typing → data used → what was asserted). Never collapse
     several drives into one row and never omit a journey as "minor" — this
     table is the complete drive-test record of the app. A PASS row MUST be a
     flow you actually drove this session — **including the write/mutation
     flows** (create, edit, renew, status-advance, add-child): drive them against
     live data and verify the effect persisted. Cover at minimum navigation,
     CRUD, search/filter (incl. dropdown filters), pagination and sorting. Close
     with an honest write-path coverage note (which mutations were driven vs
     which share the same engine). Denominator for the journeys %.
   - *4.4 Look and feel* — bolded-lead paragraphs for navigation & layout and the
     design-system tokens actually built (colours, typeface, radii).
   - *4.5 Live captures* — one subsection per implemented screen: a **trimmed,
     base64-embedded** screenshot of the RUNNING app + a caption (what it shows,
     which design node it implements, how it behaves, what data feeds it).
5. **Requirements list** — the core of the report, and mostly ONE table: one row
   per spec id, in the Business Brief's order (spec order when there is no
   brief), over EVERY requirement, every
   individually-identified business rule AND every user story the source / brief
   implies. When a rules or stories source exists (the extractor's
   `04-business-rules.md` / `06-user-stories.md` slices, a `business-rules.md` /
   `user-stories.md` or any other such file, `requirements.json` entries, the
   Business Spec's sections), each rule and story is its own row — never merged
   or sampled. A rule the Business Spec numbers but `requirements.json` doesn't
   carry is a row in this same table, never a second table or subsection of its
   own: the reader ticks off one list. Rows of different id families (BR, REQ,
   RULE, US) keep spec order inside the one table.
   Columns: **Req ID** (`REQ-00001`, `REQ-00002`, … in row order: the Business
   Brief's number for the same row, see "One numbered requirements table" above)
   · **type** (functional requirement, business rule, user story, non-functional,
   …) · **source id** (the spec id, exactly as spelled) · **description** (one short plain-English sentence on what
   the requirement asks for, written so someone who doesn't read code
   understands it: "Orders over the customer's credit limit need a manager's
   approval", not "If Order.Total > Customer.Limit". Use the spec's own
   description when `requirements.json` or the Business Spec carries one; when
   you write it, paraphrase the spec text and add nothing it doesn't say, and
   when the spec text can't be read as business behaviour, say "Unclear in the
   spec:" and what is unclear. The verbatim spec text goes in appendix A) · **app** (the app
   that implements it, or is planned to — a column whenever the app landscape is
   required: two or more apps built or planned. A requirement of a planned app
   that was not built stays in the list under that app as Not built, so unbuilt
   scope stays in the totals. It feeds the per-app cards and the app landscape)
   · status (the fixed vocabulary above) · tested (PASS / FAIL / PARTIAL / NOT OBSERVABLE / NOT
   TESTED — the verdict of a flow actually driven this session, from the
   `TestReport`) · built as (screen / action / entity) · evidence / why not
   (with a Test Evidence Pack, the evidence cell cites its run as Skill
   `outsystems-handover-docs` lays out: the requirement's matrix row and the tests
   that prove it, named by their test ids as `summary.json` spells them
   (`TEST-007`), every one the entry lists and no other, each prefixed with its
   app's name (`<App> TEST-007`) when the report covers more than one app, since
   each app's pack numbers from `TEST-001`; without a pack, cite no
   test id, since a `test_id` in the `TestReport` names a pack test, not
   evidence). The
   five tested states are distinct, and two of them are NOT gaps: **PARTIAL** =
   some acceptance criteria driven, ≥1 couldn't be (note which); **NOT
   OBSERVABLE** = genuinely uncheckable by driving or read-only inspection —
   **excluded from the tested-% denominator, never rewritten as NOT TESTED**
   (that would invert its meaning and demand a bogus "why"). **NOT TESTED** =
   should have been checked but wasn't → a real gap. Every Partial / Deferred /
   Not built row and every PARTIAL / NOT TESTED cell carries its reason (scope
   decision, blocker, not reachable because X), in the evidence cell or after
   the status word in the same cell (`PARTIAL: region filter not driven`; the
   status or verdict always comes first) — a blank "why" is the same
   unforgivable bug as a missing Not built row. The spec-id rows are the
   denominator for the requirements % in the KPI cards; the rules rows are the
   denominator for the rules %; the story rows mirror the 4.3 journeys table
   one-to-one (same verdicts — a story can't PASS there and be Not built here).
   Never a "wired" status; keep the driven-vs-present nuance in the evidence
   column. (A separate features table is redundant with this list plus the
   journeys table — don't add one.) Close with the *Additions* subsection.
6. **Workflows and automations** — every approval flow, status lifecycle and
   scheduled job the spec names: how it was built (process, timer, the server
   action that carries the key transaction), its status, and whether it ran in
   testing. Draw each stateful flow as a rendered **state diagram** (states and
   transitions, e.g. Draft → Submitted → Approved) next to its row.
7. **Integrations** — each external system and trigger the spec names: built,
   stubbed (a Partial row that says "stubbed") or deferred, with the reason. Add
   the system-architecture diagram here whenever the app is more than a trivial
   single-screen CRUD.
8. **Non-functional** — each NFR: what was measured and how; otherwise its
   section-5 status in the fixed vocabulary, with the reason. Implemented, not
   tested is only for an NFR with implementation evidence; one that is deferred,
   partial or absent says so. "Not in source" when the spec carries none.
9. **Open questions** — each UNK: answered during the build (the answer, and who
   gave it) or still open (who must answer).

**Appendices** (Report-only, after section 9):

- **A. Traceability** — spec id → the spec's text, verbatim → built element
  (screen / action / entity / role) for every item, with the source file and
  line the spec cites for it.
- **B. Loading real data** — the step-by-step guide to replace bootstrapped sample
    rows with real data. **If the app ships an `Import Data` screen — built only
    when the user asked for one — lead with it**: sign in as a user
    holding the app role, open **Import Data from the top menu**, pick the entity
    from the dropdown, choose the import mode, then use the right download for the
    job and upload it back, reading the reported counts and fixing any
    rejected rows from the reasons given. **Report every count the screen shows:
    rows read / created / updated / deleted / rejected** — the deleted count is the
    one that tells the customer what Replace removed, so never omit it on the
    Replace path. **Spell out the two downloads and when to
    use each**, because this is the part a customer gets wrong:
    **"Download template"** gives empty headers with the Id column blank — fill it
    with new records and upload it in **Add and update** mode to ADD them alongside
    what is already there. **In Replace mode (the default) the uploaded sheet is the
    entity's complete desired contents**, so a template holding only new rows deletes
    every existing row — the confirmation says so, with the exact count, before
    anything runs. **"Download current data"** gives every existing row with its Id
    filled in — the starting point for a Replace, and the way to CHANGE existing
    records in either mode: edit the values, leave the Ids alone, upload it back. **Rows are matched on the Id column and nothing else.**
    A blank Id always adds a new record, so re-uploading a blank-Id file adds the
    rows again rather than updating them. An Id that does not exist is rejected and
    nothing is created for it. **Tell the customer to start from a download every
    time and not to add, remove or reorder its columns.** State the accepted file
    types (`.xls`, `.xlsx`, `.xlsb` — anything else is refused with a message) and the size cap
    **as built**. It works on entities
    that already hold data — use **Download current data**, edit the rows, and upload
    them back to change existing records — so it is also the correction and reload path,
    not just first load. This needs **no developer and no republish**; do NOT tell the customer to
    open ODC Studio and republish to load their own data. Note that `Import Data` is
    **role-restricted** even on an otherwise-public app, and that this is
    intentional — so somebody must already hold the app role; say who grants it.
    **Replace mode clears the sample rows for you; the seed timers still need
    retiring.** The default import mode **replaces** that entity's data, so the
    bootstrapped samples are gone the moment the customer uploads a sheet holding their
    complete real data (start from **Download current data** and replace the sample rows
    with theirs — the sheet is the whole table, not an addition to it) —
    do NOT tell them to clear the table by hand first, that step no longer exists.
    Two things still do need saying: **Add and update** mode is the other option and
    never deletes a row (blank Id creates, filled Id updates the matching row), so
    name which mode the instruction assumes and give the deleted count only for
    Replace; and the `When Published` seed timers
    must still be disabled once real data is in, or the next publish re-seeds the
    table underneath them.
    **If the app has NO import screen**, say so plainly and give the developer-side
    paths instead: which action and When-Published timer seeded
    each entity, how to clear the samples, the load paths (ODC Studio "Bootstrap
    Data from Excel" with column types matching the attributes, the app's own forms,
    or an API), and the gotchas (bootstraps load into an EMPTY table only; disable
    the seed timers once real data is in so a later publish doesn't re-seed).
- **C. Design phase — the options explored** — the design directions shown to
  the client (≈2 screens per Figma option) before the chosen one, plus the
  implemented design tokens. Include when a design/Figma exists; if the Figma
  connector is unavailable, say so and link the file rather than skipping it.
  It is Report-only and never reaches the Business Brief.
- **D. Run metrics** — only when the user explicitly asked for it (rule 11).
- **Z. Requirements checklist** — always present and always the report's last
  section, so the reader can tick every requirement off. A totals line first,
  `Implemented: X of N. Tested: Y of M.`, then one table with one row per
  section-5 row (Additions excluded), in the same order: spec id · description
  (the section-5 wording) · implemented · tested. **Implemented** is Yes for
  Implemented, tested / Implemented, not tested / Changed, Partial for Partial,
  No for Deferred / Not built. **Tested** is Yes for PASS, Partial for PARTIAL,
  No for FAIL / NOT TESTED, n/a for NOT OBSERVABLE. X counts the Yes answers
  over every row (N); Y counts the Yes answers over the rows that aren't n/a
  (M). The checklist only restates section 5: it never changes a verdict.

## One document family with the Business Spec

**Rule: the Business Spec and the Implementation Report are one document family
and stay consistent in three ways — one style, the same pictures, the same
section skeleton.** The Business Spec is the extractor's pre-build document
(what the legacy application does); this report is the post-build one (what was
built, measured item by item against it). They are read as a pair: a client
holds the spec in one hand and the report in the other and asks "was this
built?". That only works when planned and built are comparable box for box, so
nothing about the report's look, pictures or numbering may force the reader to
translate between the two.

1. **One style.** The same cover band, a running header that names the role
   ("1 Business Specification · before the build" on the spec, "2 Implementation
   Report · after the build" here), the same fonts, colours, table style, KPI
   cards and section numerals. See "The PDF look" for the conventions and the
   tokens; never restyle the report in the built app's brand (rule 9).
2. **The same pictures, drawn the same way.** Three diagrams appear in both
   documents, with the same layout, direction, node shapes, colours and legend,
   so planned and built can be compared box for box:
   - the **data model (ER)** — the spec's data-model diagram vs the built ER in
     3.4 (and the legacy-vs-built diff in 3.3), a mermaid `classDiagram` in
     both;
   - the **site map** — the spec's navigation / site map vs the built site map in
     4.1;
   - the **app landscape**, "How the apps connect" — the planned landscape from
     the spec's Recommended migration vs the built one from the `BuildReport`'s
     `app_landscape`, in section 0 when two or more apps are built or planned.

   When the spec carries one of these diagrams, start from its source (its
   mermaid block): keep its node names, order, direction and legend, then add the
   built status to each node (a colour per status plus the status in words) and
   draw what the plan has and the build lacks as a dashed node. Draw a picture
   from scratch only when the spec has none, and then in the same style.
3. **The same section skeleton.** The 0–9 + A sections above, so each report
   section answers the matching spec section item by item ("section 3" is the
   data model in both; a `BR-nn` sits in the same section in both).

**What may legitimately differ.** The report adds what only exists after a
build: the built-vs-planned status on every item (the fixed status vocabulary,
tested verdicts, live captures), the run metrics appendix (only on request, rule
11), "Loading real data", the design-phase appendix and the closing
requirements checklist (appendix Z). The spec keeps its
Recommended migration section, which the report does not reproduce: the report
answers it with the built app landscape. Everything else — look, pictures,
numbering — matches.

## The second deliverable — the client Business Brief

A client migration often needs a **forward-looking Business Specification**
alongside this Report, and the two are strictly disjoint: the Brief says what the
system is *expected to do* and carries **no** build/delivery language, no
design-tool or design-option names (appendix C, "Design phase — the options
explored", is Report-only), no test verdicts, and normally no revision. Both
are opt-in. The one exception: when an OutSystems sign-in that worked earlier
expires mid-run, write the Implementation Report without being asked, and don't
wait for a revision nobody can read: name it
`<AppName>-r<last verified revision>-at-expiry-report.md` (or
`<AppName>-at-expiry-report.md` when no revision was ever verified), as rule 5
says. The re-derivation of extractor REQs into business capabilities, the
scrub proof, and the filename firewall that stops the Brief being globbed as
source truth are in **invoke Skill `outsystems-handover-docs`** — load it and
follow it rather than inventing a second convention here.

## Diagrams & flowcharts — include by default, always as images

**Every report ships visual diagrams — this is a default, not a nice-to-have.**
A wall of tables is harder to grasp than a diagram; a good schematic makes the
data model, the architecture, and the domain concepts legible at a glance. Reach
for one whenever you'd otherwise ask the reader to hold several relationships in
their head — a picture that makes the idea click beats a paragraph. At minimum,
unless genuinely not applicable (say so explicitly if you skip one):

- **Entity / data-model diagram (ER)** — the built data model: entities, key
  attributes, and relationships (FK / M:N / parent-child) as edges, in
  section 3.4. Always include one; draw it as a UML class diagram in mermaid
  **`classDiagram`** with `direction TB`, one class per entity, its key attributes
  as members, and every link drawn the way the extractor draws the Business
  Spec's: one association arrow `-->` with a multiplicity on both ends and a
  label (`Order "1" --> "*" OrderLine : has`). Write the multiplicities the
  source states as `1`, `0..1`, `*` or `1..*`; `"?"` means the source does not
  state one, so write `"?"` there rather than guessing. Label a stated relation
  with its verb, a field typed as another entity with the field's name, and a
  bare reference with `references`. Split a high-fan-out model by domain
  (see the layout note below). Show attributes for the core entities, not just
  boxes. When the Business Spec carries a data-model diagram, draw this one the
  same way (same entity order, direction and legend) so the two compare box for
  box. When porting a source, ALSO include the legacy-vs-built **diff** diagram
  of section 3.3 (renames, consolidations, drops, net-new).
- **System-architecture / context diagram** — the moving parts and how they
  connect: screens / blocks → server & aggregate actions → entities, plus any
  external pieces (REST/SOAP integrations, AI agents, When-Published timers /
  bootstrap jobs). Draw it as vertical tiers (UI → logic → data → external) with
  a mermaid **`flowchart TB`** and one `subgraph` per tier. Include whenever the
  app is more than a trivial single-screen CRUD — it's usually the single most
  clarifying picture in the report.
- **App landscape — built vs recommended** — **mandatory whenever two or more
  apps are built or planned**. Draw it from the **approved plan and the build as
  verified**: the apps delivered and the references between them, from the
  `BuildReport`'s **`app_landscape`** (the developer reads the references with
  `app_refs` after its last publish, and the orchestrator passes them to you),
  with the plan's apps that were not built. Call `app_refs` yourself only in
  solo mode, where you have the OutSystems tools (pass the app key as `key`,
  and record its `source`, `indexedKinds` and coverage the way the developer
  does); in a team your only tenant tools are the read-only context lookups,
  and `app_refs` is not one. If neither is available, ask for the
  `app_landscape` rather than drawing references nobody verified. An app's
  edges are its `references` plus its `build_references`. **When its
  `refs.coverage` is `unknown`, a dependency missing from those lists is not
  evidence that there is none**: keep an edge the plan or the extraction's
  diagram has and the lists lack, drawn dashed and labelled `not confirmed`,
  and say under the diagram which apps' references are unknown and which kinds
  `app_refs` covered (`indexedKinds`). Remove such an edge only when the app's
  coverage is `complete`, and never call the landscape complete while any
  app's coverage is unknown. It shows
  the planned landscape against what was delivered: user groups on top with an
  arrow into each app they work in; apps below in rows by wave, each above the
  apps it builds on, with an arrow per dependency (label it with its link count
  when the spec gives one); the shared-data apps framed as one row; libraries in
  a row of their own (theme, logic), with the apps that use them. Name each app's
  kind when it is not a web app (mobile app, workflow, AI agent), and **colour
  each box by its asset type**, the same palette as the Business Spec's diagram,
  with a small legend of the types shown: app white (border `#80858C`), mobile
  app `#E8F1FB` (border `#2F6FB0`), workflow `#FFF4DE` (border `#C98A00`), AI
  agent `#F1EAFB` (border `#7A4FC4`), library `#E7F5EC` (border `#2E8B57`). In
  mermaid that is one `classDef` per type, e.g. `classDef agent
  fill:#F1EAFB,stroke:#7A4FC4`, and a `class` line naming its nodes. **Each app box
  carries its requirements done**: `Claims Management · 18/24 requirements (75%)`,
  counted from the section-5 list's **App** column with the same
  status rules as the KPI cards, so the per-app numbers add up to the headline
  %. An app the plan includes but this build did not deliver stays in the
  picture, labelled `not built` and drawn dashed, rather than disappearing.
  **Reuse the extraction's diagram when there is one**: if the extractor's
  recommended migration in the spec collection carries a *How the apps connect*
  mermaid block, start from its nodes and edges (its `%% wave N: <app>` comments
  give each app's row), then correct them to the build as verified and add the %
  to each app's label. When there is none, draw it from the plan and the verified
  references alone. Author it as a mermaid
  `flowchart TB` with one `subgraph` per wave and one for libraries, and render
  it as an image like every other diagram. Keep it free of crossing lines: when
  an arrow would cross another, reorder the apps in its row, and state a link
  that still cannot be drawn cleanly in a line under the diagram instead.
- **Site map** — the section-4.1 picture of how a user moves through the BUILT
  app: the tenant's UI flows and screens (`context_screens`), entry / login →
  menu → list → detail / create / edit, with the links and back paths, every
  node tagged by status and the expected-but-missing screens dashed. Mermaid
  **`flowchart TB`**, one `subgraph` per UI flow or menu group, a `classDef`
  per status and a legend. Always include one. When the Business Spec carries a
  site map, start from it (see "One document family with the Business Spec").
- **Workflow / state-machine diagram** — for any status lifecycle or BPT /
  approval / multi-step process the app implements (e.g. Draft → Submitted →
  Approved), draw the states and transitions in section 6. Prefer mermaid
  **`stateDiagram-v2`**. Include whenever the source or build has a stateful
  flow.
- **Concept / domain diagram** — when a domain idea is non-obvious (how the core
  business concepts relate, a scoring / pricing / calculation pipeline, a
  role-and-permission model), a small schematic earns its place. Use whichever
  mermaid type fits the idea (`flowchart TB`, `erDiagram`, `mindmap`); the test
  is simply "does a picture make this click faster than prose".
- Any other **schematic** (integration `sequenceDiagram`, bootstrap / seed flow)
  that clarifies a non-obvious part of the build.

**Prefer mermaid, oriented vertically.** Author every diagram in mermaid — it's
the default source format (readable, consistent, and the type names above map
straight to it) — and lay it out **top-to-bottom / portrait** so it fits the
PDF's vertical page without shrinking to an unreadable strip. Use `flowchart TB`
(or `graph TD`); `stateDiagram-v2` is vertical by default; give a `classDiagram`
`direction TB`. **Split a high-fan-out entity model (one hub with many related
tables) into a few smaller per-domain diagrams.** Field-proven on the earlier
`erDiagram` form: a 28-entity ER rendered as a 1500×320 strip with illegible text
until it was split into three per-domain diagrams. Only
reach for `LR` (left-to-right) when a chain is genuinely wide-and-shallow and
would read worse stacked, and even then keep it narrow enough to stay legible at
page width. Split a large graph into a few smaller vertical diagrams rather than
one sprawling landscape one.

**In the browser-render path, `classDiagram` member blocks are fragile.** One
malformed member line (a space or a symbol in a name, an unclosed brace) throws a
hard `Syntax error in text` and blanks the WHOLE diagram (not just that class) —
and the render-via-preview-browser path surfaces that only as an empty box, so it
costs a whole render cycle to notice. Write each member as `+Type Name`, where
the class name, the type and the attribute name are each letters, digits and
underscores (members `+int Id` and `+Text Status` in `class Order`). Don't rename an entity
whose name has a space or a non-ASCII letter: give it an ASCII id and keep the
real name as the mermaid alias, `class Order_Item["Order Item"]`, which is how
the Business Spec's diagram carries it. If a block still fails, fall back to
**relationships-only** edges with the multiplicities on the edge
(`Order "1" --> "*" OrderLine : has`), adding members back one class at a
time. Field-proven on the earlier `erDiagram` form: an ER with attribute blocks
failed to render until it was reduced to relationships-only.

**Render every diagram as an IMAGE and embed it base64** — a fenced ```mermaid
block does NOT render in the PDF (the terminal deliverable). Author it in
mermaid, then render to PNG — the reliable path here is to render the mermaid in
the **preview browser and screenshot it**: write the diagram as an HTML page that
loads `mermaid.js`, serve the folder detached (`setsid bash -c 'cd <dir> &&
python3 -m http.server <port>' &`), then `mcp__preview__get_screenshot` at
`http://localhost:<port>/<file>.html` — the preview browser runs in THIS
container, so `localhost` resolves. (The `mmdc` CLI exists but has choked
on some diagrams); fall back to Graphviz (`apt-get install -y graphviz`;
`dot -Tpng`) only when mermaid genuinely can't express the shape. Embed the PNG
as a base64 data URI (see "Embed screenshots (and diagrams)" and PDF-polish rule
4 below for the exact mechanics). Place each diagram in the section it
illustrates: the app landscape in 0 after the KPI cards, legacy-vs-built in 3.3,
the built ER in 3.4, the site map in 4.1, state machines in 6 beside the
workflow they describe, architecture in 7.

**Rendering needs a shell.** Serving the mermaid page takes `Bash`, which the
`reporter` subagent does not have. In multi-agent mode, write each diagram's
HTML page under `reports/diagrams/` anyway and name every unrendered diagram
as OUTSTANDING in the prose above your `ReportRef` (the same escape hatch as
the PDF page review), so whoever has a shell renders and embeds it before the
work is called done. The site map has a path that needs no shell: a nested
markdown list (UI flow → its screens), each node followed by its status in
words and tinted with an inline HTML badge in the status colour. Never ship a
fenced mermaid block as the only copy of a diagram.

## Counting AOs (Application Objects)

AOs are OutSystems' licensing size metric. As of this writing, **each screen,
each entity (including static entities), and each exposed/consumed API method
counts as 1 AO** — in ODC, custom-defined Events count too. Blocks, server /
client actions, roles, timers, processes, and structures do NOT count. Compute
the built app's AO count from the report's own inventory — the screens you
capture in the screens section, the entities in the data-model table, plus the
`BuildReport`'s `ao_inventory` counts (`api_methods`, `odc_events`). If a
component isn't reported, count it as 0 and SAY SO next to the AO number
("no API methods reported") — never guess a count. The definition
changes over time — **verify it at report time**: the canonical reference is
<https://success.outsystems.com/support/licensing/application_objects/> (the
page is client-side rendered, so a plain fetch returns an empty shell — use a
web search for "OutSystems Application Objects licensing" or fetch the docs
source that backs the page:
<https://raw.githubusercontent.com/OutSystems/docs-support/master/src/licensing/app-object-count.md>),
and note in the report which definition you used.

## Screenshots

Capture each screen from the running app with
`mcp__preview__get_screenshot {url, full_page, save_path}` — pass a relative
`save_path` like `shots/home.png` (keep paths space-free) so the PNG lands in
your workspace. Capture at report time (fresh, from the live app), not from
earlier in the build when screens may have changed.

**Trim dead whitespace before embedding.** A `full_page` capture of a short
screen leaves a large empty band that dominates a PDF page. Trim each shot to
its content box. **Heads-up on THIS image: `apt-get install imagemagick` does not
persist (apt writes to `/usr`, lost on rebuild) and often fails outright, and the
venv `python3` has no `pip`/`PIL`** — so the reliable trim is **Pillow run via the
pip-owning interpreter**: `PY=$(head -1 "$(command -v pip)" | sed 's/^#!//')`. That
interpreter (field-proven `/usr/local/bin/python3.12`) does **not** always ship
Pillow — if `"$PY" -c 'import PIL'` fails with `ModuleNotFoundError: No module
named 'PIL'`, run `pip install Pillow` first (it installs into that same
interpreter's site-packages) and re-import; do not conclude "no PIL available"
and skip trimming. Then in `$PY` open the PNG, get the content bbox with
`ImageChops.difference(im, white).getbbox()`, pad a few px, `crop` and save.
**`difference(im, white)` only crops a PURE-WHITE border** — an app whose page
background is a near-white tint (e.g. `#f8fafc`) leaves a full-width coloured band
the trim can't see, so a centred card (a Login screen) still embeds mostly empty.
Diff against the ACTUAL background instead — sample a corner pixel and diff on it:
`bg = im.getpixel((0, 0)); ImageChops.difference(im, Image.new("RGB", im.size,
bg)).getbbox()` — or accept the band only when it faithfully shows the app's own
whitespace. (If ImageMagick IS present, `mogrify -bordercolor white -border 10
-fuzz 6% -trim +repage shots/home.png` also works.)

**Embed screenshots (and diagrams) as base64 data URIs — NOT the
`/api/file-raw` route.** The `/api/file-raw?path=…` link renders in the
Files-tab markdown preview, but the PDF renderer does **not** resolve it, so the
images come out BLANK in the PDF — the terminal deliverable. Inline a data URI
instead (works in both the PDF and the Files view, so one form covers both):

```python
import base64, pathlib
b64 = base64.b64encode(pathlib.Path("shots/home.png").read_bytes()).decode()
# swap BOTH ![alt](path) AND any <img src="path"> you wrote,
# or a markdown-only rewrite leaves those blank
# then write:  f"![Home](data:image/png;base64,{b64})"
```

Do this for every screenshot and every rendered diagram right before the final
render (a small helper script that swaps each `![alt](path)` for the data URI
keeps the markdown authorable).

## Rules

1. **Report against the input, not against what you built.** Walk the source /
   requirements item by item; every source entity, feature, and flow appears in
   the report with a status. Omitting a Not built row is the one unforgivable
   report bug.
2. **Statuses are earned** (the fixed vocabulary in "Report structure"):
   Implemented, tested = works and was driven to PASS; Partial = present but
   incomplete (say which half); Not built = absent with no decision behind it.
   A PASS you did not drive this session is a lie — retest or downgrade.
3. **Honesty over polish.** The report exists to tell the user what they can
   rely on and what is still ahead. Overstating kills its value; a clearly
   named gap is a feature of the report.
4. **No fidelity claim without Exactness evidence.** Never write that the app
   "matches the design", is "1-for-1", a "carbon copy", or a "faithful build"
   unless Skill **`outsystems-ui-exactness`** claim tables show PASS (screenshots may
   attach as evidence). Functional completeness ("works & persists") is NOT
   visual Exactness; report them as separate KPI lanes. Where content or data
   diverges from the design, say so as a gap — an unbacked fidelity claim is
   the same unforgivable overstatement as a missing Not built row.
5. **Name the report for the revision it describes.** The filename MUST carry the
   app revision the report was written against:
   **`<AppName>-r<revision>-report.md`** (e.g. `ItemManagement-r42-report.md`), and
   the PDF alongside it as `<AppName>-r<revision>-report.pdf`. The revision comes
   from the `BuildReport` handoff's `revision` field — your only tenant tools are
   the read-only context lookups, so never guess it or read it off a screenshot. If the orchestrator did not pass one,
   ask for it before writing; only when the build genuinely has no revision (a
   standalone / non-ODC app) fall back to `<AppName>-report.md` and say in the meta
   table that no revision applies. **On a sign-in expiry, don't wait for it.**
   Nobody can read the revision until the user reconnects, so when the last
   publish's revision is unknown, name the file
   `<AppName>-r<last verified revision>-at-expiry-report.md` (or
   `<AppName>-at-expiry-report.md` when no revision was ever verified), so it
   never overwrites an existing report. In the meta table, give the last
   verified revision and say a later publish may not be reflected. A report is a statement about one specific
   published revision — an unversioned filename silently overwrites the previous
   revision's report and destroys the ability to compare them.
6. **Every generated report lives in `reports/`.** The path is
   **`reports/<AppName>-r<revision>-report.md`** at the project root (create the
   folder if it is not there), with the PDF alongside it as
   `reports/<AppName>-r<revision>-report.pdf` — and the same for any other
   document you generate: residual-gaps, handover pair, test report. The ONLY
   exception is a location the user asked for, which always wins; say where you
   put it. Reports accumulate one per revision and a workspace root that mixes
   them with notes, screenshots, specs and source is impossible to scan — one
   folder makes "every report for this app" a single listing, and makes the set
   easy to hand over.
7. **Push and maintain.** Write the file under that name, push it
   with `mcp__preview__show_file`, and if you keep working afterwards, update
   the file and push the same path again so the canvas shows the current truth.
   **A new publish means a new revision means a NEW file** — never rewrite the
   previous revision's report in place; write the new `-r<revision>-` file so both
   remain on the Files tab.
8. **Ground it in the `TestReport`.** The orchestrator hands you the tester's
   `TestReport` (per-flow PASS/FAIL) and the source of truth (source repo /
   requirements / design brief). Reconcile the two: a flow the tester marked
   `FAIL` is Partial or Not built in the report, never an Implemented status. Don't invent
   a status the `TestReport` doesn't support. Business-rule and user-story rows
   reconcile one-to-one with the `TestReport`'s per-item entries (the rule-/
   story-id-named flows): `tested` is the driven verdict; an item with no
   `TestReport` entry is NOT TESTED with the reason — never a silent PASS.
9. **Style EVERY report as the document family, not as the app.** The report
   and the extractor's Business Specification are one family with two roles,
   so the cover, palette, type, tables, KPI cards and page chrome come from
   `render_pdf` (see "The PDF look"), never from the app's brand. The built
   app's identity lives in its own screenshots and in its design tokens
   (colours, typeface, radii) named in the 4.4 look-and-feel section. Don't
   tint the report with the app's colours, don't add a logo banner, and don't
   fetch a company's brand kit for the report.
10. **A user-attached PDF is the template.** When the user provided a PDF (a
   prior report, a corporate template, a handoff example) and it makes sense
   for this deliverable, follow its tone, its cover's wording and what its meta
   table lists. The template sets the tone and the cover's wording, never the
   look: the cover band, palette, type and tables stay the document family's
   (rule 9), and the section numbers stay the shared skeleton above so the
   report still lines up with the Business Spec; follow the template's own
   order only when the user asks for it. Say in one line which
   reference you followed.
11. **No cost or run metrics unless explicitly requested.** Never include the
   run's execution cost, token counts, API spend, model usage, or turn/run
   timing telemetry in the report — that is workflow telemetry about how the
   app was generated, not deliverable content about the app. By default there
   is **no "Run metrics" section**. Include it ONLY when the user explicitly
   asked for costs/metrics: add a `## D. Run metrics` heading as the last
   appendix before the closing `## Z. Requirements checklist` (never mixed into the KPI cards) — on `render_pdf` the server fills
   that section with the real, captured numbers. With no such heading, nothing
   is injected, so an ordinary report carries no run-metrics/cost section at all.
12. **The report is a snapshot of the app as it stands — not a changelog.**
   Every section describes the CURRENT state of the application (this
   revision, this publish). Do not structure content as deltas against
   earlier revisions or earlier reports ("since the last report…", "newly
   added in this round…", "changes from v2"), and do not carry forward
   per-revision history sections. When updating an existing report file,
   rewrite it as the new snapshot rather than appending change notes.
   Version-to-version comparison appears only when the user explicitly asks
   for a changelog. (The source-vs-built comparisons — requirements, data
   model, journeys — are scope reconciliation against the SOURCE, not version
   history; they stay.)

## The PDF look — one document family

The report and the extractor's Business Specification are one family with two
roles, so a client sees at a glance that they belong together. `render_pdf`
draws the family look; you write plain markdown and never style it yourself:

- **No `<style>` blocks and no hand-written HTML banners or cards.** The
  family stylesheet owns the look and a `<style>` block in the markdown is
  dropped. The one raw-HTML element allowed is an inline status badge (a
  status word in its status colour, as the site map uses), never as a banner
  or a card. Plain markdown also keeps the Files-tab view complete.
- **Cover**: `render_pdf` draws the role band (Legacy Modernization ·
  Implementation Report, the two-step "before the build → after the build"
  strip) from the `#` title. An opening `>` quote right under the title is the
  lead, and an `| Item | Value |` table before the first `##` section is the
  meta table; both move to the cover.
- **KPI cards**: a bullet list where EVERY item is
  `- **<number> <label>** <caption>` becomes the card grid, four to a row. The
  number may read `66%`, `~78` or `34 / 34`, e.g.
  `- **66% REQs implemented** 53 of 80, tested or Changed`. Keep the label short;
  the caption carries the denominator.
- **Section numbers**: write the skeleton's number into the heading
  (`## 3. Data model before and after`, `## A. ...`); `render_pdf` draws it as
  the red section numeral, the same way the Business Spec shows its sections.
- **Running header and footer, page numbers, tables, CJK**: all automatic.

The tokens below are the family's, the same ones the extractor's Business Spec
renderer uses. `render_pdf` (role `implementation-report`) already applies them;
a host without it applies them in its own print stylesheet so the PDF still
reads as the same family:

| Token | Value | Used for |
|---|---|---|
| Ink | `#0A141E` | headings, KPI numbers, KPI card top bar, the filled process step |
| Body text | `#39414A` | paragraphs |
| Muted | `#52606D` | cover eyebrow, captions, running header |
| Accent | `#DB2400` | section numerals, the short rule under them, the cover band's top rule, page numbers |
| Link | `#5252F2` | links |
| Rule / grid | `#D9DEE3` | table grid, card borders, header and footer rules |
| Panel | `#F5F7FA` | cover band, meta-table key column, quote callouts |
| Table header | `#E4E7EB` | table header row (ink, bold) |

- **Type**: Helvetica (or the host's Arial / sans-serif fallback). Body
  9.5/13.5 pt, table cells 8/10 pt, sections 16 pt, subsections 12.5 pt, KPI
  numbers 20 pt. A4, 18 mm side margins.
- **Cover band**: a light panel with a 4.5 pt accent top rule, the eyebrow
  `LEGACY MODERNIZATION · IMPLEMENTATION REPORT`, the subject at 20 pt bold, the
  process strip `1 · Business Specification · before the build → 2 ·
  Implementation Report · after the build` with step 2 filled, and one role
  statement: "What was built, measured item by item against the Business
  Specification."
- **Running header on every page**: `Legacy Modernization · Implementation
  Report · after the build`, the subject on the right. **Footer**: `subject ·
  role · date`, the page number in the accent colour.
- **Tables**: light header row, thin full grid, no zebra. **KPI cards**: white,
  thin border, an ink top bar, the number, the label, an optional caption.

## PDF polish — hard-won rendering rules

The rendered PDF is what clients actually read; these make it land:

1. **Minimize white space — control every page break.** Empty bands read as
   sloppy. The family stylesheet already carries the print rules below; follow
   these habits so nothing strands a blank half-page:
   - **No orphaned headings / empty sections after a title.** Never emit a
     heading with no body under it, and never sprinkle `page-break-before:always`
     per section — forced breaks strand blank tails; let content flow and break
     only where the renderer must. Do **not** use `break-after:avoid` on headings
     in these reports (next bullet — it strands the page before a long table).
   - **Tables: rows atomic, header repeats, short ones don't split.** Let a LONG
     table (one row per spec item) flow across pages with each ROW kept intact
     and the header **repeated** (`thead{display:table-header-group}`) so a
     continuation is never headerless. Wrap a SHORT table (and the KPI grid / any
     small block) in an element with inline `style="break-inside:avoid"` so it
     jumps whole rather than leaving one stray row on the next page. **Trim to
     fit**: cut a mostly-empty section to its essential columns/rows (or merge it
     into a neighbour) instead of leaving a heading above blank space.
   - **A tall image with `break-inside:avoid` is the single biggest empty-space
     cause** — it can't split, so it jumps whole to the next page and strands the
     bottom of the current one. Cap `img{max-height}` around **150mm** so images
     fit the space remaining instead (field-proven: 13→7 and 16→12 pages).
   - **Diagrams never split and never overflow.** `break-inside:avoid` keeps a
     diagram image whole; the `max-height` cap keeps a tall one on a single page.
     If a vertical diagram is still too tall to fit, split it into a couple of
     smaller stacked diagrams rather than letting it shrink to an unreadable
     strip or spill across a break.
   - **Keep the header compact** so section 1 starts on page 1 — a tall header /
     KPI band that strands the body on a near-empty first page is a bug.
   - **`break-after:avoid` on a heading immediately before a LONG table strands
     the prior page.** The heading can't separate from the table's first row, so
     when heading + row 1 don't fit the space left on the page the WHOLE table
     jumps to the next page, leaving a half-empty page behind it. Implementation
     reports are table-dominated (requirements, journeys and data-model tables all
     run long), so here prefer **`break-after:auto`** on headings and let
     `table{break-inside:auto}` + a repeated `thead` flow the table onto the
     current page; the "never emit a heading with no body under it" habit above
     still guards the orphaned-heading case. Field-proven: flipping the heading
     rule from `break-after:avoid` to `auto` closed two stranded half-pages on one
     report (14 → 12 pages).

   The family stylesheet sets these (shown so you know what is already true):

   ```css
   table{break-inside:auto} thead{display:table-header-group}
   tr,td,th{break-inside:avoid}
   h1,h2,h3,h4{break-after:auto}   /* NOT :avoid — see the long-table note above */
   img{break-inside:avoid;max-width:100%;max-height:150mm;display:block;margin:3px auto}
   ```
2. **KPI cards beat a KPI table — on page 1.** Write the at-a-glance metrics as
   the KPI list ("The PDF look"); `render_pdf` draws them as cards on the cover,
   kept whole on page 1. Verify page 1 shows the KPIs when you check the
   rendered PDF (rule 8).
3. **Markdown only.** The Files-tab markdown view strips raw HTML; the family
   conventions are plain markdown, so the cover, meta table and KPIs read there
   too. Keep raw HTML to the rare thing markdown can't say (an inline status
   badge), never for layout.
4. **Diagrams as images, not code fences.** A fenced `mermaid` block does NOT
   render in the PDF. Author in mermaid, laid out **vertically** (`flowchart TB`
   / `graph TD`; `stateDiagram-v2` is vertical; `classDiagram` with `direction TB`;
   split a high-fan-out data model by domain, see the diagram section), then
   produce a real image — render the mermaid in the preview browser and
   screenshot it (Graphviz `dot -Tpng` is the fallback when mermaid can't express
   the shape) — and embed it base64. This is the render mechanics for the
   diagrams the "Diagrams & flowcharts — include by default" section above
   makes mandatory: the ER / data-model (and legacy-vs-built diff when
   porting), the site map, the system-architecture diagram, and the workflow /
   state-machine diagram — plus any other schematic that
   clarifies the build.
5. **Never write the "§" symbol** — some clients dislike it; spell out the word
   ("Section N").
6. **Localized (non-English) apps:** give the English name in parentheses for
   every screen / nav entry (e.g. "Encomendas (Orders)"), and note once that the
   UI language is X with English names for reference.
7. **Statuses are drive-tested, never "wired".** Don't ship an "Implemented
   (wired)" hedge. Actually drive the mutation flows (create / edit / renew /
   status-advance / add-child row) against live data and verify the effect
   persisted; then mark Implemented, tested / Partial and keep the driven-vs-present
   nuance in the evidence column. Reconcile the KPI cards, the requirements
   table, the journeys table and the screens table so they tell one consistent
   story.
8. **Verify the PDF visually before "done" — LOOK at every page.** A PDF with
   half-empty pages reads as padded and unfinished, and you cannot catch that
   from the markdown — only from the rendered pages.

   **Rasterise it with `pdftoppm`** (poppler-utils, shipped in the image):

   ```bash
   pdftoppm -png -r 80 "<AppName>-r<rev>-report.pdf" /tmp/reportpage
   # -> /tmp/reportpage-01.png, -02.png, ... one image per page
   ```

   then `Read` each PNG and actually look at it. Deterministic, one file per page.

   **Do NOT try to screenshot the PDF in the preview browser.** It looks like it
   should work and it does not: the image installs Playwright `--only-shell`, and
   the headless shell refuses to render a PDF at all (navigating to one starts a
   download instead). `chromium --headless --screenshot` on a `file://` PDF races
   its own viewer and writes a blank frame. Both were measured, not assumed.
   `pdftoppm` is the path.

   **This step needs a shell.** The `reporter` subagent has no `Bash`, so in
   multi-agent mode it cannot run the check itself: it must say in its
   `ReportRef` that the PDF page review is OUTSTANDING, and whoever has a shell
   (the orchestrator, or you in single-agent mode) runs it before the work is
   called done. Never report a PDF as verified when nobody looked at the pages.

   Hunt for: blank or near-blank pages, a heading stranded above a blank
   half-page, an empty section after a title, a table header orphaned on a
   continuation page, a diagram split across pages or overflowing one, clipped
   screenshots, and **any large empty band**. Each is a defect, not a cosmetic
   nit. Fix it (tighten content, adjust the break rules, resize or split an
   oversized diagram, merge a thin section into its neighbour), re-render, and
   re-rasterise to confirm the page is really fixed rather than assuming the edit
   worked.

## Render a PDF as the final step

Producing the PDF is the **default** — always render it whenever you write the
report (it is the primary, terminal deliverable; the markdown alone is not
enough). After the markdown report is written and pushed, produce a polished PDF
and surface it too:

1. `mcp__preview__render_pdf { path: "<AppName>-r<revision>-report.md", title: "<App> — Requirements & Implementation Report", subtitle: "<App> · rev <revision> · <date>", role: "implementation-report" }`
   — renders the markdown into `<AppName>-r<revision>-report.pdf` next to it, so the
   PDF carries the same revision as the markdown (rule 5). `subtitle` sits under
   the app name in the cover band; `role` is the family role (`"business-spec"`
   only for a document that IS a Business Specification).
2. `mcp__preview__show_file { path: "<absolute path to the .pdf> }` — put the PDF
   on the Files tab so the user can read/download it.

If you revise the report afterwards, re-run both steps so the PDF stays current.

## Handoff contract

When you finish and hand control back to the orchestrator, end your final message
with a fenced `handoff` block giving the exact path of the report you pushed, so
the orchestrator can point the user at it. Emit it LAST:

````
```handoff
{
  "type": "ReportRef",
  "path": "ItemManagement-r42-report.md"
}
```
````

- `path` is the workspace-relative path you pushed with `mcp__preview__show_file`
  — the same path, so the Files tab and this handoff agree.
- Name anything OUTSTANDING (unrendered diagrams, the PDF page review) in the
  prose just above the block, so the orchestrator finishes it.
