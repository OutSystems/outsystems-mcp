#!/usr/bin/env python3
"""End-to-end tests for build.py: deletion-impact records in, HTML out.

Runnable two ways:
    python3 test_build_impact.py      # standalone, no deps
    pytest scripts/tests/             # discovered as test_* functions

Every test runs build.py as a subprocess (fresh mode) and reads the data
bundle back out of the rendered HTML, so what is asserted is what the page
renders.

Fixtures (tests/fixtures/) follow the remote MCP server's response shapes;
names, keys and hostnames are invented:
    launch-deletion-*.json          deploy_impact {key, delete: true} responses
    status-deletion-*.json          deploy_impact_status {analysis_id, kind}
                                    terminal responses (Inventory Core Library:
                                    1 dependent, WarningsFound; OutSystems UI:
                                    74 dependents, ErrorsFound)
    launch-deletion-testlib.json    a launch whose poll was never made correctly
                                    (the poll used `analysisKey`)
    tool-error-validation.json      that poll's error envelope
    tenant-assets.json, env-list.json  tenant asset list / env_list
Derived in the tests (shapes the server emits): the capped 200-of-N report,
the Failed / Unknown / Finished-without-verdict results and the
`analysis_launch_rejected` launch. Each derivation is next to the test that
uses it.
"""
import copy
import json
import pathlib
import re
import subprocess
import sys
import tempfile

HERE = pathlib.Path(__file__).resolve().parent
BUILD = HERE.parents[2] / "claude" / "skills" / "outsystems-dependency-impact" / "scripts" / "build.py"
FIX = HERE / "fixtures"

LIB_CORE = "a000007e-0000-4000-8000-00000000007e"   # Inventory Core Library
OS_UI = "a00000ba-0000-4000-8000-0000000000ba"       # OutSystems UI
TESTLIB = "a000005a-0000-4000-8000-00000000005a"     # TestLib
AGENT = "a0000065-0000-4000-8000-000000000065"       # an Agent asset
CONN = "a00000fd-0000-4000-8000-0000000000fd"        # an AIModelConnection asset

FORBIDDEN_FOR_UNKNOWN = ("No dependents", "no issues", "NoIssuesFound", "safe")


def fx(name):
    return json.loads((FIX / name).read_text(encoding="utf-8"))


def run_build(records: dict, env_list=True):
    """Write one record per target, run build.py, return (html, bundle)."""
    with tempfile.TemporaryDirectory() as td:
        td = pathlib.Path(td)
        impact = td / "impact"
        impact.mkdir()
        for key, rec in records.items():
            (impact / f"{key}.json").write_text(json.dumps({"targetKey": key, **rec}),
                                                encoding="utf-8")
        out = td / "out.html"
        cmd = [sys.executable, str(BUILD), str(td / "cache"), str(out),
               "--impact-dir", str(impact),
               "--tenant-assets", str(FIX / "tenant-assets.json"),
               "--tenant-id", "tenant-under-test"]
        if env_list:
            cmd += ["--env-list", str(FIX / "env-list.json")]
        proc = subprocess.run(cmd, capture_output=True, text=True)
        assert proc.returncode == 0, proc.stderr
        html = out.read_text(encoding="utf-8")
    m = re.search(r"const IMPACT_DATA = (\{.*?\});\n", html, re.S)
    assert m, "IMPACT_DATA not injected"
    return html, json.loads(m.group(1).replace("<\\/", "</"))


