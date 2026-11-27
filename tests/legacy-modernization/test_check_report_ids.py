"""Run with: python3 -m unittest discover -s scripts -p 'test_*.py'"""

import importlib.util
import json
import re
import shutil
import tempfile
import unittest
from pathlib import Path

_SCRIPT = (Path(__file__).resolve().parents[2]
           / "legacy-modernization/skills/outsystems-handover-docs/scripts/check_report_ids.py")
_spec = importlib.util.spec_from_file_location("check_report_ids", _SCRIPT)
check_report_ids = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(check_report_ids)

SPEC_IDS = ["BR-418", "RULE-012", "REQ-001", "REQ-002", "NFR-03"]

GOOD = """# Northwind Orders — Implementation Report

## 0. Cover and summary

REQ-001 and REQ-002 are built; RULE-012 is Changed.

## 5. Requirements list

| Req ID | Type | Source id | Description | Status | Tested | Built as | Evidence |
|---|---|---|---|---|---|---|---|
| REQ-00001 | Business rule | BR-418 | Credit limit needs approval | Implemented, tested | PASS | Order.Submit | J2 |
| REQ-00002 | Business rule | `RULE-012` | A rejected order returns to draft | Changed | PASS | ApprovalStep | note field |
| REQ-00003 | Functional requirement | **REQ-001** | Enter orders | Implemented, tested | PASS | NewOrder | J1 |
| REQ-00004 | Functional requirement | REQ-002 | Approvers see pending orders | Implemented, not tested | PARTIAL | Approvals | one region |
| REQ-00005 | Non-functional | NFR-03 | Pages load in under 2 s | Implemented, not tested | NOT OBSERVABLE | none | no load tool |
| REQ-00006 | Input | IN-01 | Export to CSV, from the brief | Implemented, tested | PASS | ExportCsv | J3 |

### Additions

| Id | Addition | Status | Tested | Built as | Evidence |
|---|---|---|---|---|---|
| ADD-01 | Dark mode | Implemented, tested | PASS | Theme | toggled |

## A. Traceability

| Spec id | Built element | Source |
|---|---|---|
| BR-418 | Order.Submit | agent, line 40 |
| RULE-012 | ApprovalStep.Decision | form, line 12 |
| REQ-001 | MainFlow/NewOrder | form, field OrdNo |
| REQ-002 | ApprovalFlow/Approvals | view, line 3 |
| NFR-03 | none | spec 09 |

```text
REQ-1 inside a code fence is not part of the report text.
```

## Z. Requirements checklist

**Implemented: 6 of 6. Tested: 4 of 5.**

| Spec id | Description | Implemented | Tested |
|---|---|---|---|
| BR-418 | Orders over the credit limit need approval | Yes | Yes |
| RULE-012 | A rejected order goes back to draft | Yes | Yes |
| REQ-001 | Staff can enter orders | Yes | Yes |
| REQ-002 | Approvers see the orders waiting for them | Yes | Partial |
| NFR-03 | Pages open in under 2 seconds | Yes | n/a |
| IN-01 | Orders export to a CSV file | Yes | Yes |
"""

BUSINESS_SPEC = """# Northwind Orders - Business Specification

## 5. Requirements list

| ID | Rule | Source |
|---|---|---|
| PMODEL-ORD100-0001 | If Order.Total > Customer.Limit | ORD100.pmodel:12 |
| REQ-001 | Enter orders | 06 |

## 9. Open questions

| ID | Question |
|---|---|
| UNK-001 | Who approves? |
"""


# The current extractor's section 5: numbered REQ-00001 upward, the spec id in Source id.
NUMBERED_BUSINESS_SPEC = """# Northwind Orders - Business Specification

## 5. Requirements list

### All requirements

| Req ID | Type | Source id | Description |
|---|---|---|---|
| REQ-00001 | business rule | PMODEL-ORD100-0001 | An order over the customer's limit waits for approval |
| REQ-00002 | functional requirement | REQ-001 | Staff can enter orders |

## 9. Open questions

| ID | Question |
|---|---|
| UNK-001 | Who approves? |
"""

def renumber(report: str) -> str:
    """Number section 5's requirement rows REQ-00001 upward, in order (a new row may say REQ-?????)."""
    counter = iter(range(1, 10000))
    return re.sub(r"(?m)^\| REQ-(?:[0-9]{5}|\?{5}) \|", lambda m: "| REQ-{:05d} |".format(next(counter)), report)


def with_rule(report: str, cell: str, a_cell: str = "", z_cell: str = "") -> str:
    """GOOD plus one implemented, tested rule row in section 5, appendix A and appendix Z."""
    report = re.sub(r"(?m)^(\| REQ-[0-9]{5} \| Input \| IN-01 \| Export to CSV)",
                    lambda m: "| REQ-????? | Business rule | {} | Orders over the limit wait for approval | "
                              "Implemented, tested | PASS | Order.Submit | J2 |\n{}".format(cell, m.group(1)), report)
    report = renumber(report)
    report = report.replace("| NFR-03 | none | spec 09 |",
                            "| NFR-03 | none | spec 09 |\n| {} | Order.Submit | rules, line 12 |".format(a_cell or cell))
    report = report.replace("| IN-01 | Orders export",
                            "| {} | Orders over the limit wait | Yes | Yes |\n| IN-01 | Orders export".format(z_cell or cell))
    return report.replace("Implemented: 6 of 6. Tested: 4 of 5.", "Implemented: 7 of 7. Tested: 5 of 6.")


