# Test Evidence Pack: the playbook

A Test Evidence Pack is a Playwright Test project, in TypeScript, shipped beside a
generated app as a zip (`npm run handover`), never inside its OML. It has three parts:

| Part | Where | For |
|---|---|---|
| Tests | `tests/*.spec.ts` | One test per requirement or user-journey step, tagged with the requirement's id and named by a test id of its own (`TEST-007`). The customer re-runs them and keeps them as the app's regression suite. |
| Traceability matrix | `evidence/traceability-matrix.{html,md,csv}` and `<pack>/evidence/summary.json` | Built after every run: requirement, where it lives, tests, result and evidence. |
| HTML report | `evidence/html-report/` | A trace (DOM snapshots, replayable) and screenshots per test, so a reader can watch a requirement pass or fail without running anything. |

It runs on whatever machine the customer, the professional services team or the agent
has: one run, one result, against the app's published URL. Every command is an `npm` script or a
Node script, never a shell script. Settings come from `.env`, never from an inline
`VAR=x cmd`, which is bash syntax and fails in PowerShell and cmd. Checks assert on
data, never on pixel baselines, because font rendering differs between operating
systems.

## 1. Scaffold the pack

```
python3 <skill>/scripts/scaffold_pack.py <spec>/requirements.json <pack-dir> \
    --app-name "Order Desk" --base-url https://<tenant>/OrderDesk \
    --sample ORDER_AWAITING_APPROVAL=10452
```

This writes the template and `<pack>/requirements/requirements.json`: every extractor
requirement with its id and text unchanged, plus an empty `screens` list each.
Pass `--sample` once for each record a test needs (section 4). Re-run it with
`--update` after a new extraction. That refreshes the requirements, keeps the
`screens` and `untestable` entries already added, never touches `tests/`, and lists
any id the extraction dropped.

Then, in the pack:

```
npm install        # once; it writes package-lock.json, which ships with the pack
npm run setup      # downloads the pinned Chromium
```

When the build already started the pack for its screen tests (section 9), don't
scaffold a second one: run the same command with `--update` and the extraction's
`requirements.json`, which keeps `tests/` as it is.

## 2. Fill in where each requirement lives