def test_real_deletion_reports_list_the_dependents():
    html, b = run_build({
        LIB_CORE: {"launch": fx("launch-deletion-inventory-core.json"),
                    "result": fx("status-deletion-inventory-core.json")},
        OS_UI: {"launch": fx("launch-deletion-outsystems-ui.json"),
                "result": fx("status-deletion-outsystems-ui.json")},
    })
    core = b["byTarget"][LIB_CORE]
    assert core["state"] == "known"
    assert core["n"] == "Inventory Core Library" and core["kind"] == "LowCodeLibrary"
    assert core["total"] == 1 and core["shown"] == 1
    user = core["users"][0]
    assert user["n"] == "Inventory Inspections" and user["t"] == "MobileApplication"
    assert user["sev"] == "Warning"
    assert user["envs"][0]["en"] == "acme-dev"   # env name resolved
    assert user["envs"][0]["r"] == 4 and user["envs"][0]["c"] == "LibraryDirect"
    assert "Inventory Inspections" in html

    ui = b["byTarget"][OS_UI]
    assert ui["state"] == "known" and ui["reportStatus"] == "ErrorsFound"
    assert ui["total"] == 74 and ui["shown"] == 74 and not ui["truncated"]
    assert ui["summary"] == "74 dependents (ErrorsFound)."
    # worst severity across environments wins, errors sort first
    assert ui["users"][0]["sev"] == "Error"
    assert "Banking Sync Services" in html
    assert b["stats"]["edgeCount"] == 75
    assert b["stats"]["knownCount"] == 2 and b["stats"]["unknownCount"] == 0
    assert b["tenant"]["id"] == "tenant-under-test"


def test_capped_report_says_showing_n_of_m():
    # Derived: the server caps impactedAssets at 200 and reports the real
    # total with truncated: true. Built from the OutSystems UI fixture rows.
    status = fx("status-deletion-outsystems-ui.json")
    rows = status["report"]["impactedAssets"]
    capped = []
    for i in range(200):
        r = copy.deepcopy(rows[i % len(rows)])
        r["assetKey"] = r["applicationKey"] = f"{i:08d}-0000-0000-0000-000000000000"
        capped.append(r)
    status["report"].update(impactedAssets=capped, displayed=200, total=312,
                            truncated=True)
    html, b = run_build({OS_UI: {"launch": fx("launch-deletion-outsystems-ui.json"),
                                 "result": status}})
    ui = b["byTarget"][OS_UI]
    assert ui["total"] == 312 and ui["shown"] == 200 and ui["truncated"]
    assert ui["summary"].startswith("Showing 200 of 312 dependents")
    assert "Showing 200 of 312" in html
    assert b["stats"]["edgeCount"] == 312      # the real blast radius, not 200
    assert "showing ${t.shown} of ${t.total}" in html   # table header wording


def test_harness_cut_response_is_partial_not_complete():
    # Codex truncates large MCP results; the skill keeps status/total from the
    # visible tail and flags the record. Rows kept: 3 of 74.
    status = fx("status-deletion-outsystems-ui.json")
    status["report"]["impactedAssets"] = status["report"]["impactedAssets"][:3]
    _, b = run_build({OS_UI: {"launch": fx("launch-deletion-outsystems-ui.json"),
                              "result": status, "harnessTruncated": True}})
    ui = b["byTarget"][OS_UI]
    assert ui["state"] == "known" and ui["truncated"]
    assert ui["summary"].startswith("Showing 3 of 74 dependents")
    assert "harness cut the response" in ui["summary"]


def _assert_unknown(target, reason_fragment):
    assert target["state"] == "unknown", target
    assert target["users"] == [] and target["total"] == 0
    assert target["summary"].startswith("Impact unknown"), target["summary"]
    assert reason_fragment in target["summary"], target["summary"]
    assert "not the same as 'no dependents'" in target["summary"]
    for word in FORBIDDEN_FOR_UNKNOWN:
        assert word not in target["summary"], (word, target["summary"])


def test_finished_without_verdict_is_impact_unknown():
    # Derived: Finished but impactKnown false (the server withholds the report
    # when the verdict is unrecognised or self-contradictory).
    status = fx("status-deletion-inventory-core.json")
    status["impactKnown"] = False
    status.pop("report")
    html, b = run_build({LIB_CORE: {"launch": fx("launch-deletion-inventory-core.json"),
                                     "result": status}})
    _assert_unknown(b["byTarget"][LIB_CORE], "finished without a verdict")
    assert b["stats"]["unknownCount"] == 1 and b["stats"]["edgeCount"] == 0
    assert "Impact unknown" in html