class CheckReportIdsTest(unittest.TestCase):
    def setUp(self) -> None:
        self.dir = Path(tempfile.mkdtemp())
        self.requirements = self.dir / "requirements.json"
        self.write_requirements(SPEC_IDS)

    def write_requirements(self, ids, merged=None) -> None:
        rows = [{"id": i, "tier": "functional", "text": i, "source_slug": "06"} for i in ids]
        for row in rows:
            if merged and row["id"] in merged:
                row["merged"] = merged[row["id"]]
        self.requirements.write_text(json.dumps({"schema": "spec_projection.v1", "requirements": rows}),
                                     encoding="utf-8")

    def run_check(self, report: str, specs=(), business_specs=()):
        path = self.dir / "report.md"
        path.write_text(report, encoding="utf-8")
        problems, _ = check_report_ids.check(self.requirements, path, specs, business_specs)
        return problems

    def assertFlags(self, report: str, *needles: str) -> None:
        problems = self.run_check(report)
        for needle in needles:
            self.assertTrue(any(needle in p for p in problems), "{!r} not in {}".format(needle, problems))

    def test_aligned_report_passes(self) -> None:
        self.assertEqual(self.run_check(GOOD), [])

    def test_implemented_figure_counts_spec_ids_only(self) -> None:
        # Appendix Z's totals say 6 of 6 because they count the report-local IN-01 row too;
        # the figure is over the 5 spec ids, so an IN-nn row can't lift it.
        path = self.dir / "report.md"
        path.write_text(GOOD, encoding="utf-8")
        self.assertEqual(check_report_ids.implemented_figure(self.requirements, path), ((5, 5), []))

    def test_figure_counts_business_spec_ids(self) -> None:
        spec_dir = self.dir
        business = spec_dir / "Northwind-Business-Spec.md"
        business.write_text(BUSINESS_SPEC, encoding="utf-8")
        report = with_rule(GOOD, "PMODEL-ORD100-0001")
        path = self.dir / "report.md"
        path.write_text(report, encoding="utf-8")
        self.assertEqual(check_report_ids.implemented_figure(self.requirements, path, business_specs=[business]),
                         ((6, 6), []))

    def test_figure_pct_rounds_down(self) -> None:
        # 189 of 199 is 94.97%: printed as 95% it would pass a >=95% gate it failed.
        self.assertEqual(check_report_ids.figure_pct(189, 199), 94.9)
        self.assertEqual(check_report_ids.figure_pct(19, 20), 95.0)
        self.assertEqual(check_report_ids.figure_pct(0, 0), 0.0)

    def test_reqs_card_must_show_the_figure(self) -> None:
        card = "- **5% REQs implemented** 1 of 20 spec ids\n\n## 5. Requirements list"
        self.assertFlags(GOOD.replace("## 5. Requirements list", card, 1),
                         "the REQs implemented card says 5% (1 of 20), but appendix Z's spec-id rows count 5 of 5")

    def test_reqs_card_may_not_round_up(self) -> None:
        # 4 of 5 is 80%: a card reading 80.5% overstates it (rounded up), 79% understates it by under a point (rounded down).
        report = GOOD.replace("| REQ-002 | Approvers see pending orders | Implemented, not tested | PARTIAL |",
                              "| REQ-002 | Approvers see pending orders | Not built | NOT TESTED |")
        report = report.replace("| REQ-002 | Approvers see the orders waiting for them | Yes | Partial |",
                                "| REQ-002 | Approvers see the orders waiting for them | No | No |")
        report = report.replace("Implemented: 6 of 6. Tested: 4 of 5.", "Implemented: 5 of 6. Tested: 4 of 5.")
        self.assertEqual(self.run_check(report), [])
        up = report.replace("## 5. Requirements list", "- **80.5% REQs implemented** 4 of 5\n\n## 5. Requirements list", 1)
        self.assertFlags(up, "the REQs implemented card says 80.5% (4 of 5)")
        down = report.replace("## 5. Requirements list", "- **79.5% REQs implemented** 4 of 5\n\n## 5. Requirements list", 1)
        self.assertEqual(self.run_check(down), [])

    def test_a_report_without_appendix_z_has_no_figure_and_says_why(self) -> None:
        path = self.dir / "report.md"
        path.write_text(GOOD[:GOOD.index("## Z. Requirements checklist")], encoding="utf-8")
        figure, problems = check_report_ids.implemented_figure(self.requirements, path)
        self.assertIsNone(figure)
        self.assertTrue(any("no appendix Z heading" in p for p in problems), problems)

    def test_reqs_card_showing_the_figure_passes(self) -> None:
        card = "- **100% REQs implemented** 5 of 5 spec ids\n\n## 5. Requirements list"
        self.assertEqual(self.run_check(GOOD.replace("## 5. Requirements list", card, 1)), [])

    def test_implemented_figure_counts_only_implemented_rows(self) -> None:
        # The validator gate reads this figure: two rows Not built must lower it, not leave it at 6 of 6.
        report = GOOD
        for rid, z in (("REQ-001", "Staff can enter orders"), ("REQ-002", "Approvers see the orders waiting for them")):
            row = next(line for line in report.splitlines() if line.startswith("| REQ-0000")
                       and ("| {} |".format(rid) in line or "| **{}** |".format(rid) in line))
            cells = row.split("|")
            cells[5], cells[6] = " Not built ", " NOT TESTED "
            report = report.replace(row, "|".join(cells))
            report = report.replace("| {} | {} | Yes | {} |".format(rid, z, "Yes" if rid == "REQ-001" else "Partial"),
                                    "| {} | {} | No | No |".format(rid, z))
        report = report.replace("Implemented: 6 of 6. Tested: 4 of 5.", "Implemented: 4 of 6. Tested: 3 of 5.")
        path = self.dir / "report.md"
        path.write_text(report, encoding="utf-8")
        self.assertEqual(check_report_ids.implemented_figure(self.requirements, path), ((3, 5), []))

    def test_implemented_figure_of_a_failing_report_is_none(self) -> None:
        # A totals line that overstates its rows can't be the gate's number.
        path = self.dir / "report.md"
        path.write_text(GOOD.replace("Implemented: 6 of 6.", "Implemented: 6 of 5."), encoding="utf-8")
        figure, problems = check_report_ids.implemented_figure(self.requirements, path)
        self.assertIsNone(figure)
        self.assertTrue(any("appendix Z says implemented 6 of 5" in p for p in problems), problems)

    def test_figure_flag_prints_the_requirements_figure(self) -> None:
        import contextlib
        import io

        path = self.dir / "report.md"
        path.write_text(GOOD, encoding="utf-8")
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = check_report_ids.main([str(self.requirements), str(path), "--figure"])
        self.assertEqual(code, 0)
        self.assertIn("REQS IMPLEMENTED 5 of 5 (100%)", out.getvalue())

    def test_dropped_id(self) -> None:
        report = GOOD.replace("| NFR-03 | Pages load", "| NOTE | Pages load")
        self.assertFlags(report, "1 of 5 spec ids have no section 5 row: NFR-03")

    def test_renumbered_id(self) -> None:
        self.assertFlags(GOOD.replace("| **REQ-001** |", "| REQ-01 |"), "respells spec id REQ-001 as REQ-01")

    def test_unicode_dash(self) -> None:
        self.assertFlags(GOOD.replace("| REQ-002 | Approvers", "| REQ‑002 | Approvers"),
                         "respells spec id REQ-002 as REQ‑002")

    def test_respelling_in_prose(self) -> None:
        self.assertFlags(GOOD.replace("REQ-001 and REQ-002 are built", "Req-1 and REQ-002 are built"),
                         "respells spec id REQ-001 as Req-1")

    def test_code_fence_ignored(self) -> None:
        self.assertNotIn("REQ-1", " ".join(self.run_check(GOOD)))

    def test_unknown_id(self) -> None:
        self.assertFlags(GOOD.replace("| IN-01 |", "| REQ-099 |"), "cites REQ-099, which is not in the spec")

    def test_merged_row(self) -> None:
        report = GOOD.replace("| REQ-002 | Approvers", "| REQ-001, REQ-002 | Approvers")
        self.assertFlags(report, "one row merges REQ-001, REQ-002")

    def test_duplicate_row(self) -> None:
        report = GOOD.replace("| NFR-03 | Pages load", "| REQ-001 | again |\n| NFR-03 | Pages load")
        self.assertFlags(report, "REQ-001 already has a row")

    def test_missing_traceability_row(self) -> None:
        self.assertFlags(GOOD.replace("| NFR-03 | none | spec 09 |\n", ""),
                         "1 of 5 spec ids have no appendix A row: NFR-03")

    def test_missing_section(self) -> None:
        self.assertFlags(GOOD.replace("## 5. Requirements list", "## 5b Requirements"), "no section 5 heading")

    def test_capability_ids_from_the_brief(self) -> None:
        report = GOOD.replace("| IN-01 |", "| CAP-01 |")
        self.assertFlags(report, "cites CAP-01")
        brief = self.with_capabilities(report, "| CAP-01 | Capture an order | REQ-001 | NewOrder |\n")
        self.assertEqual(self.run_check(report, [brief]), [])

    def test_respelling_in_another_row_cell(self) -> None:
        self.assertFlags(GOOD.replace("| NewOrder | J1 |", "| NewOrder | see REQ-02 |"),
                         "respells spec id REQ-002 as REQ-02")

    def test_brief_respelling_is_not_admitted(self) -> None:
        report = GOOD.replace("REQ-001 and REQ-002 are built", "REQ-01 and REQ-002 are built")
        brief = self.with_capabilities(report, "| CAP-01 | Capture an order | REQ-01 | NewOrder |\n")
        problems = self.run_check(report, [brief])
        self.assertTrue(any("respells spec id REQ-001 as REQ-01" in p for p in problems), problems)

    def test_nested_heading_under_additions(self) -> None:
        report = GOOD.replace("### Additions\n", "### Additions\n\n#### Orders app\n")
        self.assertEqual(self.run_check(report), [])

    def test_additions_end_at_a_sibling_heading(self) -> None:
        report = GOOD.replace("## A. Traceability", "### Deferred\n\n| Id | Note |\n|---|---|\n| REQ-099 | x |\n\n## A. Traceability")
        self.assertFlags(report, "cites REQ-099")

    def test_space_and_undashed_respellings(self) -> None:
        self.assertFlags(GOOD.replace("REQ-001 and REQ-002 are built", "Req 1 and REQ002 are built"),
                         "respells spec id REQ-001 as Req 1", "respells spec id REQ-002 as REQ002")
        self.assertFlags(GOOD.replace("| NFR-03 | Pages load", "| NFR 03 | Pages load"),
                         "respells spec id NFR-03 as NFR 03")

    def test_ordinary_words_with_numbers_pass(self) -> None:
        report = GOOD.replace("REQ-001 and REQ-002 are built", "REQ-001 and REQ-002 are built for us 2 regions; item 3")
        self.assertEqual(self.run_check(report), [])

    def test_lowercase_family_word_is_not_an_id(self) -> None:
        # The spec has a US- id, so the case guard is the only thing keeping "us 2" prose.
        self.write_requirements(SPEC_IDS + ["US-002"])
        report = renumber(GOOD.replace("| REQ-00005 | Non-functional | NFR-03 | Pages load", "| REQ-????? | User story | US-002 | "
                                        "Story | Implemented, tested | PASS | y | z |\n| REQ-00005 | Non-functional | NFR-03 | Pages load"))
        report = report.replace("| NFR-03 | none | spec 09 |", "| US-002 | y | z |\n| NFR-03 | none | spec 09 |")
        report = report.replace("| IN-01 | Orders export", "| US-002 | A story | Yes | Yes |\n| IN-01 | Orders export")
        report = report.replace("Implemented: 6 of 6. Tested: 4 of 5.", "Implemented: 7 of 7. Tested: 5 of 6.")
        self.assertEqual(self.run_check(report), [])
        problems = self.run_check(report.replace("REQ-001 and REQ-002 are built", "REQ-001 and REQ-002 are built for us 2 regions"))
        self.assertEqual(problems, [])
        self.assertFlags(report.replace("REQ-001 and REQ-002 are built", "US 2 and REQ-002 are built"),
                         "respells spec id US-002 as US 2")

    def test_additions_still_flag_spec_ids_and_respellings(self) -> None:
        self.assertFlags(GOOD.replace("| ADD-01 | Dark mode", "| REQ-01 | Dark mode"), "respells spec id REQ-001 as REQ-01")
        self.assertFlags(GOOD.replace("| ADD-01 | Dark mode", "| REQ-002 | Dark mode"),
                         "REQ-002 is a spec id; it belongs in the requirements list, not under Additions")

    def test_bad_requirements_json_fails_cleanly(self) -> None:
        for raw in (b"", b"{not json", b'"REQ-001"'):
            with self.subTest(raw=raw):
                self.requirements.write_bytes(raw)
                problems = self.run_check(GOOD)
                self.assertEqual(len(problems), 1, problems)
                self.assertIn("requirements.json", problems[0])

    def test_bom_and_top_level_list_are_read(self) -> None:
        rows = [{"id": i} for i in SPEC_IDS]
        self.requirements.write_bytes(b"\xef\xbb\xbf" + json.dumps(rows).encode("utf-8"))
        self.assertEqual(self.run_check(GOOD), [])
        path = self.dir / "report.md"
        path.write_bytes(b"\xef\xbb\xbf" + GOOD.encode("utf-8"))
        self.assertEqual(check_report_ids.check(self.requirements, path)[0], [])

    def test_brief_admits_only_capability_ids(self) -> None:
        report = GOOD.replace("| IN-01 |", "| FR-900 |")
        brief = self.with_capabilities(GOOD.replace("| IN-01 |", "| CAP-01 |"), "| FR-900 | Invented | REQ-001 | NewOrder |\n"
                                             "| CAP-01 | Capture | REQ-001 | NewOrder |\n")
        self.assertTrue(any("cites FR-900" in p for p in self.run_check(report, [brief])))
        self.assertEqual(self.run_check(GOOD.replace("| IN-01 |", "| CAP-01 |"), [brief]), [])

    def test_links_and_case_outside_the_id_cell(self) -> None:
        report = GOOD.replace("| **REQ-001** |", "| [REQ-001](#req-001) |")
        report = report.replace("| REQ-002 | ApprovalFlow/Approvals | view, line 3 |",
                                "| REQ-002 | ApprovalFlow/Approvals | shots/req-002.png |")
        self.assertEqual(self.run_check(report), [])
        # In the id cell, a case change is still a respelling.
        self.assertFlags(GOOD.replace("| **REQ-001** |", "| req-001 |"), "respells spec id REQ-001 as req-001")

    def test_missing_files_fail_cleanly(self) -> None:
        problems, _ = check_report_ids.check(self.requirements, self.dir / "nope.md")
        self.assertEqual(len(problems), 1, problems)
        self.assertIn("nope.md", problems[0])
        path = self.dir / "report.md"
        path.write_text(GOOD, encoding="utf-8")
        problems, _ = check_report_ids.check(self.requirements, path, [self.dir / "no-brief.md"])
        self.assertEqual(len(problems), 1, problems)
        self.assertIn("no-brief.md", problems[0])

    def test_tables_without_leading_pipes(self) -> None:
        def unpipe(text: str) -> str:
            return "\n".join(line.strip()[1:-1].strip() if line.startswith("|") else line for line in text.splitlines())
        self.assertEqual(self.run_check(unpipe(GOOD)), [])
        self.assertFlags(unpipe(GOOD.replace("| **REQ-001** |", "| REQ-01 |")), "respells spec id REQ-001 as REQ-01")

    def test_suffixed_id_is_not_the_spec_id(self) -> None:
        report = GOOD.replace("| **REQ-001** |", "| REQ-001-v2 |").replace("| REQ-001 | MainFlow", "| REQ-001-v2 | MainFlow")
        self.assertFlags(report, "no section 5 row: REQ-001", "no appendix A row: REQ-001")

    def test_case_change_in_prose_is_a_respelling(self) -> None:
        for prose in ("Req-001 is implemented.", "req-001 is implemented."):
            with self.subTest(prose=prose):
                self.assertFlags(GOOD.replace("REQ-001 and REQ-002 are built", prose + " REQ-002 is built"),
                                 "respells spec id REQ-001 as " + prose.split()[0])
        self.assertFlags(GOOD.replace("| NewOrder | J1 |", "| NewOrder | see Req-002 |"),
                         "respells spec id REQ-002 as Req-002")
        # Addresses keep their own spelling.
        report = GOOD.replace("REQ-001 and REQ-002 are built",
                              "REQ-001 and REQ-002 are built; see https://example.test/req-001 and reports/req-002.md")
        self.assertEqual(self.run_check(report), [])

    def test_unsupported_requirements_shape_fails(self) -> None:
        for data in ({"requirements": {"REQ-001": {"text": "x"}}}, {"by_tier": ["REQ-001"]}, {"requirements": []}, []):
            with self.subTest(data=data):
                self.requirements.write_text(json.dumps(data), encoding="utf-8")
                problems = self.run_check(GOOD)
                self.assertEqual(len(problems), 1, problems)
                self.assertIn("requirements.json", problems[0])

    def test_row_without_an_id_in_the_requirements_table(self) -> None:
        report = GOOD.replace("| NFR-03 | Pages load", "| TBD | Export orders | Implemented, tested | PASS | x | y |\n| NFR-03 | Pages load")
        self.assertFlags(report, "a row with no spec id (TBD)")
        # A table with no id rows at all (a summary table) is not the requirements list.
        summary = GOOD.replace("## A. Traceability", "| App | Rows |\n|---|---|\n| Orders | 6 |\n\n## A. Traceability")
        self.assertEqual(self.run_check(summary), [])

    def test_escaped_dash_is_the_same_id(self) -> None:
        self.assertEqual(self.run_check(GOOD.replace("| BR-418 | Credit", "| BR\\-418 | Credit")), [])

    def test_nested_fences(self) -> None:
        report = GOOD + "\n````md\n```text\nREQ-1\n```\n````\n\nREQ-01 after the fence.\n"
        problems = self.run_check(report)
        self.assertFalse(any("as REQ-1" in p for p in problems), problems)
        self.assertTrue(any("as REQ-01" in p for p in problems), problems)

    def test_appendix_heading_spelled_out(self) -> None:
        self.assertEqual(self.run_check(GOOD.replace("## A. Traceability", "## Appendix A — Traceability")), [])

    def test_business_spec_only_ids_join_the_one_list(self) -> None:
        spec = self.dir / "Northwind-Business-Spec.md"
        spec.write_text(BUSINESS_SPEC, encoding="utf-8")
        problems = self.run_check(GOOD, business_specs=[spec])
        for label in ("section 5", "appendix A", "appendix Z"):
            self.assertTrue(any("no {} row: PMODEL-ORD100-0001".format(label) in p for p in problems), problems)
        self.assertFalse(any("UNK-001" in p for p in problems), problems)
        report = renumber(GOOD.replace("| REQ-00006 | Input | IN-01 | Export to CSV",
                                       "| REQ-????? | Business rule | PMODEL-ORD100-0001 | Orders over the limit wait for "
                                       "approval | Implemented, tested | PASS | Order.Submit | J2 |\n"
                                       "| REQ-00006 | Input | IN-01 | Export to CSV"))
        report = report.replace("| NFR-03 | none | spec 09 |",
                                "| NFR-03 | none | spec 09 |\n| PMODEL-ORD100-0001 | Order.Submit | ORD100.pmodel:12 |")
        report = report.replace("| IN-01 | Orders export",
                                "| `PMODEL-ORD100-0001` | Orders over the limit wait | Yes | Yes |\n| IN-01 | Orders export")
        report = report.replace("Implemented: 6 of 6. Tested: 4 of 5.", "Implemented: 7 of 7. Tested: 5 of 6.")
        self.assertEqual(self.run_check(report, business_specs=[spec]), [])
        # Without the Business Spec the id is not a spec id, so its row is flagged rather than passed.
        self.assertFlags(report, "cites PMODEL-ORD100-0001, which is not in the spec (if the Business Spec numbers "
                                 "it, pass --business-spec)")

    def test_native_rule_ids_of_any_prefix(self) -> None:
        # Own-tools rules keep their native ids; one that contains a family token is still one id.
        for rid in ("MSACCESS-RULE-0007", "AS400-3f9a1c-ORDCHK-0002", "PMODEL-ORD100-0001"):
            with self.subTest(rid=rid):
                self.write_requirements(SPEC_IDS + [rid])
                self.assertEqual(self.run_check(with_rule(GOOD, rid)), [])
                self.assertFlags(GOOD, "no section 5 row: " + rid)
        self.write_requirements(SPEC_IDS + ["MSACCESS-RULE-0007"])
        self.assertFlags(with_rule(GOOD, "MSACCESS-RULE-0008"), "no section 5 row: MSACCESS-RULE-0007")

    def test_prefixed_or_suffixed_id_never_satisfies_a_shorter_one(self) -> None:
        self.write_requirements(SPEC_IDS + ["RULE-0002"])
        self.assertEqual(self.run_check(with_rule(GOOD, "RULE-0002")), [])
        problems = self.run_check(with_rule(GOOD, "MSACCESS-RULE-0002"))
        for label in ("section 5", "appendix A", "appendix Z"):
            self.assertTrue(any("no {} row: RULE-0002".format(label) in p for p in problems), problems)
        self.write_requirements(SPEC_IDS + ["PMODEL-ORD100-0001"])
        self.assertFlags(with_rule(GOOD, "PMODEL-ORD100-0001.v2"), "no section 5 row: PMODEL-ORD100-0001")
        # Punctuation after an id is not part of it.
        self.assertEqual(self.run_check(with_rule(GOOD, "PMODEL-ORD100-0001.")), [])

    def test_formatting_cannot_hide_a_business_spec_id(self) -> None:
        spec = self.dir / "Northwind-Business-Spec.md"
        for cell in ("_PMODEL-ORD100-0001_", "__PMODEL-ORD100-0001__", "[PMODEL-ORD100-0001](#rule-1)"):
            with self.subTest(cell=cell):
                spec.write_text(BUSINESS_SPEC.replace("| PMODEL-ORD100-0001 |", "| {} |".format(cell)),
                                encoding="utf-8")
                problems = self.run_check(GOOD, business_specs=[spec])
                for label in ("section 5", "appendix A", "appendix Z"):
                    self.assertTrue(any("no {} row: PMODEL-ORD100-0001".format(label) in p for p in problems),
                                    problems)

    def test_underscore_emphasis_reads_like_asterisks(self) -> None:
        report = GOOD.replace("| Staff can enter orders | Yes | Yes |", "| Staff can enter orders | _Yes_ | __Yes__ |")
        report = report.replace("| Enter orders | Implemented, tested |", "| Enter orders | _Implemented, tested_ |")
        self.assertEqual(self.run_check(report), [])
        # An underscore inside an id is part of it, emphasised or not.
        rid = "AS400-3f9a1c-ORD_CHK-0002"
        self.write_requirements(SPEC_IDS + [rid])
        self.assertEqual(self.run_check(with_rule(GOOD, "_{}_".format(rid), a_cell=rid)), [])
        self.assertFlags(with_rule(GOOD, "AS400-3f9a1c-ORDCHK-0002"), "no section 5 row: " + rid)

    def test_a_linked_status_or_answer_reads_by_its_label(self) -> None:
        report = GOOD.replace("| Enter orders | Implemented, tested | PASS |",
                              "| Enter orders | [Implemented, tested](#evidence) | [PASS](#j1) |")
        report = report.replace("| Staff can enter orders | Yes | Yes |",
                                "| Staff can enter orders | [Yes](#evidence) | [Yes](#j1) |")
        report = report.replace("| Source id | Description | Status |", "| Source id | [Description](#how-to-read) | Status |")
        self.assertEqual(self.run_check(report), [])

    def test_a_link_target_is_not_a_description(self) -> None:
        for cell in ("[](https://example.test/spec)", "[REQ-001](https://example.test/spec)", "REQ-002", "RULE-012."):
            with self.subTest(cell=cell):
                self.assertFlags(GOOD.replace("| Approvers see pending orders |", "| {} |".format(cell)),
                                 "REQ-002 has no description")
                self.assertFlags(GOOD.replace("| Approvers see the orders waiting for them |", "| {} |".format(cell)),
                                 "REQ-002 has no description")
        # A description may still mention an id beside its words.
        self.assertEqual(self.run_check(GOOD.replace("| Approvers see pending orders |",
                                                     "| Approvers see pending orders (see REQ-001) |")), [])

    def test_an_evidence_url_is_not_prose(self) -> None:
        report = GOOD.replace("| NewOrder | J1 |", "| NewOrder | https://example.test/REQ-001/req-002 |")
        self.assertEqual(self.run_check(report), [])

    def test_only_the_visible_link_text_cites_an_id(self) -> None:
        # A hidden target does not cite the id the reader can't see.
        self.assertFlags(GOOD.replace("| **REQ-001** |", "| [Order entry](#REQ-001) |"),
                         "a row with no spec id ([Order entry](#REQ-001))", "no section 5 row: REQ-001")
        # A visible id keeps its row even when the target names other ids.
        self.assertEqual(self.run_check(GOOD.replace("| **REQ-001** |",
                                                     "| [REQ-001](https://example.test/REQ-002#REQ-001) |")), [])

    def test_native_ids_count_only_in_requirement_tables(self) -> None:
        summary = "| App | Rows |\n|---|---|\n| Orders-v2 | 6 |\n\n### Additions"
        self.assertEqual(self.run_check(GOOD.replace("### Additions", summary)), [])
        unknown = ("| Spec id | Description | Status | Tested | Built as | Evidence |\n|---|---|---|---|---|---|\n"
                   "| MSACCESS-RULE-0099 | Invented | Implemented, tested | PASS | x | y |\n\n### Additions")
        self.assertFlags(GOOD.replace("### Additions", unknown), "cites MSACCESS-RULE-0099",
                         "section 5 splits the spec ids over 2 tables")

    def test_an_invented_native_id_fails(self) -> None:
        self.write_requirements(SPEC_IDS + ["MSACCESS-RULE-0007"])
        report = with_rule(GOOD, "MSACCESS-RULE-0007")
        self.assertFlags(report.replace("| **REQ-001** |", "| REQ-001, MSACCESS-RULE-0099 |"),
                         "cites MSACCESS-RULE-0099, which is not in the spec", "one row merges")
        extra = report.replace("### Additions", "### More rules\n\n| Spec id | Description | Status | Tested | Built as "
                               "| Evidence |\n|---|---|---|---|---|---|\n| MSACCESS-RULE-0099 | Invented | Implemented, "
                               "tested | PASS | x | y |\n\n### Additions")
        self.assertFlags(extra, "section 5 splits the spec ids over 2 tables", "cites MSACCESS-RULE-0099")

    def test_business_spec_must_be_the_extractors(self) -> None:
        spec = self.dir / "Northwind-Business-Spec.md"
        spec.write_text(BUSINESS_SPEC.replace("| ID | Rule |", "| **ID** | Rule |"), encoding="utf-8")
        self.assertTrue(any("no section 5 row: PMODEL-ORD100-0001" in p
                            for p in self.run_check(GOOD, business_specs=[spec])))
        spec.write_text(BUSINESS_SPEC.replace("## 5. Requirements list", "## Overview"), encoding="utf-8")
        message = self.run_check(GOOD, business_specs=[spec])[0]
        self.assertIn("fix the heading", message)
        self.assertNotIn("pass only the domain specs", message)
        # The reporter's own brief must not turn its ids into spec ids.
        brief = self.dir / "Northwind-business-brief.md"
        brief.write_text(BUSINESS_SPEC.replace("PMODEL-ORD100-0001", "FR-900"), encoding="utf-8")
        self.assertEqual(self.run_check(with_rule(GOOD, "FR-900"), business_specs=[brief]),
                         ["Northwind-business-brief.md: is a Business Brief, not the extractor's Business Spec; "
                          "pass it with --spec"])
        elsewhere = self.dir / "reports" / "Northwind-Business-Spec.md"
        elsewhere.parent.mkdir()
        elsewhere.write_text(BUSINESS_SPEC, encoding="utf-8")
        self.assertIn("is not in the spec collection", self.run_check(GOOD, business_specs=[elsewhere])[0])
        domain = self.dir / "domains" / "001-orders" / "Northwind-Orders-Business-Spec.md"
        domain.parent.mkdir(parents=True)
        domain.write_text(BUSINESS_SPEC, encoding="utf-8")
        self.assertEqual(self.run_check(with_rule(GOOD, "PMODEL-ORD100-0001"), business_specs=[domain]), [])

    def test_a_status_may_carry_its_reason(self) -> None:
        report = GOOD.replace("| Implemented, not tested | PARTIAL | Approvals |",
                              "| Implemented, not tested (one region) | PARTIAL: region filter not driven | Approvals |")
        report = report.replace("| NOT OBSERVABLE | none |", "| NOT OBSERVABLE  (no load tool) | none |")
        self.assertEqual(self.run_check(report), [])
        self.assertFlags(GOOD.replace("| PARTIAL | Approvals |", "| PARTIALLY | Approvals |"),
                         "REQ-002 tested is 'PARTIALLY', not one of")

    def test_a_dash_joined_range_still_shows_a_respelling(self) -> None:
        self.assertFlags(GOOD.replace("REQ-001 and REQ-002 are built", "REQ-001–REQ-02 are built"),
                         "respells spec id REQ-002 as REQ-02")

    def test_requirements_are_numbered_from_req_00001_in_order(self) -> None:
        self.assertEqual(self.run_check(GOOD), [])
        self.assertFlags(GOOD.replace("| REQ-00003 | Functional", "| REQ-00004 | Functional"),
                         "Req ID is 'REQ-00004', expected REQ-00003")
        self.assertFlags(GOOD.replace("| REQ-00001 | Business rule", "| REQ-1 | Business rule"),
                         "Req ID is 'REQ-1', expected REQ-00001")
        self.assertFlags(GOOD.replace("| REQ-00004 | Functional requirement |", "| REQ-00004 |  |"),
                         "REQ-00004 has no Type")
        self.assertFlags(GOOD.replace("| Req ID | Type | Source id |", "| Type | Source id |").replace(
            "| REQ-00001 | Business rule | BR-418", "| Business rule | BR-418"), "has no Req ID column")
        # The running number is not a spec id, so it never reads as a respelling of REQ-001.
        self.assertFalse(any("respells" in p for p in self.run_check(GOOD)))

    def with_capabilities(self, report: str, rows: str) -> Path:
        """A brief whose section 5 matches `report`, plus a capability table after it."""
        brief = self.write_brief(report)
        brief.write_text(brief.read_text(encoding="utf-8") + "\n## 6. Capabilities\n\n" + rows, encoding="utf-8")
        return brief

    def write_brief(self, report: str) -> Path:
        """A Business Brief whose section 5 is the report's numbered table, minus the build columns."""
        rows = [line for line in report.split("## A.")[0].split("### Additions")[0].splitlines()
                if line.startswith("| REQ-") or line.startswith("| Req ID")]
        table = ["| " + " | ".join(line.strip("|").split("|")[i].strip() for i in range(4)) + " |" for line in rows]
        table.insert(1, "|---|---|---|---|")
        brief = self.dir / "Northwind-business-brief.md"
        brief.write_text("# Northwind - Business Specification\n\n## 5. Requirements\n\n" + "\n".join(table) + "\n",
                         encoding="utf-8")
        return brief

    def test_the_report_maps_the_briefs_table_one_for_one_in_order(self) -> None:
        brief = self.write_brief(GOOD)
        self.assertEqual(self.run_check(GOOD, specs=[brief]), [])
        # Same rows, two swapped: the order differs from the brief's.
        swapped = GOOD.replace("| REQ-00003 | Functional requirement | **REQ-001** | Enter orders |",
                               "| REQ-00003 | Functional requirement | REQ-002 | Enter orders |", 1)
        self.assertTrue(any("row REQ-00003 is REQ-002" in p and "has REQ-00003 REQ-001" in p
                            for p in self.run_check(swapped, specs=[brief])), self.run_check(swapped, specs=[brief]))
        # A different Type for the same requirement.
        self.assertTrue(any("row REQ-00005" in p for p in self.run_check(
            GOOD.replace("| REQ-00005 | Non-functional |", "| REQ-00005 | Business rule |"), specs=[brief])))
        # A row the brief doesn't have.
        longer = self.write_brief(with_rule(GOOD, "BR-418"))
        self.assertTrue(any("lists 6 requirements but Northwind-business-brief.md section 5 lists 7" in p
                            for p in self.run_check(GOOD, specs=[longer])))

    def test_a_brief_without_a_section_5_table_fails(self) -> None:
        brief = self.write_brief(GOOD)
        good = brief.read_text(encoding="utf-8")
        table = good.split("## 5. Requirements\n\n")[1]
        for text in (good.replace("## 5. Requirements", "## 6. Requirements"),
                     good.replace("## 5. Requirements", "## Requirements"),
                     good.replace("## 5. Requirements", "### 5. Requirements"),
                     "# Northwind\n\nNo requirements yet.\n",
                     "",
                     good.replace(table, table.splitlines()[0] + "\n" + table.splitlines()[1] + "\n")):
            with self.subTest(text=text[:60]):
                brief.write_text(text, encoding="utf-8")
                problems = self.run_check(GOOD, specs=[brief])
                self.assertTrue(any("no section-5 requirements table" in p for p in problems), problems)

    def test_the_brief_is_numbered_too(self) -> None:
        brief = self.write_brief(GOOD)
        brief.write_text(brief.read_text(encoding="utf-8").replace("| REQ-00002 |", "| REQ-00009 |"), encoding="utf-8")
        self.assertTrue(any("Northwind-business-brief.md" in p and "expected REQ-00002" in p
                            for p in self.run_check(GOOD, specs=[brief])))

    def test_a_missing_status_column_fails_once(self) -> None:
        problems = self.run_check(GOOD.replace("| Source id | Description | Status |", "| Source id | Description | State |"))
        self.assertEqual(sum("no Status column" in p for p in problems), 1, problems)

    def test_checklist_lists_every_section_5_row(self) -> None:
        self.assertFlags(GOOD.replace("| IN-01 | Orders export to a CSV file | Yes | Yes |\n", "").replace(
            "Implemented: 6 of 6. Tested: 4 of 5.", "Implemented: 5 of 5. Tested: 3 of 4."),
            "IN-01 has no appendix Z row")
        self.assertFlags(GOOD.replace("| IN-01 | Orders export", "| IN-02 | Invented | Yes | Yes |\n| IN-01 | Orders export")
                         .replace("Implemented: 6 of 6. Tested: 4 of 5.", "Implemented: 7 of 7. Tested: 5 of 6."),
                         "IN-02 has no section-5 row")

    def test_checklist_needs_a_readable_section_5_status(self) -> None:
        self.assertFlags(GOOD.replace("| Source id | Description | Status | Tested |", "| Source id | Description | State | Result |"),
                         "the requirements table has no Status column", "the requirements table has no Tested column")
        self.assertFlags(GOOD.replace("| Enter orders | Implemented, tested |", "| Enter orders | Built |"),
                         "REQ-001 status is 'Built', not one of")
        # A status badge reads as the status it wraps, so a contradiction behind one still fails.
        badge = GOOD.replace("| Enter orders | Implemented, tested | PASS |",
                             '| Enter orders | <span style="color:gray">Deferred</span> | NOT TESTED |')
        self.assertFlags(badge, "REQ-001 implemented says Yes but its section-5 row says No")

    def test_business_spec_ids_come_from_its_id_table_only(self) -> None:
        spec = self.dir / "Northwind-Business-Spec.md"
        spec.write_text(BUSINESS_SPEC.replace("## 9. Open questions", "| Step | What |\n|---|---|\n| Phase-1 | Load |\n\n"
                                              "## 9. Open questions"), encoding="utf-8")
        problems = self.run_check(GOOD, business_specs=[spec])
        self.assertFalse(any("Phase-1" in p for p in problems), problems)
        self.assertTrue(any("PMODEL-ORD100-0001" in p for p in problems), problems)

    def test_a_req_id_numbered_business_spec_reads_its_source_ids(self) -> None:
        # The current extractor numbers section 5 REQ-00001 upward and cites the spec id in Source id.
        spec = self.dir / "Northwind-Business-Spec.md"
        spec.write_text(NUMBERED_BUSINESS_SPEC, encoding="utf-8")
        self.assertEqual(check_report_ids.business_spec_ids(spec, self.requirements),
                         ["PMODEL-ORD100-0001", "REQ-001"])
        self.assertEqual(self.run_check(with_rule(GOOD, "PMODEL-ORD100-0001"), business_specs=[spec]), [])
        # The Source id is a spec id like any other: the report still needs its rows.
        problems = self.run_check(GOOD, business_specs=[spec])
        self.assertTrue(any("no section 5 row: PMODEL-ORD100-0001" in p for p in problems), problems)
        # The Req ID numbers are the Business Spec's own, never spec ids the report must cite.
        self.assertFalse(any("REQ-00001" in p or "REQ-00002" in p for p in problems), problems)

    def test_a_split_overview_numbered_by_req_id_reads_its_source_ids(self) -> None:
        # The overview's table carries a trailing Domains column; the domain specs' tables don't.
        overview = self.dir / "Northwind-Business-Spec.md"
        overview.write_text(NUMBERED_BUSINESS_SPEC.replace("| Description |\n|---|---|---|---|",
                                                           "| Description | Domains |\n|---|---|---|---|---|")
                            .replace("limit |", "limit | Orders |").replace("orders |", "orders | Orders |"),
                            encoding="utf-8")
        domain = self.dir / "domains" / "001-orders" / "Northwind-Orders-Business-Spec.md"
        domain.parent.mkdir(parents=True)
        domain.write_text(NUMBERED_BUSINESS_SPEC, encoding="utf-8")
        for spec in (overview, domain):
            with self.subTest(spec=spec.name):
                self.assertEqual(check_report_ids.business_spec_ids(spec, self.requirements, split=True),
                                 ["PMODEL-ORD100-0001", "REQ-001"])
        self.assertEqual(self.run_check(with_rule(GOOD, "PMODEL-ORD100-0001"), business_specs=[overview, domain]),
                         [])

    def test_a_req_id_row_without_a_known_source_id_fails(self) -> None:
        spec = self.dir / "Northwind-Business-Spec.md"
        for source in ("", "-", "see rules", "Order total"):
            with self.subTest(source=source):
                spec.write_text(NUMBERED_BUSINESS_SPEC.replace("| PMODEL-ORD100-0001 |", "| {} |".format(source)),
                                encoding="utf-8")
                problems = self.run_check(with_rule(GOOD, "PMODEL-ORD100-0001"), business_specs=[spec])
                self.assertEqual(len(problems), 1, problems)
                self.assertIn("(REQ-00001): the Source id cell", problems[0])
                self.assertIn("names no spec id", problems[0])
        # No Source id column at all: the table names no spec id, so it fails rather than passing empty.
        spec.write_text(NUMBERED_BUSINESS_SPEC.replace("| Source id ", "| Origin "), encoding="utf-8")
        problems = self.run_check(GOOD, business_specs=[spec])
        self.assertEqual(len(problems), 1, problems)
        self.assertIn("numbered by Req ID but has no Source id column", problems[0])

    def test_a_business_spec_with_neither_table_names_both_shapes(self) -> None:
        spec = self.dir / "Northwind-Business-Spec.md"
        spec.write_text("# Northwind\n\n## 5. Requirements list\n\nNone yet.\n", encoding="utf-8")
        message = self.run_check(GOOD, business_specs=[spec])[0]
        self.assertIn("table headed ID or numbered by Req ID", message)

    def test_merged_ids_are_covered_by_their_parent(self) -> None:
        parent, folded = "PMODEL-ORD100-0001", ["PMODEL-ORD100-0002", "PMODEL-ORD100-0003"]
        self.write_requirements(SPEC_IDS + [parent], merged={parent: folded})
        self.assertEqual(self.run_check(with_rule(GOOD, parent)), [])
        both = "{}, {}".format(parent, ", ".join(folded))
        self.assertEqual(self.run_check(with_rule(GOOD, both)), [])
        self.assertEqual(self.run_check(with_rule(GOOD, folded[0], a_cell=parent, z_cell=folded[1])), [])
        # A folded id with a row of its own beside its parent's is a second row for the same requirement.
        report = with_rule(GOOD, parent).replace(
            "| IN-01 | Export to CSV", "| {} | Same rule again | Implemented, tested | PASS | x | y |\n"
            "| IN-01 | Export to CSV".format(folded[0]))
        self.assertFlags(report, "{} (folded into {}) already has a row".format(folded[0], parent))
        self.assertFlags(with_rule(GOOD, "{}, REQ-001".format(folded[0])), "one row merges")
        # The Business Spec still numbers the folded ids; they are not demanded again.
        spec = self.dir / "Northwind-Business-Spec.md"
        spec.write_text(BUSINESS_SPEC.replace("| REQ-001 | Enter orders | 06 |", "| {} | Same | 7 |\n"
                                              "| REQ-001 | Enter orders | 06 |".format(folded[0])), encoding="utf-8")
        self.assertEqual(self.run_check(with_rule(GOOD, parent), business_specs=[spec]), [])

    def test_bad_merged_shape_fails_cleanly(self) -> None:
        for merged in ("PMODEL-ORD100-0002", [""], [7]):
            with self.subTest(merged=merged):
                self.write_requirements(SPEC_IDS, merged={"REQ-001": merged})
                problems = self.run_check(GOOD)
                self.assertEqual(len(problems), 1, problems)
                self.assertIn("`merged`", problems[0])

    def test_requirements_split_over_two_tables(self) -> None:
        report = GOOD.replace("| REQ-00005 | Non-functional | NFR-03 | Pages load",
                              "\n### Rules numbered only in the Business Spec\n\n"
                              "| Spec id | Description | Status | Tested | Built as | Evidence |\n|---|---|---|---|---|---|\n"
                              "| NFR-03 | Pages load")
        self.assertFlags(report, "section 5 splits the spec ids over 2 tables")

    def test_every_requirement_has_a_description(self) -> None:
        self.assertFlags(GOOD.replace("| Source id | Description | Status |", "| Source id | Requirement | Status |"),
                         "the table has no Description column")
        self.assertFlags(GOOD.replace("| REQ-002 | Approvers see pending orders |", "| REQ-002 |  |"),
                         "REQ-002 has no description")
        self.assertFlags(GOOD.replace("| REQ-002 | Approvers see the orders waiting for them |", "| REQ-002 | REQ-002 |"),
                         "REQ-002 has no description")

    def test_checklist_closes_the_report(self) -> None:
        z = GOOD.index("## Z.")
        self.assertFlags(GOOD[:z], "no appendix Z heading")
        self.assertFlags(GOOD + "\n## B. Loading real data\n\nSteps.\n", "must be the report's last section")

    def test_checklist_matches_section_5(self) -> None:
        self.assertFlags(GOOD.replace("| Yes | Partial |", "| Yes | Yes |"),
                         "REQ-002 tested says Yes but its section-5 row says Partial",
                         "says tested 4 of 5, but its rows count 5 of 5")
        self.assertFlags(GOOD.replace("| Staff can enter orders | Yes |", "| Staff can enter orders | Done |"),
                         "REQ-001 implemented is 'Done'; answer Yes, Partial or No")

    def test_checklist_totals_line(self) -> None:
        self.assertFlags(GOOD.replace("Implemented: 6 of 6.", "Implemented: 5 of 6."),
                         "says implemented 5 of 6, but its rows count 6 of 6")
        self.assertFlags(GOOD.replace("**Implemented: 6 of 6. Tested: 4 of 5.**", ""),
                         "no `Implemented: X of N. Tested: Y of M.` totals line")
        # Only the totals line counts: an earlier "tested: N of M" in the prose is not it.
        self.assertEqual(self.run_check(GOOD.replace("**Implemented: 6 of 6.", "Implemented but not tested: 1 of 6.\n\n"
                                                     "**Implemented: 6 of 6.")), [])

    def test_a_split_application_checks_the_overview_and_domain_specs(self) -> None:
        # The overview's section 5 holds the identified requirements, Requirements to confirm the rest.
        overview = self.dir / "Northwind-Business-Spec.md"
        identified = BUSINESS_SPEC.replace(
            "| PMODEL-ORD100-0001 | If Order.Total > Customer.Limit | ORD100.pmodel:12 |\n", "")
        overview.write_text(identified + "\n### Requirements to confirm\n\n| ID | Domains | Requirement |\n"
                            "|---|---|---|\n| PMODEL-ORD100-0001 | - | If Order.Total > Customer.Limit |\n\n"
                            "## 10. Glossary\n\n"
                            "| ID | Term |\n|---|---|\n| GLOSS-001 | Order |\n", encoding="utf-8")
        domain = self.dir / "domains" / "001-orders" / "Northwind-Orders-Business-Spec.md"
        domain.parent.mkdir(parents=True)
        domain.write_text(BUSINESS_SPEC, encoding="utf-8")
        specs = [overview, domain]
        self.assertEqual(self.run_check(with_rule(GOOD, "PMODEL-ORD100-0001"), business_specs=specs), [])
        problems = self.run_check(GOOD, business_specs=[overview])
        self.assertTrue(any("no section 5 row: PMODEL-ORD100-0001" in p for p in problems), problems)
        self.assertFalse(any("GLOSS-001" in p for p in problems), problems)
        # An overview whose every requirement waits to be confirmed has no section-5 table and still counts.
        overview.write_text("# Northwind\n\n## 9. Open questions\n\n### Requirements to confirm\n\n"
                            "| ID | Domains | Requirement |\n|---|---|---|\n| PMODEL-ORD100-0001 | - | Limit |\n",
                            encoding="utf-8")
        self.assertEqual(self.run_check(with_rule(GOOD, "PMODEL-ORD100-0001"), business_specs=[overview]), [])

    def test_a_requirements_to_confirm_only_overview_needs_every_id(self) -> None:
        # The extractor's real overview shape: no section 5, one `### Requirements to confirm` table.
        overview = self.dir / "Northwind-Business-Spec.md"
        overview.write_text("# Northwind\n\n## 9. Open questions\n\n### Requirements to confirm\n\n"
                            "| ID | Domains | Requirement |\n|---|---|---|\n| PMODEL-ORD100-0001 | - | Limit |\n"
                            "| PMODEL-ORD100-0002 | - | Credit hold |\n", encoding="utf-8")
        both = with_rule(with_rule(GOOD, "PMODEL-ORD100-0001"), "PMODEL-ORD100-0002").replace(
            "Implemented: 7 of 7. Tested: 5 of 6.", "Implemented: 8 of 8. Tested: 6 of 7.")
        self.assertEqual(self.run_check(both, business_specs=[overview]), [])
        problems = self.run_check(with_rule(GOOD, "PMODEL-ORD100-0001"), business_specs=[overview])
        self.assertTrue(any("no section 5 row: PMODEL-ORD100-0002" in p for p in problems), problems)

    def test_a_numbered_or_bold_requirements_to_confirm_heading_still_counts(self) -> None:
        for heading in ("### 9.1 Requirements to confirm", "### **Requirements to confirm**",
                        "### `Requirements to confirm`"):
            with self.subTest(heading=heading):
                overview = self.dir / "Northwind-Business-Spec.md"
                overview.write_text("# Northwind\n\n## 9. Open questions\n\n" + heading + "\n\n"
                                    "| ID | Domains | Requirement |\n|---|---|---|\n"
                                    "| PMODEL-ORD100-0001 | - | Limit |\n", encoding="utf-8")
                self.assertEqual(self.run_check(with_rule(GOOD, "PMODEL-ORD100-0001"),
                                                business_specs=[overview]), [])

    def test_an_overview_older_than_its_tables_is_skipped_beside_domain_specs(self) -> None:
        # Before the extractor numbered requirements in the overview, it had no ID table; the domain specs carry every id.
        overview = self.dir / "Northwind-Business-Spec.md"
        overview.write_text("# Northwind\n\n## 1. Summary\n\nThree domains.\n", encoding="utf-8")
        domain = self.dir / "domains" / "001-orders" / "Northwind-Orders-Business-Spec.md"
        domain.parent.mkdir(parents=True)
        domain.write_text(BUSINESS_SPEC, encoding="utf-8")
        path = self.dir / "report.md"
        path.write_text(with_rule(GOOD, "PMODEL-ORD100-0001"), encoding="utf-8")
        problems, summary = check_report_ids.check(self.requirements, path, (), [overview, domain])
        self.assertEqual(problems, [])
        self.assertIn("skipped Northwind-Business-Spec.md: an overview from before", summary)
        # Alone, it still fails, and the domains/ folder beside it is the next step.
        problems = self.run_check(GOOD, business_specs=[overview])
        self.assertIn("numbers no requirements", problems[0])
        self.assertIn("pass each domains/*/ Business Spec", problems[0])
        # A flat app has no domains/ folder, so it is not sent off to look for one.
        shutil.rmtree(str(self.dir / "domains"))
        problems = self.run_check(GOOD, business_specs=[overview])
        self.assertIn("numbers no requirements", problems[0])
        self.assertNotIn("domains", problems[0])

    def test_an_older_overview_with_another_id_table_is_still_skipped(self) -> None:
        # A glossary or open-questions table headed ID is not a requirements table, so it can't un-skip the overview.
        overview = self.dir / "Northwind-Business-Spec.md"
        overview.write_text("# Northwind\n\n## 1. Summary\n\nThree domains.\n\n## 10. Glossary\n\n"
                            "| ID | Term |\n|---|---|\n| GLOSS-001 | Order |\n", encoding="utf-8")
        domain = self.dir / "domains" / "001-orders" / "Northwind-Orders-Business-Spec.md"
        domain.parent.mkdir(parents=True)
        domain.write_text(BUSINESS_SPEC, encoding="utf-8")
        path = self.dir / "report.md"
        path.write_text(with_rule(GOOD, "PMODEL-ORD100-0001"), encoding="utf-8")
        problems, summary = check_report_ids.check(self.requirements, path, (), [overview, domain])
        self.assertEqual(problems, [])
        self.assertIn("skipped Northwind-Business-Spec.md", summary)

    def test_an_older_overview_with_a_glossary_passed_alone_is_sent_to_its_domain_specs(self) -> None:
        # Its glossary heading is right, so "fix the heading" would send the author the wrong way.
        overview = self.dir / "Northwind-Business-Spec.md"
        overview.write_text("# Northwind\n\n## 10. Glossary\n\n| ID | Term |\n|---|---|\n| GLOSS-001 | Order |\n",
                            encoding="utf-8")
        (self.dir / "domains" / "001-orders").mkdir(parents=True)
        message = self.run_check(GOOD, business_specs=[overview])[0]
        self.assertIn("numbers no requirements; pass each domains/*/ Business Spec", message)
        self.assertNotIn("fix the heading", message)

    def test_a_header_only_requirements_table_numbers_zero_ids(self) -> None:
        # Nothing left to confirm is a current overview, not a drifted heading and not an older overview.
        domain = self.dir / "domains" / "001-orders" / "Northwind-Orders-Business-Spec.md"
        domain.parent.mkdir(parents=True)
        domain.write_text(BUSINESS_SPEC, encoding="utf-8")
        overview = self.dir / "Northwind-Business-Spec.md"
        for header in ("| ID | Domains | Requirement |\n|---|---|---|\n", "| ID | Requirement |\n|---|---|\n"):
            with self.subTest(header=header):
                overview.write_text("# Northwind\n\n## 9. Open questions\n\n### Requirements to confirm\n\n" + header,
                                    encoding="utf-8")
                path = self.dir / "report.md"
                path.write_text(with_rule(GOOD, "PMODEL-ORD100-0001"), encoding="utf-8")
                problems, summary = check_report_ids.check(self.requirements, path, (), [overview, domain])
                self.assertEqual(problems, [])
                self.assertNotIn("skipped", summary)
                self.assertEqual(check_report_ids.business_spec_ids(overview, self.requirements), [])

    def test_an_overview_whose_id_table_heading_drifted_is_not_skipped(self) -> None:
        # An ID table under an unrecognised heading means a current overview, so its ids can't drop silently.
        overview = self.dir / "Northwind-Business-Spec.md"
        overview.write_text("# Northwind\n\n### Requirements awaiting confirmation\n\n"
                            "| ID | Domains | Requirement |\n|---|---|---|\n"
                            "| PMODEL-ORD100-0002 | - | Credit hold |\n", encoding="utf-8")
        domain = self.dir / "domains" / "001-orders" / "Northwind-Orders-Business-Spec.md"
        domain.parent.mkdir(parents=True)
        domain.write_text(BUSINESS_SPEC, encoding="utf-8")
        problems = self.run_check(with_rule(GOOD, "PMODEL-ORD100-0001"), business_specs=[overview, domain])
        self.assertTrue(any("fix the heading" in p for p in problems), problems)
        self.assertFalse(any("pass only the domain specs" in p for p in problems), problems)

    def test_a_to_confirm_table_whose_heading_lost_the_word_requirement_is_not_skipped(self) -> None:
        # Its Domains column still marks the extractor's to-confirm table, so its ids can't drop silently.
        overview = self.dir / "Northwind-Business-Spec.md"
        overview.write_text("# Northwind\n\n### To confirm\n\n"
                            "| ID | Domains | Requirement |\n|---|---|---|\n"
                            "| PMODEL-ORD100-0002 | - | Credit hold |\n", encoding="utf-8")
        domain = self.dir / "domains" / "001-orders" / "Northwind-Orders-Business-Spec.md"
        domain.parent.mkdir(parents=True)
        domain.write_text(BUSINESS_SPEC, encoding="utf-8")
        problems = self.run_check(with_rule(GOOD, "PMODEL-ORD100-0001"), business_specs=[overview, domain])
        self.assertTrue(any("fix the heading" in p for p in problems), problems)

    def test_a_flat_or_domain_spec_is_not_told_to_pass_domain_specs(self) -> None:
        # Neither file is a split overview, so the older-overview advice does not apply.
        flat = self.dir / "Northwind-Business-Spec.md"
        flat.write_text("# Northwind\n\n## 1. Summary\n\nNo tables.\n", encoding="utf-8")
        message = self.run_check(GOOD, business_specs=[flat])[0]
        self.assertIn("numbers no requirements", message)
        self.assertNotIn("pass only the domain specs", message)
        domain = self.dir / "domains" / "001-orders" / "Northwind-Orders-Business-Spec.md"
        domain.parent.mkdir(parents=True)
        domain.write_text("# Orders\n\n## 1. Summary\n\nNo tables.\n", encoding="utf-8")
        message = self.run_check(GOOD, business_specs=[domain])[0]
        self.assertIn("numbers no requirements", message)
        self.assertNotIn("pass only the domain specs", message)
        domain.write_text(BUSINESS_SPEC.replace("## 5. Requirements list", "## 4. Rules"), encoding="utf-8")
        message = self.run_check(GOOD, business_specs=[domain])[0]
        self.assertIn("fix the heading", message)
        self.assertNotIn("pass only the domain specs", message)

    def test_nothing_asks_for_the_application_wide_business_spec(self) -> None:
        # The extractor stopped publishing it, so a check or prompt that names it can never pass.
        spec = self.dir / "Northwind-Business-Spec.md"
        spec.write_text("# Northwind\n\n## Overview\n", encoding="utf-8")
        self.assertNotIn("application-wide", self.run_check(GOOD, business_specs=[spec])[0])
        root = _SCRIPT.parents[3]
        named = [str(p.relative_to(root)) for top in ("agents", "app", "commands", "skills")
                 for p in (root / top).rglob("*")
                 if p.is_file() and "Business-Spec-application-wide" in p.read_text(encoding="utf-8", errors="ignore")]
        self.assertEqual(named, [])



