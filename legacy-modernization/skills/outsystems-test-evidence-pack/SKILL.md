---
name: outsystems-test-evidence-pack
description: >-
  The Test Evidence Pack shipped beside every generated app: a Playwright (TypeScript) project with one test per requirement tagged with the extractor's id and carrying a stable test id of its own (TEST-007), a traceability matrix, and an HTML report with traces and screenshots, handed over as a zip anyone can rerun. Use when turning the flows the tester verified into the delivered suite, keeping each screen's tests during a build and replaying them after every publish (npm run screens), scaffolding or refreshing a pack from requirements.json, or checking one before handover. Not for: validation verdicts -> the tester role; the Implementation Report -> outsystems-handover-docs.
license: MIT
compatibility: Designed for Claude Code with Bash, Node.js 20.12+ and network access to the deployed app. Two scripts in scripts/ (Python 3.8+, standard library only) scaffold and check a pack; the pack itself needs npm and a Playwright Chromium download. Needs no tenant tools.
allowed-tools: Read Write Edit Glob Grep Bash
metadata:
  version: "1.3.0"
  author: outsystems-r-and-d
---

# OutSystems Test Evidence Pack

The tester proves each requirement by driving the running app, but a live drive
leaves nothing the customer can re-run. The pack writes those same flows down as
Playwright tests, so the customer can repeat every check against their app,
unaided, and again after their own changes. Each run turns into a matrix of
requirement, where it lives, test, result and evidence.

The full playbook (layout, how to write a test that can't pass falsely, the
signed-out rule, untestable requirements, running it and checking it) is in
**[Test-Evidence-Pack.md](./Test-Evidence-Pack.md)** in this folder. **Read it
before writing a test.**

**Limited availability: check access first.** Legacy modernization isn't generally
available yet. Before anything else, sign in to the OutSystems MCP (see the plugin
README's [Authorize before you run](../../README.md#authorize-before-you-run)) and read
its tool list. If `modernize_session_start` isn't listed, tell the user, word for
word: *"Legacy modernization is in limited availability and isn't enabled for your tenant yet. Contact OutSystems if you'd like access."* Then stop.

## The rules that matter most

1. **The ids are the extractor's, unchanged.** `scripts/scaffold_pack.py` copies
   every requirement from `requirements.json` into the pack with its id and text
   as they are (`REQ-001`, `BR-418`, `RULE-012`). The Business Spec and the
   Implementation Report use the same ids, so there's no third requirement id
   family. Tag each test with the ids it proves: `{ tag: req('REQ-010') }`.
2. **Every test has its own id, for as long as the test exists.** The first tag is
   `testId('TEST-007')`: `TEST-` and three or more digits, one per test, never
   shared. It isn't a requirement id; it names the *test*, so the
   matrix, `summary.json`, the HTML report and the Implementation Report can cite
   it beside the requirement it proves, and a reworded title or a moved file
   leaves it as it was. A new test takes the next number after the highest
   (`check_pack.py` prints it), so a deleted test's id may go to a new test. `{ tag: [testId('TEST-007'), ...req('REQ-010')] }`.
   An id is unique within its pack: in a build of several apps each app's pack
   numbers from `TEST-001`, and a report covering more than one app cites
   `<App> TEST-007`.
3. **Every requirement gets a row.** `requirements.json` is the coverage
   denominator. A requirement with no test shows as **Not covered**. One that the
   UI can't show (a timer, a batch job) gets an `untestable` reason and shows as
   **Blocked**. Neither is ever left out.
4. **No check may pass because the page hasn't loaded yet.** OutSystems screens
   update after the load event. Before any "is absent", "count is 0" or "doesn't
   navigate" check, wait for content that only exists once the record has loaded
   (`expectAbsent(page, loaded, ...)`), never just the action bar. After a click
   that should navigate, run it through `onScreen`, which waits for the target URL
   and for the screen you were on to leave the page. Before submitting, leave the field (`fillField`).
5. **Never depend on row order or on "the first row".** Filter, then wait until
   every visible row matches (`filterList`). A check that needs a particular
   record reads its id from `.env` (`sample('NAME')`).
6. **Read-only by default, and always check signed-out access.** Tests that
   change data run only with `ALLOW_WRITES=true`. Every pack has an `@ACCESS`
   test per screen with write or role-gated actions. It opens the screen signed
   out and asserts those actions are absent.
7. **Steps read as Given / When / Then, in business language.** Use the `given`,
   `when` and `then` helpers. The evidence page and the report quote them.
8. **Check before you hand over.** `npm run typecheck`, `npm run list`, then
   `python3 scripts/check_pack.py <pack> --requirements <extractor
   requirements.json>`. It fails on a respelled or unknown id, a test with no
   test id, a malformed one or one two tests share, a test with no
   Given/When/Then step, no `@ACCESS` test, or a `TODO(pack)` left in the README.
   Then `npm test` and `npm run handover`, which zips the pack with that run's
   matrix, report and traces. The zip is the handover: no GitHub repo, no CI.
9. **Rerun, don't re-drive.** Once a pack exists, check a change by running
   `npm test` in it and reading `<pack>/evidence/summary.json`, not by driving the app
   again. A person reruns it from the results page: `npm start`, then **Rerun tests**, or
   **Rerun** on one requirement to check one fix (`npm run test:req -- TEST-007` reruns one test).
10. **Start the pack at the first publish, not at handover.** Each screen's tests go in
   `tests/screens/<Screen>.spec.ts` as soon as the screen first passes a drive-test, and
   after every publish `npm run screens -- <Screen> …` replays the ones the change
   touched in one call, instead of driving them again. See section 9 of the playbook.