def test_impact_known_false_with_a_stray_report_is_still_unknown():
    # Belt and braces: never trust a report the server did not vouch for.
    status = fx("status-deletion-inventory-core.json")
    status["impactKnown"] = False
    _, b = run_build({LIB_CORE: {"launch": fx("launch-deletion-inventory-core.json"),
                                  "result": status}})
    _assert_unknown(b["byTarget"][LIB_CORE], "finished without a verdict")


def test_failed_analysis_is_impact_unknown_with_reason():
    status = {"analysisKey": fx("launch-deletion-inventory-core.json")["analysisKey"],
              "assetKey": LIB_CORE, "impactKnown": False, "processStatus": "Failed",
              "error": {"message": "Dependency graph unavailable"}, "type": "Deletion"}
    _, b = run_build({LIB_CORE: {"launch": fx("launch-deletion-inventory-core.json"),
                                  "result": status}})
    _assert_unknown(b["byTarget"][LIB_CORE], "failed (Dependency graph unavailable)")


def test_unknown_process_status_is_impact_unknown():
    status = {"analysisKey": fx("launch-deletion-inventory-core.json")["analysisKey"],
              "impactKnown": False, "processStatus": "Unknown", "type": "Deletion"}
    _, b = run_build({LIB_CORE: {"launch": fx("launch-deletion-inventory-core.json"),
                                  "result": status, "gaveUp": "unknown-status"}})
    _assert_unknown(b["byTarget"][LIB_CORE], "processStatus: Unknown")


def test_still_in_progress_is_impact_unknown():
    status = {"analysisKey": fx("launch-deletion-inventory-core.json")["analysisKey"],
              "impactKnown": False, "processStatus": "InProgress", "type": "Deletion"}
    _, b = run_build({LIB_CORE: {"launch": fx("launch-deletion-inventory-core.json"),
                                  "result": status, "gaveUp": "still-in-progress"}})
    _assert_unknown(b["byTarget"][LIB_CORE], "still in progress")


def test_launched_but_never_polled_is_impact_unknown():
    # The TestLib analysis was launched, but the poll used the
    # wrong parameter name and errored, so no result exists.
    _, b = run_build({TESTLIB: {"launch": fx("launch-deletion-testlib.json")}})
    _assert_unknown(b["byTarget"][TESTLIB], "never polled")


def test_errored_poll_saved_as_result_is_impact_unknown():
    # That poll's error envelope, saved in place of a result.
    _, b = run_build({TESTLIB: {"launch": fx("launch-deletion-testlib.json"),
                                "result": fx("tool-error-validation.json")}})
    _assert_unknown(b["byTarget"][TESTLIB], "Impact unknown")


def _rejected(message):
    # Derived from the tool-error envelope, with the code and wording
    # deploy_impact uses for a refused launch (server behaviour).
    err = fx("tool-error-validation.json")
    err["category"] = err["data"]["category"] = "UpstreamError"
    err["data"]["code"] = "analysis_launch_rejected"
    err["data"]["upstream_status"] = 400
    err["error"] = f"UpstreamError: deletion analysis rejected by the Dependency Management API (400 Bad Request): {message}"
    return err


def test_refused_launch_says_not_available_for_the_type():
    html, b = run_build({
        AGENT: {"launch": _rejected("OS-DEP-40000 asset type not supported")},
        CONN: {"skipped": "type-unsupported",
               "probeError": _rejected("OS-DEP-40000 asset type not supported")},
    })
    agent = b["byTarget"][AGENT]
    assert agent["state"] == "refused" and agent["kind"] == "Agent"
    assert agent["summary"].startswith("Deletion analysis not available for this asset (Agent)")
    assert "analysis_launch_rejected" in agent["summary"]
    assert "Dependents unknown, not 'no dependents'" in agent["summary"]
    conn = b["byTarget"][CONN]
    assert conn["state"] == "refused" and conn["kind"] == "AIModelConnection"
    assert "not available for this asset type (AIModelConnection)" in conn["summary"]
    for t in (agent, conn):
        assert t["users"] == []
        for word in FORBIDDEN_FOR_UNKNOWN:
            assert word not in t["summary"]
    assert b["stats"]["refusedCount"] == 2 and b["stats"]["unknownCount"] == 2
    assert "Deletion analysis not available" in html