def linked(report: str) -> str:
    """GOOD with each spec row's section-5 Evidence cell citing its Test Evidence Pack matrix row."""
    for rid in SPEC_IDS:
        report = re.sub(r"(?m)^(\| REQ-[0-9]{{5}} \| [^|]* \| (?:`|\*\*)?{}(?:`|\*\*)? \|.*\| )([^|]*) \|$".format(
                            re.escape(rid)),
                        lambda m: "{}{} · [matrix](evidence/traceability-matrix.html#req-{}) |".format(
                            m.group(1), m.group(2), rid), report, count=1)
    return report


MATRIX = {"BR-418": "Pass", "RULE-012": "Pass", "REQ-001": "Pass", "REQ-002": "Pass (partial)", "NFR-03": "Blocked"}


class MatrixModeTest(unittest.TestCase):
    """--matrix: the report's section 5 links and agrees with the Test Evidence Pack's run."""

    def setUp(self) -> None:
        self.dir = Path(tempfile.mkdtemp())
        self.requirements = self.dir / "requirements.json"
        rows = [{"id": i, "tier": "functional", "text": i, "source_slug": "06"} for i in SPEC_IDS]
        self.requirements.write_text(json.dumps({"requirements": rows}), encoding="utf-8")

    def run_check(self, report: str, verdicts=None, **extra):
        summary = {"subset": [], "requirements": [{"id": i, "verdict": v} for i, v in (verdicts or MATRIX).items()]}
        summary.update(extra)
        matrix = self.dir / "summary.json"
        matrix.write_text(json.dumps(summary), encoding="utf-8")
        path = self.dir / "report.md"
        path.write_text(report, encoding="utf-8")
        return check_report_ids.check(self.requirements, path, matrix=matrix)[0]

    def assertFlags(self, problems, needle) -> None:
        self.assertTrue(any(needle in p for p in problems), "{!r} not in {}".format(needle, problems))

    def test_a_linked_report_that_agrees_with_the_run_passes(self) -> None:
        self.assertEqual(self.run_check(linked(GOOD)), [])

    def test_a_row_without_its_matrix_link_fails(self) -> None:
        self.assertFlags(self.run_check(GOOD), "BR-418 doesn't link its evidence")

    def test_a_pass_the_run_contradicts_fails(self) -> None:
        self.assertFlags(self.run_check(linked(GOOD), dict(MATRIX, **{"REQ-001": "Fail"})),
                         "REQ-001 is PASS here, but the Test Evidence Pack's run says Fail")

    def test_a_fail_the_run_passed_fails(self) -> None:
        report = linked(GOOD).replace("| Enter orders | Implemented, tested | PASS |", "| Enter orders | Partial | FAIL |")
        report = report.replace("| REQ-001 | Staff can enter orders | Yes | Yes |", "| REQ-001 | Staff can enter orders | Partial | No |")
        report = report.replace("Implemented: 6 of 6. Tested: 4 of 5.", "Implemented: 5 of 6. Tested: 3 of 5.")
        self.assertFlags(self.run_check(report), "REQ-001 is FAIL here, but the Test Evidence Pack's run says Pass")

    def test_the_matrix_must_list_every_spec_id_once_and_nothing_else(self) -> None:
        verdicts = {k: v for k, v in MATRIX.items() if k != "NFR-03"}
        verdicts["REQ-777"] = "Pass"
        problems = self.run_check(linked(GOOD), verdicts)
        self.assertFlags(problems, "1 of 5 spec ids have no matrix row: NFR-03")
        self.assertFlags(problems, "a row for REQ-777, which is not in the spec")

    def test_a_subset_run_is_refused(self) -> None:
        self.assertFlags(self.run_check(linked(GOOD), subset=["REQ-001"]), "is a subset run (REQ-001)")

    def test_a_pass_on_a_partial_run_fails(self) -> None:
        self.assertFlags(self.run_check(linked(GOOD), dict(MATRIX, **{"REQ-001": "Pass (partial)"})),
                         "REQ-001 is PASS here, but the Test Evidence Pack's run says Pass (partial)")

    def test_a_folded_id_counts_for_its_entry(self) -> None:
        rows = [{"id": i, "tier": "functional", "text": i, "source_slug": "06"} for i in SPEC_IDS]
        rows[2]["merged"] = ["REQ-009"]
        self.requirements.write_text(json.dumps({"requirements": rows}), encoding="utf-8")
        self.assertEqual(self.run_check(linked(GOOD)), [])
        problems = self.run_check(linked(GOOD), dict(MATRIX, **{"REQ-009": "Pass"}))
        self.assertFlags(problems, "the matrix has two rows for REQ-001")