`requirements.json` has a `screens` map (screen id to `name` and `route`, where
`route` is `null` for a screen that isn't built) and a `screens` list on each
requirement. Fill both from the build. The matrix's "Where in the app" column comes
from them.

A requirement the UI can never show (a scheduled job, a timer, an integration with
no screen) gets an `untestable` sentence saying why:

```json
{ "id": "REQ-012", "text": "...", "screens": [],
  "untestable": "Runs as a scheduled job with no screen, so the UI cannot show it." }
```

It then shows as **Blocked** with that reason. Never leave it uncovered without a
reason, and never tag a test on it that doesn't prove it.

## 3. Write one test per flow you verified

Write down each flow the tester drove to a verdict as a test, using the same steps
and the same assertions. Group the tests by area (`list-views.spec.ts`,
`approvals.spec.ts`, `access.spec.ts`).

```ts
import { test, expect } from '@playwright/test';
import { req, testId, open, chooseView, listTotal, columnValues, evidence, given, when, then } from './support';

test('an approver sees only the orders waiting for them', { tag: [testId('TEST-007'), ...req('REQ-007', 'BR-031')] }, async ({ page }, testInfo) => {
  await given('an approver opens the Approvals view from the Switch view menu', async () => {
    await open(page, '/');
    await chooseView(page, page.locator('select').first(), 'Approvals', 'ApprovalList');
  });
  await then('every order listed is waiting for approval', async () => {
    expect(await listTotal(page)).toBeGreaterThan(0);
    expect(new Set(await columnValues(page, 'Status'))).toEqual(new Set(['Pending approval']));
    await evidence(page, testInfo, 'approvals list');
  });
});
```

- **Give every test its own test id, first in its tags**: `testId('TEST-007')`,
  `TEST-` and three or more digits. It names the test, not a requirement: the
  matrix, `summary.json`, the HTML report and the Implementation Report cite the
  test by it, beside the requirement it proves. It names one test for as long as that
  test exists, so reword a title, move a test to another file or change what it proves and keep
  its id. A new test takes the next number after the highest in the pack, which
  `check_pack.py` prints ("a new test takes TEST-015"); once a test is deleted,
  its id may go to a new test. When the tester's `TestReport` gives a
  flow a `test_id`, use that one, unless `check_pack.py` says another test
  already has it: that test keeps it, and the new one takes the id `check_pack.py`
  prints. A test declared in a loop builds its id from
  the loop (`` testId(`TEST-0${10 + i}`) ``), so each test it makes has its own.
  A test id is unique within its pack. In a build of several apps each app's pack
  numbers from `TEST-001` and is checked on its own, so a report covering more than
  one app cites each id with its app's name in front, `<App> TEST-007`.
- **Tag with every id the test proves**, exactly as `requirements.json` spells it.
  One test may prove several requirements (`req('REQ-007', 'BR-031')`), and one
  requirement may need several tests. A business rule (`BR-`, `RULE-`) gets its own
  test that drives its trigger and asserts its outcome, the same as a user story.
- **Name steps in Given / When / Then form, in business language**, with the
  `given` / `when` / `then` helpers. The test title says what a reader is checking.
  Neither names a selector.
- **Reach a screen the way a user does**: through its menu or link, not by typing
  the route, unless the requirement is about the route itself.
- **Attach evidence** at the moment the verdict rests on (`evidence(page, testInfo,
  name)`). Playwright also keeps a trace and a screenshot for every test. Video is off: the
  trace and the screenshot show what happened, and video makes every run and the
  handover much heavier. Turn it on in `playwright.config.ts` only if a customer asks.
- **Use the helpers in `<pack>/tests/support.ts`** rather than writing new waits. Add a
  helper there when a pattern repeats.
- **Prefer roles and visible names** (`getByRole('button', { name: 'Approve' })`)
  over CSS classes and generated ids, which change when the app is republished.

## 4. Tests that can't pass falsely

Each rule below comes from a real false pass or unstable result in an earlier pack.

1. **Wait for the data before checking absence.** OutSystems screens fetch data and
   render after the load event, so a control that will appear isn't there yet, and
   `toHaveCount(0)` passes at once. Use `expectAbsent(page, loaded, ...controls)`.
   `loaded` must be content that only exists once the record has arrived, such as a
   field of the loaded record (`page.getByText('Order 10452')`). The action bar or the
   page title is not enough: they render before the record or role fetch adds the
   gated buttons. The helper then waits for the network to go quiet, checks, takes a
   second look 1.5 s later and checks again. That second look is a bound, not a
   guarantee: a control that renders more than about 1.5 s after the network goes
   quiet still passes. If the app renders a gated control that late, wait for
   whatever triggers it (a role fetch, a second data action) as part of `loaded`.
2. **Wait before checking non-navigation.** "Clicking X doesn't open Y" passes
   before navigation has started. Use `expectNoNavigation(page, /Y/)`, which waits
   for the URL first.
3. **Wait for the screen you navigated to, and for the old one to leave.** Run
   any click or dropdown choice that navigates through
   `onScreen(page, /Target/, () => link.click())` (`chooseView` calls it). The URL
   alone isn't enough: OutSystems keeps the previous screen in the DOM while the new
   one loads and renders, so for a moment the URL is new but a locator matches the
   old screen's rows. `onScreen` marks the current screen before the action and waits
   for that screen to go, so it can't pass while only the old screen is there. In the
   JPetStore pack this caused most of the first run's failures. An app with no `main`
   landmark gets no protection from it; wait for content only the target screen has.
4. **Leave a field before submitting.** Under load, clicking Save or Update straight
   after `fill` can submit the previous value. Use `fillField(field, value)`, which
   leaves the field and checks the value has been taken. For an input that reformats
   on blur (currency, decimals, dates), pass what it shows as the third argument:
   `fillField(price, '5', '5.00')`.
5. **Wait for the change, not for a message that can repeat.** Two updates in a row
   can show the same "Saved." text, and a pop-up message may close itself before the
   check runs. Wait for what the action changes (the row re-renders, a total moves),
   then check a message only if it stays on the page.
6. **Filter, then wait until every row matches.** Reading rows straight after
   choosing a filter reads the unfiltered list. `filterList` polls until every
   visible row shows the expected value.
7. **Never use row order.** Rows with equal sort keys come back in a different
   order between runs, which made one test skip on one OS and not the
   other. Find a row by what it contains, or use a named sample.
8. **Name sample records.** A check that needs a particular kind of record (an
   order with lines, an order past its SLA) reads its id from `.env` with
   `sample('NAME')`, which skips with a reason when it's unset. The README says what
   each sample must be.
9. **Read-only by default.** A test that creates, changes or deletes data starts
   with `test.skip(!env.allowWrites, WRITES_SKIP_REASON)`. Delivered apps often run
   on shared environments.
10. **Skip with a reason, never silently.** A test that needs a user or a role
    starts with `test.skip(!env.user, USER_SKIP_REASON)`. The matrix shows the
    reason.
11. **Assert on data.** Check filter values, roster membership, row counts, a
    computed total, or the contents of an exported file (read the download off
    disk). "The button is visible" proves only that the button is visible.

## 5. Always check signed-out access

For every screen with write or role-gated actions, one test opens it signed out and
asserts those actions are absent, once the record's own data is on the screen. Tag
it `ACCESS` and the requirement it protects:

```ts
test('a signed-out visitor is not offered write actions on an order', { tag: [testId('TEST-034'), ACCESS, ...req('REQ-034')] }, async ({ page }, testInfo) => {
  await given('a signed-out visitor opens an order awaiting approval', async () => {
    await open(page, `/OrderDetail?OrderId=${sample('ORDER_AWAITING_APPROVAL')}`);
  });
  await then('no edit, approve or cancel action is offered', async () => {
    await evidence(page, testInfo, 'order, signed out');
    await expectAbsent(
      page,
      page.getByText(`Order ${sample('ORDER_AWAITING_APPROVAL')}`, { exact: true }),
      ...['Edit', 'Approve', 'Cancel order'].map((name) => page.getByRole('button', { name, exact: true })),
    );
  });
});
```

Where the spec defines roles and `APP_USER_WITHOUT_ROLE` is set, add the same check
signed in without the role. An earlier pack found signed-out visitors could see Edit,
Cancel and a role-gated return action on a generated app that had passed validation. This
rule makes sure every pack would catch that.

Actions `outsystems-auth-and-deploy` §4a exempts are expected to stay open: leave
them out of the `ACCESS` assertions and name them, with the reason, when you report the pack.

## 6. Run it and check it

```
npm run typecheck
npm run list                                   # writes evidence/tests.json
python3 <skill>/scripts/check_pack.py . --requirements <spec>/requirements.json
npm test                                       # runs everything, then builds the matrix
```

`check_pack.py` fails on:

- an id in the pack that differs from the extraction, or text that was reworded;
- a test with no test id, two of them, or one another test already has, and a
  malformed test id (`TEST-7`, `test-007`); with `<pack>/evidence/tests.json` this is
  read per test Playwright lists, so a loop that gives every test it makes the
  same id fails too;
- a requirement id in the `TEST-` family, which a tag couldn't tell from a test id;
- a tag that isn't a requirement id, `ACCESS` or a test id, including one that respells an id
  (`REQ-01`) and one with no digit (`@Access`, `@smoke`);
- a `<pack>/evidence/tests.json` older than any test file or the config (run `npm run list`
  again), because the runtime tags it holds would no longer match the tests;
- a `test.only` or `describe.only` left in;
- a test with no Given / When / Then step;
- no `@ACCESS` test;
- a requirement in a required tier with neither a test nor an `untestable` reason.
  The functional tier is required by default (`--require-tier` adds more). Business
  rules may stay Not covered, and the matrix shows them apart, per tier;
- a screen a requirement names that isn't in the `screens` map;
- a `TODO(pack)` line left in the README or `.env.example`.

It reports, per tier, how many requirements have a test, how many are untestable and
how many are not covered yet, and the test id the next new test takes. Report those
counts with the pack.

`npm test` exits non-zero when any test fails, and when any test is **flaky** (failed,
then passed on its retry). Flaky is its own verdict in the matrix, never a pass: a test
that fails only sometimes is a difference to fix. A failing test
against a real defect is the pack working: report the defect, don't weaken the test.
After the run, `<pack>/evidence/results.json` and `<pack>/evidence/summary.json` hold the
results the Implementation Report cites. A run that dies before writing results leaves
no matrix, rather than the previous one. Set `APP_REVISION` in `.env` to the revision you
tested, so the matrix and the report name the build each result is about.

`summary.json` gives the report everything its requirements list cites, one entry per
requirement, in the extractor's ids:

- the verdict, and the blocked reason when there is one;
- `source`, where the requirement comes from in the legacy code, as the extraction cites
  it (it is also a column of the matrix);
- `where`, the screens and routes that deliver it;
- `matrix`, the link to its row in `traceability-matrix.html`;
- each tagged test: its `id` (the test id, `TEST-007`), title, file, result, failure
  or skip reason, Given/When/Then steps, `report` (its entry in the HTML report, with
  the trace) and `screenshot` (the failure screenshot, copied under
  `evidence/screenshots/`). The untagged checks under `other` carry their `id` too.

The matrix names every test by its test id as well (in the HTML, Markdown and CSV), and
the HTML report shows it as the test's `@TEST-007` tag, so a reader finds the test the
Implementation Report cites in each of them.

Links are relative to the run's folder: `evidence/` for the full run the report cites (`evidence/subset/` for a subset run). Skill `outsystems-handover-docs` says how the report
turns these into its section-5 rows, and its `check_report_ids.py --matrix` proves the
report and the matrix list the same requirements, that each row cites the test ids
that prove it, and that they don't disagree.

`npm run test:req -- REQ-012` runs only those requirements and writes to
`evidence/subset/`, listing just them; `npm run test:req -- TEST-007` runs that one
test and lists the requirements it proves. The full run's report and matrix are left as
they were, so cite only a full run.

## 7. Before it ships

- Fill in the README's "What data the tests expect" section and each sample's
  description. `check_pack.py` fails while a `TODO(pack)` remains.
- Ship `package-lock.json`, so `npm ci` installs the same versions the pack was run
  with. Playwright is pinned to an exact version for the same reason.
- Run the full suite (`npm test`), then `npm run handover`. It writes
  `dist/<package name>.zip`: the tests, the requirements, the README and the
  lock file, with that run's matrix, report and traces, so the customer can read the
  evidence before installing anything. It refuses to run until a full run has built
  the matrix. That zip is what ships; the pack needs no git repo.
- No `.env`, no `node_modules/`, no raw `evidence/artifacts/`, no subset run and no
  screen-test run (`evidence/screens/`) in what ships. The handover script leaves them out.
- No GitHub repo and no CI workflow: the zip is self-contained. Whoever changes the app
  reruns it locally (section 8).

## 8. Rerunning it after a change

The pack is the app's regression suite, for the agent and for people alike. After any
change to the app (a Mentor turn, the professional services team's last 20%), rerun it
against the published app.

A person runs `npm start` in the unzipped pack. It serves the matrix on
`http://127.0.0.1:4173` and opens it, with a **Rerun tests** button that runs the whole
suite, shows each test as it finishes and reloads the page with the new results. Each
requirement with tests also has a **Rerun** button that runs only its tests
(`npm run test:req -- <id>`, into `evidence/subset/`) and shows the new result on that row,
marked RERUN, beside the full run's. The full run's matrix and report are left as they
were, so the Implementation Report still cites a full run. The
first rerun on a machine runs `npm ci`, installs the pinned Chromium and copies
`.env.example` to `.env`. The server listens on this machine only, needs nothing but
Node, and starts nothing but the pack's own run. Opened straight from the zip as a file,
the page says to run `npm start` instead.

From a terminal, or as an agent:

```
npm test
```

An agent asked to "rerun the tests" runs that one command in the pack and reads
`<pack>/evidence/summary.json` (totals and each requirement's verdict) instead of driving the
app again, so a rerun costs no tokens beyond reading the result. A person opens
`<pack>/evidence/traceability-matrix.html` for the same result. First time on a machine:
`npm ci`, `npm run setup` and a `.env` copied from `.env.example`.

## 9. Screen tests during the build

The pack doesn't have to wait for handover. Started at the first publish, it holds
each screen's tests while the app is built, and replaying them after every publish
replaces re-driving the screens by hand. In an ablation on a published app, checking
three screens after a publish by driving them took 14 tool calls and about a minute;
replaying their saved tests took one call and a few seconds, for the same verdicts.

- **Start it at the first publish.** `scaffold_pack.py` as in section 1, or with
  `--no-requirements` in place of the requirements file when the build has no
  extraction yet (`--update` adds them later). Then `npm install` and `npm run setup`
  once.
- **One file per screen: `tests/screens/<Screen>.spec.ts`.** After a screen's first
  passing drive-test, write what you just checked as its tests, in the same turn: the
  screen loads with its data, and each key interaction behaves (search narrows the
  list, a row opens its detail). Every rule in sections 3 and 4 applies: Given / When /
  Then steps, assert on loaded data, no step that writes data unless it is gated on
  `ALLOW_WRITES`. The file name is the screen, so tag a test only with its test id and
  the requirement ids it proves. A journey across screens goes in the file of the screen it starts on.
  In a build of several apps, keep one pack per app, so a screen name never collides
  and a run after publishing one app replays only that app's screens.
- **After each publish, replay the screens it touched, in one call:**
  `npm run screens -- CustomerList CustomerDetail` (no names runs every test). It runs
  without trace or video, keeps a screenshot only of a failure, writes to
  `evidence/screens/` (the full run's evidence is left alone) and answers in a few
  lines:

  ```
  Screen tests: 3/4 PASS, 1 FAIL.
  FAIL CustomerDetail › a customer opens a record at "Then the name is shown": Error: expect(locator).toBeVisible() failed · Locator: getByText('Ada') · Expected: visible (screenshot: evidence/screens/artifacts/…/test-failed-1.png)
  PASS 3/4: CustomerList › lists customers; CustomerList › search narrows the list; Orders › lists orders
  ```

  The first line is the verdict, the one a `BuildReport` quotes. A spec that fails to load
  gets its own `ERROR <file>: …` line and counts as a `FAIL` in the verdict (its tests
  never ran), a run cut short adds `INCOMPLETE`, and the PASS line names the first 20
  passing tests and counts the rest. When the app now runs on another origin
  than the pack's `.env`, give it on the call: `APP_BASE_URL=<origin> npm run screens -- …`.
  A name with no file exits 2 and lists the screens that have tests. Include the start
  screen of any journey that passes through a screen the change touched, and run them
  all before handing back or after a change to something shared (a block, an entity,
  the theme, a role).
- **Don't re-drive a screen whose tests pass.** Open it in the browser only to build or
  check something new on it, to compare it with the design, or to diagnose a failure.
- **A failure blocks the next change, not its fix.** Any `FAIL`, `ERROR` or `INCOMPLETE`
  means the run is not green: make the next change the fix (the app, or a spec that no
  longer loads), then replay. When the screen changed
  on purpose, edit the test and say so; delete a removed screen's file. Never weaken a
  test to get past a screen that broke.
- **At handover these are already the pack's first tests.** Section 1's `--update`
  brings in the requirements, and sections 2 to 7 finish the pack.