def test_unavailable_launch_is_unknown_and_retryable():
    err = _rejected("")
    err["data"]["code"] = "analysis_launch_unavailable"
    err["error"] = "UpstreamError: deletion analysis could not reach the Dependency Management API (503 Service Unavailable)"
    _, b = run_build({LIB_CORE: {"launch": err}})
    t = b["byTarget"][LIB_CORE]
    _assert_unknown(t, "could not be started (analysis_launch_unavailable")
    assert "Worth retrying later" in t["summary"]


def test_zero_dependents_only_from_a_real_verdict():
    status = fx("status-deletion-inventory-core.json")
    status["report"].update(impactedAssets=[], displayed=0, total=0,
                            status="NoIssuesFound")
    _, b = run_build({LIB_CORE: {"launch": fx("launch-deletion-inventory-core.json"),
                                  "result": status}})
    t = b["byTarget"][LIB_CORE]
    assert t["state"] == "known" and t["total"] == 0
    assert t["summary"].startswith("No dependents: the platform's deletion analysis found none")


def test_cached_rerender_and_script_escaping():
    with tempfile.TemporaryDirectory() as td:
        td = pathlib.Path(td)
        impact = td / "impact"
        impact.mkdir()
        status = fx("status-deletion-inventory-core.json")
        status["report"]["impactedAssets"][0]["name"] = "Evil </script><b>x <!--<script> y"
        (impact / f"{LIB_CORE}.json").write_text(json.dumps({
            "targetKey": LIB_CORE,
            "launch": fx("launch-deletion-inventory-core.json"),
            "result": status}), encoding="utf-8")
        cache = td / "cache"
        first = subprocess.run([sys.executable, str(BUILD), str(cache), str(td / "a.html"),
                                "--impact-dir", str(impact),
                                "--tenant-assets", str(FIX / "tenant-assets.json")],
                               capture_output=True, text=True)
        assert first.returncode == 0, first.stderr
        meta = json.loads((cache / "meta.json").read_text())
        assert meta["target_count"] == 1 and meta["known_count"] == 1
        second = subprocess.run([sys.executable, str(BUILD), str(cache), str(td / "b.html")],
                                capture_output=True, text=True)
        assert second.returncode == 0, second.stderr
        html = (td / "b.html").read_text()
    assert "Evil \\u003c/script>" in html and "Evil </script>" not in html
    # "<!--<script" inside the inline script would put the HTML parser into
    # its double-escaped state and blank the page; no literal "<" survives.
    payload = re.search(r"const IMPACT_DATA = (\{.*?\});\n", html, re.S).group(1)
    assert "<" not in payload
    assert json.loads(payload)["byTarget"][LIB_CORE]["users"][0]["n"].endswith("<!--<script> y")


def test_tenant_architecture_bundle_is_accepted_as_the_asset_list():
    # Branch D reuses outsystems-tenant-architecture's tenant-data.json.
    assets = fx("tenant-assets.json")
    rows = assets if isinstance(assets, list) else [
        {"k": a["assetKey"], "n": a.get("name") or "", "t": a.get("assetType") or "",
         "r": a.get("revision"), "d": (a.get("revisionDateTime") or "")[:10],
         "x": bool(a.get("isExternal", False))} for a in assets["results"]]
    bundle = {"schema": 1, "tenant": {}, "envs": [], "assets": rows,
              "deployments": None, "health": None, "ai": None}
    with tempfile.TemporaryDirectory() as td:
        td = pathlib.Path(td)
        impact = td / "impact"
        impact.mkdir()
        (impact / f"{LIB_CORE}.json").write_text(json.dumps({
            "targetKey": LIB_CORE,
            "launch": fx("launch-deletion-inventory-core.json"),
            "result": fx("status-deletion-inventory-core.json")}), encoding="utf-8")
        (td / "tenant-data.json").write_text(json.dumps(bundle), encoding="utf-8")
        proc = subprocess.run([sys.executable, str(BUILD), str(td / "cache"), str(td / "o.html"),
                               "--impact-dir", str(impact),
                               "--tenant-assets", str(td / "tenant-data.json")],
                              capture_output=True, text=True)
        assert proc.returncode == 0, proc.stderr
        data = json.loads((td / "cache" / "impact-data.json").read_text())
    core = data["byTarget"][LIB_CORE]
    assert core["n"] == "Inventory Core Library" and core["kind"] == "LowCodeLibrary"