class MatrixCheckTest(unittest.TestCase):
    """matrix_check on its own, for inputs a whole report makes awkward to build."""

    def check(self, cells, expected, packed, verdicts):
        path = Path(tempfile.mkdtemp()) / "summary.json"
        path.write_text(json.dumps({"requirements": [{"id": i, "verdict": v} for i, v in verdicts.items()]}),
                        encoding="utf-8")
        row = check_report_ids.Row(7, [cells[0]], False, 1, cells)
        headers = {1: ["spec id", "description", "status", "tested", "evidence"]}
        return check_report_ids.matrix_check(path, expected, packed, {}, {cells[0]: row}, headers, "report.md")

    def test_a_link_to_a_longer_id_is_not_a_link(self) -> None:
        cells = ["RULE-1", "Rule one", "Implemented, tested", "PASS", "[m](traceability-matrix.html#req-RULE-12)"]
        problems = self.check(cells, ["RULE-1", "RULE-12"], ["RULE-1", "RULE-12"], {"RULE-1": "Pass", "RULE-12": "Pass"})
        self.assertTrue(any("RULE-1 doesn't link its evidence" in p for p in problems), problems)
        cells[4] = "[m](traceability-matrix.html#req-RULE-1)"
        self.assertEqual(self.check(cells, ["RULE-1", "RULE-12"], ["RULE-1", "RULE-12"],
                                    {"RULE-1": "Pass", "RULE-12": "Pass"}), [])

    def test_an_id_only_the_business_spec_numbers_needs_no_matrix_row(self) -> None:
        cells = ["REQ-001", "Enter orders", "Implemented, tested", "PASS", "[m](traceability-matrix.html#req-REQ-001)"]
        problems = self.check(cells, ["REQ-001", "PMODEL-ORD100-0001"], ["REQ-001"], {"REQ-001": "Pass"})
        self.assertEqual(problems, [])


