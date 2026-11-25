"""Run with: python3 -m unittest discover -s scripts -p 'test_*.py'"""

import contextlib
import importlib.util
import io
import json
import os
import shutil
import subprocess
import sys
import time
import tempfile
import unittest
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parents[2] / "legacy-modernization/skills/outsystems-test-evidence-pack/scripts"
sys.path.insert(0, str(_SCRIPTS))


def _load(name):
    spec = importlib.util.spec_from_file_location(name, _SCRIPTS / (name + ".py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


scaffold_pack = _load("scaffold_pack")
check_pack = _load("check_pack")

EXTRACTION = {
    "schema": "requirements@1",
    "requirements": [
        {"id": "REQ-001", "tier": "functional", "text": "Enter orders."},
        {"id": "REQ-002", "tier": "functional", "text": "Approvers see pending orders.", "merged": ["REQ-009"]},
        {"id": "BR-418", "tier": "business", "text": "Nightly timer closes stale orders."},
    ],
}
EXTRACTION["by_tier"] = {"functional": EXTRACTION["requirements"][:2], "business": EXTRACTION["requirements"][2:]}

GOOD_SPEC = """import { test, expect } from '@playwright/test';
import { req, testId, ACCESS, open, given, then, expectAbsent } from './support';

test('a user enters an order', { tag: [testId('TEST-001'), ...req('REQ-001')] }, async ({ page }) => {
  await given('a user opens the new order form', async () => {
    await open(page, '/NewOrder');
  });
  await then('the form is empty', async () => {
    expect(1).toBe(1);
  });
});

test('approvers see pending orders', { tag: ['@TEST-002', '@REQ-002'] }, async ({ page }) => {
  test.skip(!process.env.APP_USER, 'Needs a user.');
  await test.step('Given an approver opens Approvals', async () => {});
});

test('signed out, no approve', { tag: [testId('TEST-003'), ACCESS, ...req('REQ-002')] }, async ({ page }) => {
  await then('approve is not offered', async () => {
    await expectAbsent(page.getByRole('button', { name: 'Print' }), page.getByRole('button', { name: 'Approve' }));
  });
});
"""


def quiet(fn, *args, **kwargs):
    out = io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(out):
        result = fn(*args, **kwargs)
    return result, out.getvalue()


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.extraction = self.tmp / "requirements.json"
        self.extraction.write_text(json.dumps(EXTRACTION), encoding="utf-8")
        self.pack = self.tmp / "pack"

    def scaffold(self, *extra, source=None):
        args = [str(source or self.extraction), str(self.pack), "--app-name", "Order Desk",
                "--base-url", "https://tenant.example/OrderDesk/", *extra]
        return quiet(scaffold_pack.main, args)

    def pack_spec(self):
        return json.loads((self.pack / "requirements/requirements.json").read_text(encoding="utf-8"))

    def finish(self, spec_text=GOOD_SPEC):
        """A pack check_pack accepts: specs written, BR-418 untestable, README filled in."""
        (self.pack / "tests/orders.spec.ts").write_text(spec_text, encoding="utf-8")
        data = self.pack_spec()
        data["requirements"][2]["untestable"] = "Runs as a nightly timer with no screen."
        (self.pack / "requirements/requirements.json").write_text(json.dumps(data), encoding="utf-8")
        readme = self.pack / "README.md"
        readme.write_text(readme.read_text(encoding="utf-8").replace("TODO(pack)", "Done."), encoding="utf-8")


class ScaffoldTest(Base):
    def test_keeps_every_id_and_text_unchanged(self):
        code, _ = self.scaffold()
        self.assertEqual(code, 0)
        rows = self.pack_spec()["requirements"]
        self.assertEqual([r["id"] for r in rows], ["REQ-001", "REQ-002", "BR-418"])
        self.assertEqual([r["text"] for r in rows], [r["text"] for r in EXTRACTION["requirements"]])
        self.assertEqual(rows[1]["merged"], ["REQ-009"])
        self.assertTrue(all(r["screens"] == [] for r in rows))

    def test_reads_a_bare_list_and_a_by_tier_mapping(self):
        bare = self.tmp / "bare.json"
        bare.write_text(json.dumps(EXTRACTION["requirements"]), encoding="utf-8")
        tiers = self.tmp / "tiers.json"
        tiers.write_text(json.dumps({"by_tier": EXTRACTION["by_tier"]}), encoding="utf-8")
        for source in (bare, tiers):
            rows = scaffold_pack.extractor_requirements(source)
            self.assertEqual(sorted(r["id"] for r in rows), ["BR-418", "REQ-001", "REQ-002"])

    def test_fills_every_placeholder(self):
        self.scaffold("--sample", "ORDER_WITH_LINES=10452")
        for f in self.pack.rglob("*"):
            if f.is_file():
                self.assertNotRegex(f.read_text(encoding="utf-8"), r"\{\{[A-Z_]+\}\}", f.name)
        self.assertTrue((self.pack / "README.md").is_file())
        self.assertFalse(list(self.pack.rglob("*.template")))
        self.assertIn("APP_BASE_URL=https://tenant.example/OrderDesk\n", (self.pack / ".env.example").read_text())
        self.assertIn("SAMPLE_ORDER_WITH_LINES=10452", (self.pack / ".env.example").read_text())
        self.assertFalse((self.pack / ".github").exists())
        self.assertEqual(json.loads((self.pack / "package.json").read_text())["name"],
                         "order-desk-test-evidence-pack")
        scripts = json.loads((self.pack / "package.json").read_text())["scripts"]
        self.assertEqual(scripts["start"], "node scripts/serve.mjs")
        self.assertEqual(scripts["handover"], "node scripts/handover.mjs")

    def test_refuses_to_overwrite_a_pack(self):
        self.scaffold()
        code, out = self.scaffold()
        self.assertEqual(code, 1)
        self.assertIn("--update", out)

    def test_update_keeps_what_the_tester_added_and_lists_dropped_ids(self):
        self.scaffold()
        self.finish()
        data = self.pack_spec()
        data["requirements"][0]["screens"] = ["S-01"]
        data["screens"] = {"S-01": {"name": "New order", "route": "NewOrder"}}
        (self.pack / "requirements/requirements.json").write_text(json.dumps(data), encoding="utf-8")
        newer = self.tmp / "newer.json"
        newer.write_text(json.dumps([EXTRACTION["requirements"][0], EXTRACTION["requirements"][2],
                                     {"id": "REQ-003", "text": "Export orders."}]), encoding="utf-8")
        code, out = self.scaffold("--update", source=newer)
        self.assertEqual(code, 0)
        self.assertIn("REQ-002", out)
        rows = {r["id"]: r for r in self.pack_spec()["requirements"]}
        self.assertEqual(sorted(rows), ["BR-418", "REQ-001", "REQ-003"])
        self.assertEqual(rows["REQ-001"]["screens"], ["S-01"])
        self.assertEqual(rows["BR-418"]["untestable"], "Runs as a nightly timer with no screen.")
        self.assertEqual(self.pack_spec()["screens"], data["screens"])
        self.assertEqual((self.pack / "tests/orders.spec.ts").read_text(), GOOD_SPEC)

    def test_update_needs_no_name_and_keeps_the_packs_own(self):
        self.scaffold()
        code, _ = quiet(scaffold_pack.main, [str(self.extraction), str(self.pack), "--update"])
        self.assertEqual(code, 0)
        self.assertEqual(self.pack_spec()["app"], "Order Desk")
        code, _ = self.scaffold("--update")  # --app-name is passed again, but never renames the pack
        self.assertEqual(self.pack_spec()["app"], "Order Desk")

    def test_update_reports_a_malformed_pack_instead_of_a_traceback(self):
        self.scaffold()
        (self.pack / "requirements/requirements.json").write_text("{not json", encoding="utf-8")
        code, out = self.scaffold("--update")
        self.assertEqual(code, 1)
        self.assertIn("can't be read as a pack's requirements", out)

    def test_a_new_pack_needs_a_name_and_url_and_update_needs_a_pack(self):
        code, out = quiet(scaffold_pack.main, [str(self.extraction), str(self.pack)])
        self.assertEqual(code, 1)
        self.assertIn("--app-name and --base-url", out)
        code, out = quiet(scaffold_pack.main, [str(self.extraction), str(self.pack), "--update"])
        self.assertEqual(code, 1)
        self.assertIn("holds no pack to update", out)

    def test_rejects_a_requirement_without_id_or_text(self):
        for rows in ([{"text": "x"}], [{"id": "REQ-001"}], []):
            self.extraction.write_text(json.dumps(rows), encoding="utf-8")
            code, out = self.scaffold()
            self.assertEqual(code, 1, rows)
            self.assertIn("FAIL", out)


    def test_a_pack_can_start_with_no_requirements_and_take_them_later(self):
        # A build with no extraction still keeps its screen tests in a pack from the first publish.
        code, out = quiet(scaffold_pack.main, ["--no-requirements", str(self.pack), "--app-name", "Order Desk",
                                               "--base-url", "https://tenant.example/OrderDesk/"])
        self.assertEqual(code, 0, out)
        self.assertEqual(self.pack_spec()["requirements"], [])
        self.assertIn('"screens"', (self.pack / "package.json").read_text(encoding="utf-8"))
        code, out = self.scaffold("--update")
        self.assertEqual(code, 0, out)
        self.assertEqual([r["id"] for r in self.pack_spec()["requirements"]], ["REQ-001", "REQ-002", "BR-418"])

    @unittest.skipUnless(shutil.which("node"), "needs Node.js to run the pack's matrix builder")
    def test_an_untagged_screen_spec_passes_the_check_and_the_matrix(self):
        # A build-time pack: no extraction yet, a screen spec tagged with no requirement id.
        code, out = quiet(scaffold_pack.main, ["--no-requirements", str(self.pack), "--app-name", "Order Desk",
                                               "--base-url", "https://tenant.example/OrderDesk/"])
        self.assertEqual(code, 0, out)
        (self.pack / "tests/screens").mkdir(parents=True)
        (self.pack / "tests/screens/CustomerList.spec.ts").write_text(
            "import { test, expect } from '@playwright/test';\nimport { open, testId, given, then } from '../support';\n\n"
            "test('lists customers', { tag: testId('TEST-001') }, async ({ page }) => {\n"
            "  await given('a user opens the customer list', async () => { await open(page, '/CustomerList'); });\n"
            "  await then('the customers are listed', async () => { expect(1).toBe(1); });\n});\n",
            encoding="utf-8")
        (self.pack / "tests/access.spec.ts").write_text(
            "import { test } from '@playwright/test';\nimport { ACCESS, testId, then } from './support';\n\n"
            "test('signed out', { tag: [testId('TEST-002'), ACCESS] }, async ({ page }) => {\n"
            "  await then('nothing is offered', async () => {});\n});\n", encoding="utf-8")
        readme = self.pack / "README.md"
        readme.write_text(readme.read_text(encoding="utf-8").replace("TODO(pack)", "Done."), encoding="utf-8")
        listing = [{"title": "lists customers", "file": "screens/CustomerList.spec.ts", "line": 4, "tags": ["TEST-001"]},
                   {"title": "signed out", "file": "access.spec.ts", "line": 4, "tags": ["TEST-002", "ACCESS"]}]
        (self.pack / "evidence").mkdir(exist_ok=True)
        (self.pack / "evidence/tests.json").write_text(json.dumps(listing), encoding="utf-8")
        fails, counts = check_pack.check(self.pack)
        self.assertEqual(fails, [])
        self.assertEqual((counts["listed"], counts["total"]), (1, 0))
        results = {"stats": {"startTime": "2026-10-27T10:00:00.000Z"}, "suites": [
            {"title": "screens/CustomerList.spec.ts", "specs": [
                {"title": "lists customers", "file": "screens/CustomerList.spec.ts", "line": 4, "id": "c", "tags": ["@TEST-001"],
                 "tests": [{"status": "expected", "annotations": [], "results": [{"status": "passed"}]}]}]}]}
        (self.pack / "evidence/results.json").write_text(json.dumps(results), encoding="utf-8")
        run = subprocess.run(["node", "scripts/build-matrix.mjs"], cwd=self.pack, capture_output=True, text=True)
        self.assertEqual(run.returncode, 0, run.stderr)
        summary = json.loads((self.pack / "evidence/summary.json").read_text(encoding="utf-8"))
        self.assertEqual(summary["requirements"], [])
        self.assertEqual(summary["other"], [{"id": "TEST-001", "title": "lists customers", "status": "passed"}])

    def test_requirements_or_no_requirements_but_not_both(self):
        for args in ([str(self.pack)], [str(self.extraction), str(self.pack), "--no-requirements"]):
            code, out = quiet(scaffold_pack.main, [*args, "--app-name", "X", "--base-url", "https://x/X"])
            self.assertEqual(code, 1, args)
            self.assertIn("--no-requirements", out)
        # --update with no requirements would merge nothing over the pack and drop every row.
        self.assertEqual(self.scaffold()[0], 0)
        before = self.pack_spec()
        code, out = quiet(scaffold_pack.main, [str(self.pack), "--no-requirements", "--update"])
        self.assertEqual(code, 1)
        self.assertIn("--update needs the extractor's requirements.json", out)
        self.assertEqual(self.pack_spec(), before)


class CheckTest(Base):
    def setUp(self):
        super().setUp()
        self.scaffold()

    def check(self, **kwargs):
        return check_pack.check(self.pack, kwargs.get("extractor", self.extraction))

    def test_a_finished_pack_passes(self):
        self.finish()
        fails, counts = self.check()
        self.assertEqual(fails, [])
        self.assertEqual((counts["covered"], counts["untestable"], counts["not_covered"]), (2, 1, 0))

    def test_a_fresh_scaffold_fails_until_tests_and_readme_are_written(self):
        fails, _ = self.check()
        self.assertTrue(any("no *.spec.ts" in f for f in fails))
        self.assertTrue(any("TODO(pack)" in f for f in fails))

    def test_a_respelled_tag_names_the_real_id(self):
        self.finish(GOOD_SPEC.replace("req('REQ-001')", "req('REQ-01')"))
        fails, _ = self.check()
        self.assertTrue(any("REQ-01 is a respelling of REQ-001" in f for f in fails), fails)

    def test_an_unknown_tag_fails(self):
        self.finish(GOOD_SPEC.replace("'@REQ-002'", "'@REQ-777'"))
        fails, _ = self.check()
        self.assertTrue(any("REQ-777 isn't a requirement id" in f for f in fails), fails)

    def test_any_other_tag_fails_even_without_a_digit(self):
        for bad in ("@Access", "@REQ-ABC", "@smoke"):
            self.finish(GOOD_SPEC.replace("'@REQ-002'", "'{}'".format(bad)))
            fails, _ = self.check()
            self.assertTrue(any("tag {} isn't a requirement id".format(bad[1:]) in f for f in fails), (bad, fails))

    def test_a_leftover_only_fails(self):
        self.finish(GOOD_SPEC.replace("test('a user enters an order'", "test.only('a user enters an order'"))
        fails, _ = self.check()
        self.assertTrue(any("orders.spec.ts:4: test.only runs only this test" in f for f in fails), fails)

    def test_a_required_requirement_needs_a_test_or_a_reason(self):
        self.finish(GOOD_SPEC.replace("'@REQ-002'", "'@REQ-001'").replace("...req('REQ-002')", ""))
        fails, counts = self.check()
        self.assertTrue(any("1 required requirement with no test and no `untestable` reason: REQ-002" in f
                            for f in fails), fails)
        self.assertEqual(counts["tiers"]["functional"]["not_covered"], 1)

    def test_other_tiers_may_stay_not_covered(self):
        self.finish()
        data = self.pack_spec()
        del data["requirements"][2]["untestable"]
        (self.pack / "requirements/requirements.json").write_text(json.dumps(data), encoding="utf-8")
        fails, counts = self.check()
        self.assertEqual(fails, [])
        self.assertEqual(counts["tiers"]["business"], {"total": 1, "covered": 0, "untestable": 0, "not_covered": 1})
        fails, _ = check_pack.check(self.pack, self.extraction, ["functional", "business"])
        self.assertTrue(any("BR-418" in f for f in fails), fails)

    def test_a_merged_id_counts_for_its_entry(self):
        self.finish(GOOD_SPEC.replace("'@REQ-002'", "'@REQ-009'").replace("...req('REQ-002')", ""))
        fails, counts = self.check()
        self.assertEqual(fails, [])
        self.assertEqual(counts["covered"], 2)

    def test_a_test_without_given_when_then_fails(self):
        self.finish(GOOD_SPEC.replace("test.step('Given an approver", "test.step('An approver"))
        fails, _ = self.check()
        self.assertTrue(any("orders.spec.ts:13: the test names no Given / When / Then step" in f for f in fails), fails)

    def test_no_access_test_fails(self):
        self.finish(GOOD_SPEC.replace("ACCESS, ...req('REQ-002')", "...req('REQ-002')"))
        fails, _ = self.check()
        self.assertTrue(any("@ACCESS" in f for f in fails), fails)

    def test_ids_or_text_that_drift_from_the_extraction_fail(self):
        self.finish()
        data = self.pack_spec()
        data["requirements"][0]["text"] = "Enter orders quickly."
        data["requirements"][2]["id"] = "BR-0418"
        (self.pack / "requirements/requirements.json").write_text(json.dumps(data), encoding="utf-8")
        fails, _ = self.check()
        self.assertTrue(any("REQ-001: its text differs" in f for f in fails), fails)
        self.assertTrue(any("the extraction has and the pack doesn't: BR-418" in f for f in fails), fails)
        self.assertTrue(any("the pack has and the extraction doesn't: BR-0418" in f for f in fails), fails)

    def test_an_untestable_flag_without_a_reason_fails(self):
        self.finish()
        data = self.pack_spec()
        data["requirements"][2]["untestable"] = "timer"
        (self.pack / "requirements/requirements.json").write_text(json.dumps(data), encoding="utf-8")
        fails, _ = self.check()
        self.assertTrue(any("BR-418 `untestable` must say why" in f for f in fails), fails)

    def test_a_screen_missing_from_the_map_fails(self):
        self.finish()
        data = self.pack_spec()
        data["requirements"][0]["screens"] = ["S-09"]
        (self.pack / "requirements/requirements.json").write_text(json.dumps(data), encoding="utf-8")
        fails, _ = self.check()
        self.assertTrue(any("REQ-001 names screen S-09" in f for f in fails), fails)

    def test_listed_tags_count_tags_built_at_runtime(self):
        loop = """import { test } from '@playwright/test';
import { req, testId, then } from './support';
for (const [n, id] of ['REQ-001', 'REQ-002'].entries()) {
  test(`view ${id}`, { tag: [testId(`TEST-00${n + 1}`), ...req(id)] }, async () => {
    await then('it lists rows', async () => {});
  });
}
"""
        self.finish(loop)
        fails, counts = self.check()
        self.assertEqual(counts["covered"], 0)
        self.assertEqual(counts["listed"], 0)
        (self.pack / "evidence").mkdir()
        self.write_listing()
        fails, counts = self.check()
        self.assertEqual(counts["covered"], 2)
        self.assertEqual(fails, ["tests/access.spec.ts:3: tag REQ-1 is a respelling of REQ-001; use the id exactly"])

    def write_listing(self):
        (self.pack / "evidence").mkdir(exist_ok=True)
        (self.pack / "evidence/tests.json").write_text(json.dumps([
            {"title": "view REQ-001", "file": "orders.spec.ts", "line": 4, "tags": ["TEST-001", "REQ-001"]},
            {"title": "view REQ-002", "file": "orders.spec.ts", "line": 4, "tags": ["TEST-002", "REQ-002"]},
            {"title": "signed out", "file": "access.spec.ts", "line": 3, "tags": ["TEST-003", "ACCESS", "REQ-1"]},
        ]), encoding="utf-8")

    def test_a_listing_older_than_the_tests_fails(self):
        self.finish()
        self.write_listing()
        later = time.time() + 5
        os.utime(self.pack / "tests/orders.spec.ts", (later, later))
        fails, _ = self.check()
        self.assertTrue(any("evidence/tests.json is older than tests/orders.spec.ts" in f for f in fails), fails)

    def test_source_tags_are_checked_even_with_a_listing(self):
        self.finish(GOOD_SPEC.replace("'@REQ-002'", "'@REQ-02'"))
        self.write_listing()
        fails, _ = self.check()
        self.assertTrue(any("tag REQ-02 is a respelling of REQ-002" in f for f in fails), fails)

    def test_a_test_without_a_test_id_fails(self):
        self.finish(GOOD_SPEC.replace("'@TEST-002', ", ""))
        fails, _ = self.check()
        self.assertTrue(any("orders.spec.ts:13: the test has no test id" in f for f in fails), fails)

    def test_two_tests_with_one_test_id_fail(self):
        self.finish(GOOD_SPEC.replace("'@TEST-002'", "'@TEST-001'"))
        fails, _ = self.check()
        self.assertTrue(any("orders.spec.ts:13: test id TEST-001 is already tests/orders.spec.ts:4's" in f
                            for f in fails), fails)

    def test_a_test_with_two_test_ids_fails(self):
        self.finish(GOOD_SPEC.replace("'@TEST-002', ", "'@TEST-002', '@TEST-004', "))
        fails, _ = self.check()
        self.assertTrue(any("orders.spec.ts:13: the test has 2 test ids (TEST-002, TEST-004)" in f for f in fails), fails)

    def test_a_malformed_test_id_fails(self):
        for bad in ("TEST-2", "test-002", "TEST002", "TEST-02"):
            self.finish(GOOD_SPEC.replace("'@TEST-002'", "'@{}'".format(bad)))
            fails, _ = self.check()
            self.assertTrue(any("test id {} is malformed".format(bad) in f for f in fails), (bad, fails))

    def test_a_listed_loop_needs_an_id_per_test(self):
        self.finish()
        self.write_listing()
        listing = json.loads((self.pack / "evidence/tests.json").read_text(encoding="utf-8"))
        listing[1]["tags"] = ["TEST-001", "REQ-002"]
        listing[2]["tags"] = ["ACCESS", "REQ-002"]
        (self.pack / "evidence/tests.json").write_text(json.dumps(listing), encoding="utf-8")
        fails, _ = self.check()
        self.assertTrue(any("tests/orders.spec.ts:4 `view REQ-002`: test id TEST-001 is already "
                            "tests/orders.spec.ts:4 `view REQ-001`'s" in f for f in fails), fails)
        self.assertTrue(any("tests/access.spec.ts:3 `signed out`: the test has no test id" in f for f in fails), fails)

    def test_a_requirement_id_in_the_test_family_fails(self):
        self.finish()
        data = self.pack_spec()
        data["requirements"].append({"id": "TEST-009", "tier": "business", "text": "x", "screens": [],
                                     "untestable": "Not a screen thing at all."})
        (self.pack / "requirements/requirements.json").write_text(json.dumps(data), encoding="utf-8")
        fails, _ = check_pack.check(self.pack)
        self.assertTrue(any("TEST-009 is in the TEST- family" in f for f in fails), fails)

    def loop_spec(self, test_id):
        return """import { test } from '@playwright/test';
import { req, testId, then } from './support';
for (const [n, id] of ['REQ-001', 'REQ-002'].entries()) {
  test(`view ${id}`, { tag: [testId(%s), ...req(id)] }, async () => {
    await then('it lists rows', async () => {});
  });
}
""" % test_id

    def test_an_id_built_at_runtime_is_left_to_the_listing(self):
        for built in ("`TEST-00${n + 1}`", "'TEST-' + String(n + 1).padStart(3, '0')", "ids[n]"):
            self.finish(self.loop_spec(built))
            fails, counts = self.check()
            # Without evidence/tests.json the loop's ids aren't known: neither missing nor malformed.
            self.assertFalse([f for f in fails if "test id" in f], (built, fails))
            self.assertEqual(counts["test_ids"], 0, built)
            # So the next id it prints may be one the loop holds, and the CLI says so.
            self.assertEqual(counts["runtime_ids"], 1, built)
            _code, out = quiet(check_pack.main, [str(self.pack)])
            self.assertIn("NOTE a test builds its id at runtime", out)
            self.write_listing()
            fails, counts = self.check()
            self.assertFalse([f for f in fails if "test id" in f], (built, fails))
            self.assertEqual(counts["test_ids"], 3, built)
            self.assertEqual(counts["runtime_ids"], 0, built)
            (self.pack / "evidence/tests.json").unlink()

    def test_tests_listed_at_one_place_still_need_their_own_ids(self):
        # Two describe blocks can give two loop tests one file, line and title.
        self.finish()
        self.write_listing()
        listing = json.loads((self.pack / "evidence/tests.json").read_text(encoding="utf-8"))
        listing[1] = dict(listing[0])
        (self.pack / "evidence/tests.json").write_text(json.dumps(listing), encoding="utf-8")
        fails, _ = self.check()
        self.assertTrue(any("test id TEST-001 is already another test at the same place's" in f for f in fails), fails)

    def test_a_merged_id_in_the_test_family_fails(self):
        self.finish()
        data = self.pack_spec()
        data["requirements"][0]["merged"] = ["TEST-009"]
        (self.pack / "requirements/requirements.json").write_text(json.dumps(data), encoding="utf-8")
        fails, _ = check_pack.check(self.pack)
        self.assertTrue(any("REQ-001 merges TEST-009 is in the TEST- family" in f for f in fails), fails)

    def test_a_pack_scaffolded_before_test_ids_says_how_to_bring_it_up_to_date(self):
        self.finish()
        support = self.pack / "tests/support.ts"
        old = support.read_text(encoding="utf-8")
        support.write_text(old.replace("export function testId", "function testIdGone"), encoding="utf-8")
        fails, _ = self.check()
        self.assertTrue(any("tests/support.ts predates test ids" in f for f in fails), fails)
        support.write_text(old, encoding="utf-8")
        # The matrix script writes the id into summary.json, so an old copy of it is named too.
        matrix = self.pack / "scripts/build-matrix.mjs"
        script = matrix.read_text(encoding="utf-8")
        # As the old script read: no TEST_ID, but still a `#?testId=` report link.
        old_script = script.replace("TEST_ID", "GONE")
        self.assertIn("testId", old_script)
        matrix.write_text(old_script, encoding="utf-8")
        fails, _ = self.check()
        self.assertTrue(any("scripts/build-matrix.mjs predates test ids" in f for f in fails), fails)
        matrix.write_text(script, encoding="utf-8")
        self.assertEqual(self.check()[0], [])

    def test_cli_exit_codes(self):
        code, out = quiet(check_pack.main, [str(self.pack)])
        self.assertEqual(code, 1)
        self.finish()
        code, out = quiet(check_pack.main, [str(self.pack), "--requirements", str(self.extraction)])
        self.assertEqual(code, 0, out)
        self.assertIn("functional: 2 of 2 have a test", out)
        self.assertIn("business: 0 of 1 have a test, 1 are marked untestable", out)
        self.assertIn("Test ids: 3 tests named; a new test takes TEST-004.", out)
        self.assertNotIn("builds its id at runtime", out)


class TestIdPatternTest(unittest.TestCase):
    """The two skills ship separately, so each copy of the test id rule is pinned to the same text here."""

    COPIES = (
        "skills/outsystems-test-evidence-pack/scripts/check_pack.py",
        "skills/outsystems-handover-docs/scripts/check_report_ids.py",
        "skills/outsystems-test-evidence-pack/template/tests/support.ts",
        "skills/outsystems-test-evidence-pack/template/scripts/build-matrix.mjs",
        "skills/outsystems-test-evidence-pack/template/scripts/run.mjs",
    )

    def test_every_copy_of_the_test_id_rule_agrees(self):
        import re
        root = _SCRIPTS.parent.parent.parent
        found = {}
        for rel in self.COPIES:
            text = (root / rel).read_text(encoding="utf-8")
            # `\d` (JS) and `[0-9]` (Python) mean the same digits here.
            patterns = {m.replace("\\d", "[0-9]") for m in re.findall(r"\^TEST-[^$/\"']*\$", text)}
            self.assertTrue(patterns, rel)
            found[rel] = patterns
        self.assertEqual({p for ps in found.values() for p in ps}, {"^TEST-[0-9]{3,}$"}, found)


def _result(title, tags, status, results, annotations=()):
    return {"title": title, "file": "orders.spec.ts", "line": 1, "id": title, "tags": tags,
            "tests": [{"status": status, "annotations": list(annotations), "results": results}]}


@unittest.skipUnless(shutil.which("node"), "needs Node.js to run the pack's matrix builder")
class MatrixTest(Base):
    """The pack's build-matrix.mjs, run by Node on a hand-made Playwright results.json."""

    def setUp(self):
        super().setUp()
        self.scaffold()

    def build(self, specs, subset="", directory="evidence"):
        out = self.pack / directory
        out.mkdir(parents=True, exist_ok=True)
        results = {"stats": {"startTime": "2026-10-27T10:00:00.000Z"}, "suites": [{"title": "orders.spec.ts", "specs": specs}]}
        (out / "results.json").write_text(json.dumps(results), encoding="utf-8")
        env = dict(os.environ, EVIDENCE_DIR=directory, SUBSET_IDS=subset)
        run = subprocess.run(["node", "scripts/build-matrix.mjs"], cwd=self.pack, env=env, capture_output=True, text=True)
        self.assertEqual(run.returncode, 0, run.stderr)
        return json.loads((out / "summary.json").read_text(encoding="utf-8")), (out / "traceability-matrix.md").read_text()

    def test_a_flaky_test_is_flaky_not_a_pass(self):
        summary, md = self.build([
            _result("enters", ["@REQ-001"], "flaky", [{"status": "failed", "errors": [{"message": "Error: boom"}]},
                                                    {"status": "passed"}]),
            _result("approves", ["@REQ-002"], "expected", [{"status": "passed"}]),
        ])
        verdicts = {r["id"]: r["verdict"] for r in summary["requirements"]}
        self.assertEqual(verdicts["REQ-001"], "Flaky")
        self.assertEqual(verdicts["REQ-002"], "Pass")
        self.assertEqual((summary["summary"]["flaky"], summary["tests"]["flaky"]), (1, 1))
        self.assertEqual(summary["byTier"]["functional"]["pass"], 1)

    def test_every_output_names_each_test_by_its_test_id(self):
        summary, md = self.build([
            _result("enters", ["@TEST-007", "@REQ-001"], "expected", [{"status": "passed"}]),
            _result("lists", ["@TEST-008"], "expected", [{"status": "passed"}]),
        ])
        rows = {r["id"]: r for r in summary["requirements"]}
        self.assertEqual(rows["REQ-001"]["tests"][0]["id"], "TEST-007")
        self.assertEqual(summary["other"], [{"id": "TEST-008", "title": "lists", "status": "passed"}])
        self.assertIn("`TEST-007` enters (passed)", md)
        self.assertIn("- TEST-008 lists: **passed**", md)
        self.assertNotIn("Tagged with ids requirements.json doesn't have", md)
        html = (self.pack / "evidence/traceability-matrix.html").read_text(encoding="utf-8")
        self.assertIn('<code class="tid">TEST-007</code>', html)
        self.assertNotIn('data-chip="TEST-007"', html)
        csv = (self.pack / "evidence/traceability-matrix.csv").read_text(encoding="utf-8")
        self.assertIn("TEST-007 enters [passed]", csv)

    def test_a_subset_run_of_one_test_lists_the_requirements_it_proves(self):
        summary, _ = self.build([_result("enters", ["@TEST-007", "@REQ-001"], "expected", [{"status": "passed"}])],
                                subset="TEST-007", directory="evidence/subset")
        self.assertEqual([r["id"] for r in summary["requirements"]], ["REQ-001"])

    def test_a_skip_reason_set_at_run_time_is_shown(self):
        _, md = self.build([_result("approves", ["@REQ-002"], "skipped", [
            {"status": "skipped", "annotations": [{"type": "skip", "description": "Needs APP_USER in .env."}]}])])
        self.assertIn("Needs APP_USER in .env.", md)

    def test_a_subset_run_lists_only_its_requirements_in_its_own_folder(self):
        summary, md = self.build([_result("enters", ["@REQ-001"], "expected", [{"status": "passed"}])],
                                 subset="REQ-001", directory="evidence/subset")
        self.assertEqual([r["id"] for r in summary["requirements"]], ["REQ-001"])
        self.assertIn("Subset run (REQ-001)", md)
        self.assertFalse((self.pack / "evidence/traceability-matrix.md").exists())

    def test_the_summary_names_the_default_app_url(self):
        summary, _ = self.build([_result("enters", ["@REQ-001"], "expected", [{"status": "passed"}])])
        self.assertEqual(summary["baseUrl"], "https://tenant.example/OrderDesk")

    def failing_run(self, status="unexpected"):
        """A test whose failing try left a screenshot under evidence/artifacts, as Playwright does."""
        shot = self.pack / "evidence/artifacts/orders-enters/test-failed-1.png"
        shot.parent.mkdir(parents=True, exist_ok=True)
        shot.write_bytes(b"\x89PNG fake")
        failed = {"status": "failed", "errors": [{"message": "Error: boom"}],
                  "steps": [{"title": "Then the order is saved", "error": {"message": "boom"}}],
                  "attachments": [{"name": "screenshot", "contentType": "image/png", "path": str(shot)}]}
        tries = [failed, {"status": "passed", "steps": [{"title": "Then the order is saved"}]}] if status == "flaky" else [failed]
        self.build([_result("enters", ["@REQ-001"], status, tries)])
        return (self.pack / "evidence/traceability-matrix.html").read_text(encoding="utf-8")

    def test_the_summary_carries_each_requirements_evidence_for_the_report(self):
        spec = self.pack_spec()
        spec["requirements"][0]["source"] = "`ORDERS.dxl`, form \"Order\""
        spec["requirements"][1]["source"] = ""
        spec["requirements"][1]["derived_from"] = {"source": {"file": "APPROVE.dxl", "where": {"form": "Queue\n"}}}
        (self.pack / "requirements/requirements.json").write_text(json.dumps(spec), encoding="utf-8")
        (self.pack / ".env").write_text("APP_REVISION=42\n", encoding="utf-8")
        self.failing_run()
        summary = json.loads((self.pack / "evidence/summary.json").read_text(encoding="utf-8"))
        self.assertEqual(summary["revision"], "42")
        rows = {r["id"]: r for r in summary["requirements"]}
        self.assertEqual(rows["REQ-002"]["merged"], ["REQ-009"])
        first = rows["REQ-001"]
        self.assertEqual((first["verdict"], first["source"]), ("Fail", 'ORDERS.dxl, form "Order"'))
        self.assertEqual(first["matrix"], "traceability-matrix.html#req-REQ-001")
        self.assertEqual(rows["REQ-002"]["source"], "APPROVE.dxl, Queue")
        test = first["tests"][0]
        self.assertEqual((test["status"], test["reason"]), ("failed", "boom"))
        self.assertEqual(test["steps"], ["Then the order is saved"])
        self.assertEqual(test["report"], "html-report/index.html#?testId=enters")
        self.assertTrue((self.pack / "evidence" / test["screenshot"]).exists())
        md = (self.pack / "evidence/traceability-matrix.md").read_text(encoding="utf-8")
        self.assertIn("revision 42", md)
        self.assertIn('`ORDERS.dxl, form "Order"`', md)

    def test_a_flaky_test_shows_the_try_that_failed(self):
        html = self.failing_run("flaky")
        self.assertIn("boom", html)
        self.assertIn('src="screenshots/enters.png"', html)

    def test_the_handover_zip_carries_the_failure_screenshots_the_matrix_shows(self):
        import re
        import zipfile
        html = self.failing_run()
        report = self.pack / "evidence/html-report/index.html"
        report.parent.mkdir(parents=True, exist_ok=True)
        report.write_text("<html></html>", encoding="utf-8")
        run = subprocess.run(["node", "scripts/handover.mjs"], cwd=self.pack, capture_output=True, text=True)
        self.assertEqual(run.returncode, 0, run.stderr)
        names = zipfile.ZipFile(next((self.pack / "dist").glob("*.zip"))).namelist()
        images = re.findall(r'<img src="([^"]+)"', html)
        self.assertTrue(images)
        for src in images:
            self.assertIn("evidence/" + src, names)
        self.assertFalse(any(n.startswith("evidence/artifacts/") for n in names))

    def test_the_handover_zip_leaves_out_the_builds_screen_test_runs(self):
        import zipfile
        self.failing_run()
        shot = self.pack / "evidence/screens/artifacts/x/test-failed-1.png"
        shot.parent.mkdir(parents=True, exist_ok=True)
        shot.write_bytes(b"\x89PNG fake")
        report = self.pack / "evidence/html-report/index.html"
        report.parent.mkdir(parents=True, exist_ok=True)
        report.write_text("<html></html>", encoding="utf-8")
        run = subprocess.run(["node", "scripts/handover.mjs"], cwd=self.pack, capture_output=True, text=True)
        self.assertEqual(run.returncode, 0, run.stderr)
        names = zipfile.ZipFile(next((self.pack / "dist").glob("*.zip"))).namelist()
        self.assertIn("evidence/traceability-matrix.html", names)
        self.assertFalse(any(n.startswith("evidence/screens/") for n in names), names)

    def test_the_rerun_server_refuses_bad_requests_and_stays_up(self):
        import http.client
        import socket
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            port = sock.getsockname()[1]
        server = subprocess.Popen(["node", "scripts/serve.mjs", "--no-open"], cwd=self.pack,
                                  env=dict(os.environ, PORT=str(port)), stdout=subprocess.PIPE, text=True)
        self.addCleanup(server.kill)
        self.assertIn("Test results", server.stdout.readline())

        def status(method, path, host=f"127.0.0.1:{port}"):
            conn = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
            conn.request(method, path, headers={"Host": host})
            return conn.getresponse().status

        self.assertEqual(status("GET", "/%E0%A4%A"), 400)
        self.assertEqual(status("GET", "/api/status", host="evil.example"), 403)
        self.assertEqual(status("POST", "/api/run"), 403)
        self.assertEqual(status("GET", "/..%2fpackage.json"), 403)
        self.assertEqual(status("GET", "/api/status"), 200)

        conn = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
        conn.request("GET", "/api/status")
        token = json.loads(conn.getresponse().read())["token"]

        def run(query):
            conn = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
            conn.request("POST", "/api/run?total=1" + query, headers={"x-pack-token": token})
            return conn.getresponse().status

        # Only ids requirements.json has reach the test filter.
        self.assertEqual(run("&id=REQ-999"), 400)
        self.assertEqual(run("&id=--reporter%3Dx"), 400)
        requirements = self.pack / "requirements/requirements.json"
        requirements.write_text("not json", encoding="utf-8")
        self.assertEqual(run("&id=REQ-001"), 500)
        self.assertIsNone(server.poll())

    def run_pack(self, playwright_status, matrix_crashes=False):
        """Runs scripts/run.mjs with a stub Playwright CLI that exits with `playwright_status`."""
        stub = self.pack / "node_modules/@playwright/test"
        stub.mkdir(parents=True, exist_ok=True)
        (stub / "package.json").write_text(json.dumps(
            {"name": "@playwright/test", "exports": {"./cli": "./cli.js"}}), encoding="utf-8")
        results = {"stats": {"startTime": "2026-10-27T10:00:00.000Z"}, "suites": [{"title": "orders.spec.ts", "specs": [
            _result("enters", ["@REQ-001"], "expected", [{"status": "passed"}])]}]}
        (stub / "cli.js").write_text(
            "const fs = require('fs'); const dir = process.env.EVIDENCE_DIR;\n"
            "fs.mkdirSync(dir, { recursive: true });\n"
            "fs.writeFileSync(dir + '/results.json', " + json.dumps(json.dumps(results)) + ");\n"
            "process.exit(" + str(playwright_status) + ");\n", encoding="utf-8")
        if matrix_crashes:
            (self.pack / "scripts/build-matrix.mjs").write_text("throw new Error('boom');\n", encoding="utf-8")
        return subprocess.run(["node", "scripts/run.mjs"], cwd=self.pack, capture_output=True, text=True)

    def test_run_exits_with_the_tests_status(self):
        self.assertEqual(self.run_pack(0).returncode, 0)
        self.assertTrue((self.pack / "evidence/summary.json").exists())
        self.assertEqual(self.run_pack(1).returncode, 1)

    def test_green_tests_with_a_crashed_matrix_fail_the_run(self):
        run = self.run_pack(0, matrix_crashes=True)
        self.assertNotEqual(run.returncode, 0)
        self.assertFalse((self.pack / "evidence/summary.json").exists())

    def test_no_results_means_no_matrix(self):
        run = subprocess.run(["node", "scripts/build-matrix.mjs"], cwd=self.pack, capture_output=True, text=True)
        self.assertEqual(run.returncode, 1)
        self.assertIn("no matrix", run.stderr)
        self.assertFalse((self.pack / "evidence/summary.json").exists())

    def grep_for(self, *ids):
        """The --grep pattern scripts/run.mjs hands Playwright for `npm run test:req -- <ids>`."""
        stub = self.pack / "node_modules/@playwright/test"
        stub.mkdir(parents=True, exist_ok=True)
        (stub / "package.json").write_text(json.dumps(
            {"name": "@playwright/test", "exports": {"./cli": "./cli.js"}}), encoding="utf-8")
        (stub / "cli.js").write_text(
            "const i = process.argv.indexOf('--grep');\n"
            "require('fs').writeFileSync('grep.txt', i < 0 ? '<all>' : process.argv[i + 1]);\n"
            "process.exit(1);\n", encoding="utf-8")
        run = subprocess.run(["node", "scripts/run.mjs", *ids], cwd=self.pack, capture_output=True, text=True)
        grep = self.pack / "grep.txt"
        self.assertTrue(grep.exists(), run.stderr)
        return grep.read_text(encoding="utf-8").split("|")

    def test_a_merged_id_selects_the_tests_tagged_with_its_canonical_id(self):
        # REQ-009 is merged into REQ-002, and a test is tagged with the canonical id.
        self.assertEqual(sorted(self.grep_for("REQ-009")), ["@REQ-002(?![\\w.-])", "@REQ-009(?![\\w.-])"])

    def test_a_test_id_selects_its_own_tag(self):
        self.assertEqual(self.grep_for("TEST-007"), ["@TEST-007(?![\\w.-])"])
        self.assertEqual(sorted(self.grep_for("REQ-001", "TEST-007")),
                         ["@REQ-001(?![\\w.-])", "@TEST-007(?![\\w.-])"])


@unittest.skipUnless(shutil.which("node"), "needs Node.js to run the pack's scripts")
class ScreensTest(Base):
    """scripts/screens.mjs and its compact reporter: the build loop's replay after a publish."""

    def setUp(self):
        super().setUp()
        self.scaffold()
        (self.pack / "tests/screens").mkdir(parents=True)
        for name in ("List", "CustomerList"):
            (self.pack / "tests/screens/{}.spec.ts".format(name)).write_text("// test\n", encoding="utf-8")

    def test_a_screens_run_turns_the_trace_off_and_keeps_only_failure_screenshots(self):
        # The light run the docs promise: SCREENS_RUN=1 switches the trace off and screenshots to failures only.
        config = (self.pack / "playwright.config.ts").read_text(encoding="utf-8")
        self.assertIn("const screensRun = process.env.SCREENS_RUN === '1';", config)
        self.assertRegex(config, r"trace:\s*screensRun\s*\?\s*'off'\s*:")
        self.assertRegex(config, r"screenshot:\s*screensRun\s*\?\s*'only-on-failure'\s*:")
        # ...and the evidence() helper takes no picture of a passing step on that run either.
        support = (self.pack / "tests/support.ts").read_text(encoding="utf-8")
        body = support.split("export async function evidence(", 1)[1].split("\n}\n", 1)[0]
        self.assertIn("if (process.env.SCREENS_RUN === '1') return;", body)
        self.assertLess(body.index("SCREENS_RUN"), body.index("page.screenshot"))

    def screens(self, *names, env=None):
        """Runs screens.mjs with a stub Playwright CLI that records what it was asked to run."""
        stub = self.pack / "node_modules/@playwright/test"
        stub.mkdir(parents=True, exist_ok=True)
        (stub / "package.json").write_text(json.dumps(
            {"name": "@playwright/test", "exports": {"./cli": "./cli.js"}}), encoding="utf-8")
        (stub / "cli.js").write_text(
            "require('fs').writeFileSync('ran.json', JSON.stringify({argv: process.argv.slice(2), "
            "dir: process.env.EVIDENCE_DIR, quick: process.env.SCREENS_RUN}));\n"
            "if (process.env.STUB_SIGNAL) process.kill(process.pid, process.env.STUB_SIGNAL);\n"
            "process.exit(Number(process.env.STUB_EXIT || 0));\n", encoding="utf-8")
        run = subprocess.run(["node", "scripts/screens.mjs", *names], cwd=self.pack, capture_output=True, text=True,
                             env={**os.environ, **(env or {})})
        ran = self.pack / "ran.json"
        return run, (json.loads(ran.read_text()) if ran.exists() else None)

    def test_runs_only_the_named_screens_light_and_apart_from_the_full_run(self):
        run, ran = self.screens("CustomerList,", "List")
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual((ran["dir"], ran["quick"]), ("evidence/screens", "1"))
        filters = [a for a in ran["argv"][1:] if not a.startswith("-") and "reporter" not in a]
        self.assertEqual(len(filters), 2)
        # Each filter matches its own file only: "List" must not also run CustomerList.
        node = "const f=process.argv.slice(1).map(s=>new RegExp(s));" \
               "console.log(JSON.stringify(['tests/screens/List.spec.ts','tests/screens/CustomerList.spec.ts']" \
               ".map(p=>f.map(r=>r.test(p)))))"
        hits = json.loads(subprocess.run(["node", "-e", node, *filters], capture_output=True, text=True).stdout)
        self.assertEqual(hits, [[False, True], [True, False]])
        self.assertIn("./scripts/compact-reporter.mjs", ran["argv"])

    def test_no_names_runs_every_test_in_the_pack(self):
        run, ran = self.screens()
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(ran["argv"], ["test", "--reporter", "./scripts/compact-reporter.mjs"])
        self.assertEqual((ran["dir"], ran["quick"]), ("evidence/screens", "1"))

    def test_the_exit_status_is_the_test_runs(self):
        # The build loop reads this status as the verdict, so a failing run must not exit 0.
        run, _ = self.screens(env={"STUB_EXIT": "1"})
        self.assertEqual(run.returncode, 1)
        run, _ = self.screens(env={"STUB_EXIT": "0"})
        self.assertEqual(run.returncode, 0)
        # Killed by a signal, the child has no status: that is a failure too, never a pass.
        run, _ = self.screens(env={"STUB_SIGNAL": "SIGTERM"})
        self.assertEqual(run.returncode, 1)

    def test_a_pack_that_cannot_run_exits_2_with_what_to_do(self):
        # A setup problem must not read as a failing test (exit 1) to the build loop.
        run = subprocess.run(["node", "scripts/screens.mjs"], cwd=self.pack, capture_output=True, text=True)
        self.assertEqual(run.returncode, 2, run.stderr)
        self.assertIn("@playwright/test is not installed. Run npm install && npm run setup", run.stderr)
        self.assertNotIn("MODULE_NOT_FOUND", run.stderr)

    def test_an_installed_playwright_whose_cli_wont_load_is_not_called_missing(self):
        # Reinstalling would not fix a release that dropped its ./cli export, so don't say to.
        stub = self.pack / "node_modules/@playwright/test"
        stub.mkdir(parents=True)
        (stub / "package.json").write_text(json.dumps(
            {"name": "@playwright/test", "exports": {"./other": "./other.js"}}), encoding="utf-8")
        run = subprocess.run(["node", "scripts/screens.mjs"], cwd=self.pack, capture_output=True, text=True)
        self.assertEqual(run.returncode, 2, run.stderr)
        self.assertNotIn("is not installed", run.stderr)
        self.assertIn("@playwright/test is installed but its CLI can't be loaded (ERR_PACKAGE_PATH_NOT_EXPORTED", run.stderr)

    def test_a_run_cut_short_says_so_instead_of_reading_green(self):
        self.assertEqual(self.report("""
r.onTestEnd(t('1', 'Orders', 'lists orders', 'expected'), { steps: [], attachments: [] });
r.onEnd({ status: 'timedout' });
"""), ["Screen tests: 1/1 PASS, INCOMPLETE (timedout).", "PASS 1/1: Orders › lists orders",
       "INCOMPLETE (timedout): 1 test(s) reported; the run ended before the rest."])
        # Failed with nothing above to say why.
        self.assertEqual(self.report("""
r.onTestEnd(t('1', 'Orders', 'lists orders', 'expected'), { steps: [], attachments: [] });
r.onEnd({ status: 'failed' });
""")[-1], "INCOMPLETE (failed): 1 test(s) reported; the run ended before the rest.")
        # A real failure already says why: no INCOMPLETE line on top.
        lines = self.report("""
r.onTestEnd(t('1', 'Orders', 'lists orders', 'unexpected'), { steps: [], attachments: [], error: { message: 'boom' } });
r.onEnd({ status: 'failed' });
""")
        self.assertFalse(any(l.startswith("INCOMPLETE") for l in lines), lines)

    def report(self, script):
        """The compact reporter's output for a hand-made run (``script`` drives ``r``)."""
        (self.pack / "fake.mjs").write_text(
            "import Reporter from './scripts/compact-reporter.mjs';\nconst r = new Reporter();\n"
            "const t = (id, file, title, outcome) => ({ id, title, outcome: () => outcome, "
            "location: { file: `/p/tests/screens/${file}.spec.ts` } });\n" + script, encoding="utf-8")
        run = subprocess.run(["node", "fake.mjs"], cwd=self.pack, capture_output=True, text=True)
        self.assertEqual(run.returncode, 0, run.stderr)
        return run.stdout.strip().splitlines()

    def test_the_report_counts_skipped_tests_and_says_when_none_ran(self):
        self.assertEqual(self.report("""
r.onTestEnd(t('1', 'Orders', 'lists orders', 'expected'), { steps: [], attachments: [] });
r.onTestEnd(t('2', 'Orders', 'approves', 'skipped'), { steps: [], attachments: [] });
r.onEnd({ status: 'passed' });
"""), ["Screen tests: 1/2 PASS.", "PASS 1/2: Orders › lists orders", "SKIPPED 1: Orders › approves"])
        self.assertEqual(self.report("r.onEnd({ status: 'failed' });\n"), ["Screen tests: none ran (failed)."])

    def test_the_report_names_a_spec_that_failed_to_load(self):
        # A compile or import error reaches onError, never onTestEnd: it must still be said.
        lines = self.report("""
r.onError({ message: '\\u001b[31mSyntaxError: Unexpected token\\u001b[39m\\n    at x', location: { file: process.cwd() + '/tests/screens/Broken.spec.ts', line: 3 } });
r.onTestEnd(t('1', 'Orders', 'lists orders', 'expected'), { steps: [], attachments: [] });
r.onEnd({ status: 'failed' });
""")
        # The verdict comes first and counts the spec that didn't load as a FAIL, once in the
        # total too: its tests never ran, so the run is not green even though every test that
        # ran passed, and the fraction agrees with the failure count.
        self.assertEqual(lines, ["Screen tests: 1/2 PASS, 1 FAIL.",
                                 "ERROR tests/screens/Broken.spec.ts: SyntaxError: Unexpected token",
                                 "PASS 1/2: Orders › lists orders"])
        self.assertEqual(self.report("r.onError({ message: 'Error: no config' });\nr.onEnd({ status: 'failed' });\n"),
                         ["Screen tests: none ran (failed), 1 FAIL.", "ERROR Error: no config"])

    def test_a_test_marked_to_fail_that_failed_is_not_a_pass(self):
        # test.fail() makes a failing body 'expected' and Playwright exits 0; the screen is broken.
        lines = self.report("""
r.onTestEnd(t('1', 'Orders', 'lists orders', 'expected'), { status: 'failed', steps: [], attachments: [], error: { message: 'Error: boom' } });
r.onTestEnd(t('2', 'Orders', 'approves', 'expected'), { status: 'passed', steps: [], attachments: [] });
r.onEnd({ status: 'passed' });
""")
        self.assertEqual(lines, ["Screen tests: 1/2 PASS, 1 FAIL.",
                                 "FAIL Orders › lists orders (marked test.fail()): Error: boom",
                                 "PASS 1/2: Orders › approves"])

    def test_the_pass_line_stays_short_however_many_tests_pass(self):
        [verdict, line] = self.report("""
for (let i = 0; i < 45; i++) r.onTestEnd(t(String(i), 'S' + String(i).padStart(2, '0'), 'loads', 'expected'), { steps: [], attachments: [] });
r.onEnd({ status: 'passed' });
""")
        self.assertTrue(line.startswith("PASS 45/45: S00 › loads; S01 › loads;"), line)
        self.assertTrue(line.endswith("; S19 › loads; +25 more"), line)
        self.assertNotIn("S20", line)
        self.assertEqual(verdict, "Screen tests: 45/45 PASS.")

    def test_an_unknown_screen_names_the_ones_with_tests_and_runs_nothing(self):
        run, ran = self.screens("Orders")
        self.assertEqual(run.returncode, 2)
        self.assertIsNone(ran)
        self.assertIn("No screen tests for: Orders. Screens with tests: CustomerList, List.", run.stderr)

    def test_the_report_is_one_line_per_failure_and_one_line_of_passes(self):
        self.assertEqual(self.report(r"""
r.onTestEnd(t('1', 'CustomerList', 'lists customers', 'expected'), { steps: [], attachments: [] });
r.onTestEnd(t('2', 'CustomerDetail', 'shows a customer', 'unexpected'), {
  steps: [{ title: 'Given a customer opens a record' }, { title: 'Then the name is shown', error: {} }],
  error: { message: '\u001b[31mError: expect(locator).toBeVisible() failed\u001b[39m\n\nLocator: getByText(\'Ada\')\nExpected: visible\nCall log: ...' },
  attachments: [{ contentType: 'image/png', path: process.cwd() + '/evidence/screens/x.png' }],
});
// A flaky test: its first try failed, its retry passed. The failing try is the one to show.
r.onTestEnd(t('3', 'Orders', 'lists orders', 'flaky'), {
  status: 'failed',
  steps: [{ title: 'Then the orders are listed', error: {} }],
  error: { message: 'Error: timed out' },
  attachments: [{ contentType: 'image/png', path: process.cwd() + '/evidence/screens/o.png' }],
});
r.onTestEnd(t('3', 'Orders', 'lists orders', 'flaky'), { status: 'passed', steps: [], attachments: [] });
r.onEnd({ status: 'failed' });
"""), [
            "Screen tests: 1/3 PASS, 2 FAIL.",
            'FAIL CustomerDetail › shows a customer at "Then the name is shown": Error: expect(locator).toBeVisible() '
            "failed · Locator: getByText('Ada') · Expected: visible (screenshot: evidence/screens/x.png)",
            'FLAKY Orders › lists orders (passed on retry) at "Then the orders are listed": Error: timed out '
            "(screenshot: evidence/screens/o.png)",
            "PASS 1/3: CustomerList › lists customers",
        ])

if __name__ == "__main__":
    unittest.main()