def test_result_file_and_paged_tenant_assets():
    """A record may point at the harness's saved output instead of inlining
    it, and the asset list may arrive as several raw app_list pages."""
    with tempfile.TemporaryDirectory() as td:
        td = pathlib.Path(td)
        impact = td / "impact"
        (impact / "raw").mkdir(parents=True)
        (impact / "raw" / "ui.status.json").write_text(
            (FIX / "status-deletion-outsystems-ui.json").read_text(), encoding="utf-8")
        (impact / f"{OS_UI}.json").write_text(json.dumps({
            "targetKey": OS_UI, "launch": fx("launch-deletion-outsystems-ui.json"),
            "resultFile": "raw/ui.status.json"}), encoding="utf-8")
        (impact / f"{LIB_CORE}.json").write_text(json.dumps({
            "targetKey": LIB_CORE, "launch": fx("launch-deletion-inventory-core.json"),
            "resultFile": "raw/missing.json"}), encoding="utf-8")
        compact = {a["k"]: a for a in fx("tenant-assets.json")}
        page1 = {"results": [{"assetKey": OS_UI, "name": compact[OS_UI]["n"],
                              "assetType": "LowCodeLibrary", "revision": 30}],
                 "truncated": True, "next_offset": 1, "total": 2, "displayed": 1}
        page2 = {"results": [{"assetKey": LIB_CORE, "name": "Inventory Core Library",
                              "assetType": "LowCodeLibrary", "revision": 3}],
                 "truncated": False, "total": 2, "displayed": 1}
        (td / "p1.json").write_text(json.dumps(page1))
        (td / "p2.json").write_text(json.dumps(page2))
        out = td / "o.html"
        proc = subprocess.run([sys.executable, str(BUILD), str(td / "c"), str(out),
                               "--impact-dir", str(impact),
                               "--tenant-assets", str(td / "p1.json"),
                               "--tenant-assets", str(td / "p2.json")],
                              capture_output=True, text=True)
        assert proc.returncode == 0, proc.stderr
        b = json.loads((td / "c" / "impact-data.json").read_text())
    assert b["byTarget"][OS_UI]["state"] == "known"
    assert b["byTarget"][OS_UI]["total"] == 74
    assert b["byTarget"][OS_UI]["currentRev"] == 30
    core = b["byTarget"][LIB_CORE]
    assert core["n"] == "Inventory Core Library"          # name from page 2
    _assert_unknown(core, "never polled")             # unreadable file => unknown


def test_fresh_mode_needs_both_inputs():
    with tempfile.TemporaryDirectory() as td:
        proc = subprocess.run([sys.executable, str(BUILD), td, td + "/o.html",
                               "--impact-dir", td], capture_output=True, text=True)
    assert proc.returncode == 2


def _run():
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in fns:
        fn()
        print(f"PASS {fn.__name__}")
    print(f"\n{len(fns)} passed")


def test_an_unwritable_output_path_is_one_clean_line():
    with tempfile.TemporaryDirectory() as td:
        td = pathlib.Path(td)
        impact = td / "impact"
        impact.mkdir()
        (impact / f"{LIB_CORE}.json").write_text(json.dumps({
            "targetKey": LIB_CORE,
            "launch": fx("launch-deletion-inventory-core.json"),
            "result": fx("status-deletion-inventory-core.json")}), encoding="utf-8")
        (td / "out.html").mkdir()                    # a folder where the page should go
        proc = subprocess.run([sys.executable, str(BUILD), str(td / "cache"), str(td / "out.html"),
                               "--impact-dir", str(impact),
                               "--tenant-assets", str(FIX / "tenant-assets.json")],
                              capture_output=True, text=True)
    assert proc.returncode == 1 and "could not write the output file" in proc.stderr, proc.stderr
    assert "Traceback" not in proc.stderr