# The pack's test ids: one per test, cited beside the requirements they prove.
PROVEN_BY = {"BR-418": ["TEST-002", "TEST-003"], "RULE-012": ["TEST-003"], "REQ-001": ["TEST-001"],
             "REQ-002": ["TEST-004"], "NFR-03": []}


def cited(report: str, proven_by=None) -> str:
    """linked(GOOD) with each section-5 row's evidence cell naming the test ids that prove it."""
    for rid, tids in (proven_by or PROVEN_BY).items():
        if tids:
            report = report.replace("[matrix](evidence/traceability-matrix.html#req-{})".format(rid),
                                    "[matrix](evidence/traceability-matrix.html#req-{}) {}".format(rid, ", ".join(tids)))
    return report


class TestIdTest(unittest.TestCase):
    """--matrix: the report names each requirement's tests by the pack's test ids."""

    setUp = MatrixModeTest.setUp
    assertFlags = MatrixModeTest.assertFlags

    def run_check(self, report: str, verdicts=None, proven_by=None, other=None, **extra):
        rows = [{"id": i, "verdict": v, "tests": [{"id": t, "title": "test " + t} for t in (proven_by or PROVEN_BY)[i]]}
                for i, v in (verdicts or MATRIX).items()]
        summary = {"subset": [], "requirements": rows,
                   "other": other if other is not None else [{"id": "TEST-009", "title": "lists"}]}
        summary.update(extra)
        matrix = self.dir / "summary.json"
        matrix.write_text(json.dumps(summary), encoding="utf-8")
        path = self.dir / "report.md"
        path.write_text(report, encoding="utf-8")
        return check_report_ids.check(self.requirements, path, matrix=matrix)[0]

    def test_a_linked_report_that_agrees_with_the_run_passes(self) -> None:
        self.assertEqual(self.run_check(cited(linked(GOOD))), [])

    def test_a_covered_requirement_that_cites_no_test_id_fails(self) -> None:
        problems = self.run_check(linked(GOOD))
        self.assertFlags(problems, "REQ-001 doesn't cite TEST-001, the test the Test Evidence Pack's run proves it with")
        self.assertFlags(problems, "BR-418 doesn't cite TEST-002, TEST-003, the tests")
        self.assertFalse(any("NFR-03 doesn't cite" in p for p in problems), problems)

    def test_a_test_id_the_run_does_not_have_fails(self) -> None:
        report = cited(linked(GOOD)).replace("#req-REQ-002) TEST-004", "#req-REQ-002) TEST-004, TEST-099")
        self.assertFlags(self.run_check(report), "cites test TEST-099, which isn't in the Test Evidence Pack's run")
        prose = cited(linked(GOOD)).replace("RULE-012 is Changed.", "RULE-012 is Changed (TEST-777).")
        self.assertFlags(self.run_check(prose), "report.md:5: cites test TEST-777")

    def test_a_test_id_cited_for_a_requirement_it_does_not_prove_fails(self) -> None:
        report = cited(linked(GOOD)).replace("#req-REQ-001) TEST-001", "#req-REQ-001) TEST-001, TEST-004")
        self.assertFlags(self.run_check(report), "cites TEST-004 for REQ-001, but the run doesn't tag TEST-004 with REQ-001")

    def test_a_folded_rows_tests_are_cited_under_its_parent(self) -> None:
        # REQ-009 is folded into REQ-001, and the pack's row for it carries TEST-001: REQ-001's row must cite it.
        rows = [{"id": i, "tier": "functional", "text": i, "source_slug": "06"} for i in SPEC_IDS]
        next(r for r in rows if r["id"] == "REQ-001")["merged"] = ["REQ-009"]
        self.requirements.write_text(json.dumps({"requirements": rows}), encoding="utf-8")
        verdicts = {("REQ-009" if i == "REQ-001" else i): v for i, v in MATRIX.items()}
        proven_by = {("REQ-009" if i == "REQ-001" else i): t for i, t in PROVEN_BY.items()}
        self.assertEqual(self.run_check(cited(linked(GOOD)), verdicts, proven_by), [])
        uncited = cited(linked(GOOD)).replace("#req-REQ-001) TEST-001", "#req-REQ-001)")
        self.assertFlags(self.run_check(uncited, verdicts, proven_by), "REQ-001 doesn't cite TEST-001")
        wrong = cited(linked(GOOD)).replace("#req-REQ-001) TEST-001", "#req-REQ-001) TEST-001, TEST-004")
        self.assertFlags(self.run_check(wrong, verdicts, proven_by),
                         "cites TEST-004 for REQ-001, but the run doesn't tag TEST-004 with REQ-001")

    def test_a_respelled_test_id_fails(self) -> None:
        report = cited(linked(GOOD)).replace("#req-REQ-001) TEST-001", "#req-REQ-001) TEST-01")
        problems = self.run_check(report)
        self.assertFlags(problems, "respells test id TEST-001 as TEST-01")
        self.assertFlags(problems, "REQ-001 doesn't cite TEST-001")

    def test_a_run_whose_tests_have_no_test_id_fails(self) -> None:
        problems = self.run_check(cited(linked(GOOD)), other=[{"title": "lists"}])
        # TEST-003 sits under BR-418 and RULE-012, and is one test: 5 in the run, not 6.
        self.assertFlags(problems, "1 of 5 tests in the run have no test id (`lists`)")

    def test_a_test_id_only_an_untagged_check_has_may_be_cited_in_prose(self) -> None:
        report = cited(linked(GOOD)).replace("RULE-012 is Changed.", "RULE-012 is Changed; TEST-009 lists orders.")
        self.assertEqual(self.run_check(report), [])

    def test_a_suffixed_test_id_is_another_token_and_a_long_one_is_read(self) -> None:
        # TEST-001-v2 is not TEST-001: REQ-001 still lacks its citation.
        report = cited(linked(GOOD)).replace("#req-REQ-001) TEST-001", "#req-REQ-001) TEST-001-v2")
        self.assertFlags(self.run_check(report), "REQ-001 doesn't cite TEST-001")
        # A seven-digit id is a test id like any other.
        proven = dict(PROVEN_BY, **{"REQ-001": ["TEST-1000000"]})
        self.assertEqual(self.run_check(cited(linked(GOOD), proven), proven_by=proven), [])

    def test_an_escaped_test_id_is_checked_as_it_renders(self) -> None:
        report = cited(linked(GOOD)).replace("#req-REQ-002) TEST-004", "#req-REQ-002) TEST-004, TEST\\-099")
        self.assertFlags(self.run_check(report), "cites test TEST-099, which isn't in the Test Evidence Pack's run")

    def test_a_file_or_run_name_with_a_number_is_not_a_test_id(self) -> None:
        report = cited(linked(GOOD)).replace("RULE-012 is Changed.",
                                             "RULE-012 is Changed (see test-1-failed.png and run test-1-failed).")
        self.assertEqual(self.run_check(report), [])


if __name__ == "__main__":
    unittest.main()