def test_a_target_without_a_record_is_unknown_not_dropped():
    with tempfile.TemporaryDirectory() as td:
        td = pathlib.Path(td)
        impact = td / "impact"
        impact.mkdir()
        (impact / f"{LIB_CORE}.json").write_text(json.dumps({
            "targetKey": LIB_CORE,
            "launch": fx("launch-deletion-inventory-core.json"),
            "result": fx("status-deletion-inventory-core.json")}), encoding="utf-8")
        targets = td / "targets.json"
        targets.write_text(json.dumps([LIB_CORE, "a0000999-0000-4000-8000-000000000999"]))
        proc = subprocess.run([sys.executable, str(BUILD), str(td / "cache"), str(td / "o.html"),
                               "--impact-dir", str(impact), "--targets", str(targets),
                               "--tenant-assets", str(FIX / "tenant-assets.json")],
                              capture_output=True, text=True)
        assert proc.returncode == 0, proc.stderr
        bundle = json.loads((td / "cache" / "impact-data.json").read_text())
    missing = bundle["byTarget"]["a0000999-0000-4000-8000-000000000999"]
    assert missing["state"] == "unknown" and "no analysis record" in missing["summary"]
    s = bundle["stats"]
    assert s["targetCount"] == 2 and s["unknownCount"] == 1 and s["missingCount"] == 1
    assert "1 with no saved record" in proc.stdout


def test_the_report_is_dated_by_its_oldest_record_not_the_build():
    import os, time as _time
    with tempfile.TemporaryDirectory() as td:
        td = pathlib.Path(td)
        impact = td / "impact"
        impact.mkdir()
        rec = impact / f"{LIB_CORE}.json"
        rec.write_text(json.dumps({
            "targetKey": LIB_CORE,
            "launch": fx("launch-deletion-inventory-core.json"),
            "result": fx("status-deletion-inventory-core.json")}), encoding="utf-8")
        old = int(_time.time()) - 20 * 3600              # reused from the 24-hour cache
        os.utime(rec, (old, old))
        proc = subprocess.run([sys.executable, str(BUILD), str(td / "cache"), str(td / "o.html"),
                               "--impact-dir", str(impact),
                               "--tenant-assets", str(FIX / "tenant-assets.json")],
                              capture_output=True, text=True)
        assert proc.returncode == 0, proc.stderr
        bundle = json.loads((td / "cache" / "impact-data.json").read_text())
    assert bundle["tenant"]["scannedAt"] == old


def _dep_build(td, records, assets_paths):
    impact = td / "impact"
    impact.mkdir(exist_ok=True)
    for key, rec in records.items():
        (impact / f"{key}.json").write_text(json.dumps({"targetKey": key, **rec}), encoding="utf-8")
    cmd = [sys.executable, str(BUILD), str(td / "cache"), str(td / "o.html"), "--impact-dir", str(impact)]
    for p in assets_paths:
        cmd += ["--tenant-assets", str(p)]
    return subprocess.run(cmd, capture_output=True, text=True)


def test_a_truncated_asset_page_without_its_next_page_is_incomplete():
    rows = [{"assetKey": a["k"], "name": a["n"], "assetType": a["t"], "revision": a["r"]}
            for a in fx("tenant-assets.json")]      # as app_list returns them
    first = {"results": rows[:2], "total": len(rows), "displayed": 2, "truncated": True, "next_offset": 2}
    rest = {"results": rows[2:], "total": len(rows), "displayed": len(rows) - 2, "truncated": False}
    rec = {LIB_CORE: {"launch": fx("launch-deletion-inventory-core.json"),
                      "result": fx("status-deletion-inventory-core.json")}}
    with tempfile.TemporaryDirectory() as td:
        td = pathlib.Path(td)
        (td / "p1.json").write_text(json.dumps(first)); (td / "p2.json").write_text(json.dumps(rest))
        cut = _dep_build(td, rec, [td / "p1.json"])
        assert cut.returncode == 3 and "INCOMPLETE" in cut.stderr and "offset: 2" in cut.stderr, cut.stderr
        assert not (td / "cache" / "impact-data.json").exists()
        whole = _dep_build(td, rec, [td / "p1.json", td / "p2.json"])
        assert whole.returncode == 0, whole.stderr
        # Copilot's case: a truncated search plus a DIFFERENT complete search
        # that happens to report the same total is still incomplete.
        a, b, c = rows[0], rows[1], rows[2]
        cut_search = {"results": [a], "total": 2, "displayed": 1, "truncated": True, "next_offset": 1}
        other = {"results": [b, c], "total": 2, "displayed": 2, "truncated": False}
        (td / "s1.json").write_text(json.dumps(cut_search)); (td / "s2.json").write_text(json.dumps(other))
        mixed = _dep_build(td, rec, [td / "s1.json", td / "s2.json"])
        assert mixed.returncode == 3 and "starting at s1.json" in mixed.stderr, mixed.stderr
        # Two complete searches, any totals, pass.
        (td / "s3.json").write_text(json.dumps(dict(other, results=[a])))
        assert _dep_build(td, rec, [td / "s3.json", td / "s2.json"]).returncode == 0


def test_a_status_saved_for_another_analysis_is_unknown():
    status = fx("status-deletion-inventory-core.json")
    other = dict(status, analysisKey="a0000777-0000-4000-8000-000000000777")
    wrong_asset = dict(status, assetKey=OS_UI)
    for result, word in ((other, "analysis a0000777"), (wrong_asset, f"asset {OS_UI}")):
        html, bundle = run_build({LIB_CORE: {"launch": fx("launch-deletion-inventory-core.json"),
                                             "result": result}})
        t = bundle["byTarget"][LIB_CORE]
        assert t["state"] == "unknown" and word in t["summary"] and t["users"] == []


if __name__ == "__main__":
    _run()


def test_cut_report_without_total_is_never_no_dependents():
    status = fx("status-deletion-inventory-core.json")
    rep = status["report"]
    rep.pop("total", None)
    rep["impactedAssets"] = []
    _, b = run_build({LIB_CORE: {"launch": fx("launch-deletion-inventory-core.json"),
                                 "result": status, "harnessTruncated": True}})
    t = b["byTarget"][LIB_CORE]
    assert t["state"] == "unknown" and "No dependents" not in t["summary"]

    status = fx("status-deletion-inventory-core.json")
    status["report"].pop("total", None)
    status["report"]["truncated"] = True
    _, b = run_build({LIB_CORE: {"launch": fx("launch-deletion-inventory-core.json"),
                                 "result": status}})
    t = b["byTarget"][LIB_CORE]
    assert t["state"] == "known" and t["truncated"] and t["summary"].startswith("At least 1 dependent")
    # Every counter carries the lower bound, not an exact count.
    assert t["totalKnown"] is False and b["stats"]["edgeCountIsLowerBound"] is True
    html, b2 = run_build({LIB_CORE: {"launch": fx("launch-deletion-inventory-core.json"),
                                     "result": status}})
    assert "S.edgeCountIsLowerBound !== false ? '≥'" in html and "t.totalKnown !== true" in html
    _, exact = run_build({LIB_CORE: {"launch": fx("launch-deletion-inventory-core.json"),
                                     "result": fx("status-deletion-inventory-core.json")}})
    assert exact["byTarget"][LIB_CORE]["totalKnown"] is True
    assert exact["stats"]["edgeCountIsLowerBound"] is False


def test_report_without_total_or_truncation_hint_is_still_a_lower_bound():
    status = fx("status-deletion-inventory-core.json")
    status["report"].pop("total", None)
    status["report"].pop("truncated", None)
    html, b = run_build({LIB_CORE: {"launch": fx("launch-deletion-inventory-core.json"),
                                    "result": status}})
    t = b["byTarget"][LIB_CORE]
    assert t["totalKnown"] is False and t["summary"].startswith("At least 1 dependent ")
    assert b["stats"]["edgeCountIsLowerBound"] is True
    # An older bundle without the certainty fields reads as a floor, not exact.
    assert "t.totalKnown !== true" in html and "S.edgeCountIsLowerBound !== false" in html


def test_saved_content_block_report_and_several_searches(tmp_path):
    status = fx("status-deletion-inventory-core.json")
    impact = tmp_path / "impact"
    (impact / "raw").mkdir(parents=True)
    (impact / "raw" / f"{LIB_CORE}.status.json").write_text(
        json.dumps([{"type": "text", "text": json.dumps(status)}]), encoding="utf-8")
    (impact / f"{LIB_CORE}.json").write_text(json.dumps({
        "targetKey": LIB_CORE, "launch": fx("launch-deletion-inventory-core.json"),
        "resultFile": f"raw/{LIB_CORE}.status.json"}), encoding="utf-8")
    rows = [{"assetKey": a["k"], "name": a["n"], "assetType": a["t"], "revision": a["r"],
             "revisionDateTime": a["d"] + "T00:00:00Z", "isExternal": a["x"]}
            for a in fx("tenant-assets.json")]                 # as app_list returns them
    rows.sort(key=lambda r: r["assetKey"] != LIB_CORE)        # the target in the first search
    # One file per search (repeat --tenant-assets), and a hand-merged raw-row list.
    one, two = tmp_path / "ta-1.json", tmp_path / "ta-2.json"
    one.write_text(json.dumps({"results": rows[:1]}), encoding="utf-8")
    two.write_text(json.dumps({"results": rows[1:]}), encoding="utf-8")
    merged = tmp_path / "merged.json"
    merged.write_text(json.dumps(rows), encoding="utf-8")
    for extra in (["--tenant-assets", str(one), "--tenant-assets", str(two)],
                  ["--tenant-assets", str(merged)]):
        out = tmp_path / "cache"
        proc = subprocess.run([sys.executable, str(BUILD), str(out), str(tmp_path / "o.html"),
                               "--impact-dir", str(impact), *extra], capture_output=True, text=True)
        assert proc.returncode == 0, proc.stderr
        t = json.loads((out / "impact-data.json").read_text())["byTarget"][LIB_CORE]
        assert t["state"] == "known" and t["n"] == "Inventory Core Library"


def test_poll_pacing_follows_each_harness():
    skill = (BUILD.parent.parent / "SKILL.md").read_text(encoding="utf-8")
    assert "in the foreground where it has none (Kiro)" in skill
    assert "--wait <seconds>" in skill                 # the pause runs inside the allowed tools
    assert "never a bare foreground `sleep`" not in skill


def test_targets_list_limits_the_page_to_this_runs_scope(tmp_path):
    impact = tmp_path / "impact"
    impact.mkdir()
    for key in (LIB_CORE, AGENT):
        (impact / f"{key}.json").write_text(json.dumps({
            "targetKey": key, "launch": fx("launch-deletion-inventory-core.json"),
            "result": fx("status-deletion-inventory-core.json")}), encoding="utf-8")
    targets = tmp_path / "targets.json"
    targets.write_text(json.dumps([{"key": LIB_CORE, "name": "Inventory Core Library",
                                    "type": "LowCodeLibrary"}]), encoding="utf-8")
    base = [sys.executable, str(BUILD), str(tmp_path / "cache"), str(tmp_path / "o.html"),
            "--impact-dir", str(impact), "--tenant-assets", str(FIX / "tenant-assets.json")]
    proc = subprocess.run(base + ["--targets", str(targets)], capture_output=True, text=True)
    assert proc.returncode == 0, proc.stderr
    data = json.loads((tmp_path / "cache" / "impact-data.json").read_text())
    assert list(data["byTarget"]) == [LIB_CORE] and data["stats"]["targetCount"] == 1
    assert (impact / f"{AGENT}.json").exists()          # still cached for reuse
    proc = subprocess.run(base, capture_output=True, text=True)
    assert proc.returncode == 0
    assert len(json.loads((tmp_path / "cache" / "impact-data.json").read_text())["byTarget"]) == 2


def test_branch_d_confirmation_names_the_targets():
    skill = (BUILD.parent.parent / "SKILL.md").read_text(encoding="utf-8")
    assert "Name the\ntargets in the same message" in skill
    assert "list them if the user\nwants" not in skill
