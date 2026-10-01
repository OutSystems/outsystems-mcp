#!/usr/bin/env python3
"""Tests for build.py 1.7: asset types, the deployments (env_apps) and health
(app_health) overlays, harness-truncation rejection, auth fields, and an
end-to-end run of the script as a subprocess.

Runnable two ways:
    python3 test_build_overlays.py
    pytest tests/skills/tenant-architecture/

Fixtures (tests/fixtures/, each carries a `_provenance` key). Names, keys
and hostnames are invented; the shapes follow the server's responses.
  - envs-raw.json, apps-page.json, env-apps-dev-old-server.json,
    auth-status.json: env_list, app_list (one row per asset type of a
    515-asset tenant, plus every key the other fixtures reference), env_apps
    in the older server's envelope, and auth_status.
  - env-apps-test-p1/p2.json: env_apps rows split into two pages in the
    envelope of the NEWER server (offset input, numeric next_offset).
  - env-apps-prod.json: constructed from env_apps' output schema to exercise
    drift; keys and names match the other fixtures.
  - health-prod*.json: app_health. health-prod-empty.json is a whole-stage
    168h Production response with 0 rows. health-prod.json holds five
    AppHealthRow rows, one with no `requests` reading.
    health-prod-undetermined.json adds a `noData: undetermined` in the
    server's NoData shape.
"""
import importlib.util
import json
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile

import pytest

_SCRIPTS = pathlib.Path(__file__).resolve().parents[3] / "claude" / "skills" / "outsystems-tenant-architecture" / "scripts"
_SKILL = _SCRIPTS.parent
_spec = importlib.util.spec_from_file_location("tenant_build_overlays", _SCRIPTS / "build.py")
build = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(build)

FIX = pathlib.Path(__file__).resolve().parent / "fixtures"
TEMPLATE = _SKILL / "assets" / "template.html"

TENANT = "a0000093-0000-4000-8000-000000000093"
HOSTNAME = "acme.outsystems.dev"
DEV = "a00000b6-0000-4000-8000-0000000000b6"
TEST = "a000011f-0000-4000-8000-00000000011f"
PROD = "a000003f-0000-4000-8000-00000000003f"

# Every asset type app_list returns (apps-page.json has one row of each).
REAL_TYPES = {
    "AgentDefinition", "KnowledgeBase", "WebApplication", "MobileLibrary",
    "AIModelConnection", "LowCodeLibrary", "ExternalConnection", "ExternalLibrary",
    "Agent", "MobileApplication", "ExtensionLibrary", "Workflow",
    "SearchServiceConnection", "MCPConnection", "A2AConnection", "WidgetLibrary",
}

SRI = "sha384-yxKDWWf0wwdUj/gPeuL11czrnKFQROnLgY8ll7En9NYoXibgg3C6NK/UDHNtUgWJ"

KEY = {  # asset keys used by the fixtures
    "IT Assets Portal": "a0000077-0000-4000-8000-000000000077",
    "TestApp": "a0000035-0000-4000-8000-000000000035",
    "RequestFlowTestApp": "a0000010-0000-4000-8000-000000000010",
    "ZooApp": "a0000082-0000-4000-8000-000000000082",
    "Banking Account Services": "a0000018-0000-4000-8000-000000000018",
    "People Onboarding": "a0000101-0000-4000-8000-000000000101",
    "Lending Policy Agent": "a000000a-0000-4000-8000-00000000000a",
    "Ops Advisor": "a0000094",  # prefix; resolved below
}


def _fx(name):
    return str(FIX / name)


def _load(name):
    return json.loads((FIX / name).read_text(encoding="utf-8"))


def _tmp_cache(envs=None):
    tmp = pathlib.Path(tempfile.mkdtemp())
    cache = tmp / "cache"; cache.mkdir()
    if envs is None:
        shutil.copy(FIX / "envs-raw.json", cache / "envs-raw.json")
    else:
        (cache / "envs-raw.json").write_text(json.dumps(envs), encoding="utf-8")
    return tmp, cache


def _write(tmp, name, obj):
    p = tmp / name
    p.write_text(obj if isinstance(obj, str) else json.dumps(obj), encoding="utf-8")
    return str(p)


def _run(extra, apps=None, envs=None, capsys=None):
    """main() on a temp cache. Returns (code, cache, tmp)."""
    tmp, cache = _tmp_cache(envs)
    argv = ["build.py", str(cache), str(tmp / "out.html"),
            "--tenant-id", TENANT, "--tenant-hostname", HOSTNAME,
            "--apps", *(apps or [_fx("apps-page.json")]), *extra]
    return build.main(argv), cache, tmp


_BUNDLE_PART = {"assets.json": "assets", "envs.json": "envs", "tenant.json": "tenant",
                "deployments.json": "deployments", "health.json": "health"}


def _json(cache, name):
    """A cache part: meta.json is its own file, the rest live in the bundle."""
    if name in _BUNDLE_PART:
        bundle = json.loads((cache / "tenant-data.json").read_text(encoding="utf-8"))
        return bundle[_BUNDLE_PART[name]]
    return json.loads((cache / name).read_text(encoding="utf-8"))


ALL_DEPLOYMENTS = ["--deployments",
                   f"{DEV}={_fx('env-apps-dev-old-server.json')}",
                   f"{TEST}={_fx('env-apps-test-p1.json')}",
                   f"{TEST}={_fx('env-apps-test-p2.json')}",
                   f"{PROD}={_fx('env-apps-prod.json')}"]


def _template_types():
    """{type: hub} parsed from the TYPES object literal in template.html."""
    html = TEMPLATE.read_text(encoding="utf-8")
    block = html[html.index("const TYPES = {"):]
    block = block[:block.index("};")]
    found = re.findall(r'^\s*(\w+):\s*\{\s*label:\s*"[^"]+",\s*color:\s*"#[0-9A-Fa-f]{6}",\s*hub:\s*"(\w+)"',
                       block, re.M)
    return dict(found)


# ---------------------------------------------------------------------------
# Asset types
# ---------------------------------------------------------------------------

def test_every_real_asset_type_has_an_explicit_template_entry():
    types = _template_types()
    fixture_types = {r["assetType"] for r in _load("apps-page.json")["results"]}
    assert fixture_types == REAL_TYPES          # the fixture really covers every real type
    missing = REAL_TYPES - set(types)
    assert not missing, f"no TYPES entry for {sorted(missing)}"
    assert all(types[t] != "Other" for t in REAL_TYPES)


def test_build_py_type_hubs_mirror_the_template():
    assert build.ASSET_TYPE_HUBS == _template_types()


def test_ai_and_integration_types_land_in_sensible_hubs():
    types = _template_types()
    assert {t for t, h in types.items() if h == "AI"} == {
        "Agent", "AgentDefinition", "AIModelConnection", "KnowledgeBase", "AINativeConnection"}
    assert {t for t, h in types.items() if h == "Integrations"} == {
        "ExternalConnection", "MCPConnection", "SearchServiceConnection", "A2AConnection"}


def test_unknown_type_falls_back_to_other_not_integrations(capsys):
    html = TEMPLATE.read_text(encoding="utf-8")
    fallback = html[html.index("function typeMeta(t)"):][:300]
    assert 'hub: "Other"' in fallback and "Integrations" not in fallback
    page = _load("apps-page.json")
    page["results"].append({"assetKey": "ffffffff-0000-4000-8000-000000000001", "assetType": "FutureThing",
                            "isExternal": False, "name": "Future", "revision": 1,
                            "revisionDateTime": "2026-09-01T00:00:00Z"})
    page["total"] += 1
    tmp = pathlib.Path(tempfile.mkdtemp())
    code, cache, _ = _run([], apps=[_write(tmp, "p.json", page)])
    assert code == 0
    out = capsys.readouterr().out
    assert "Other 1" in out and "FutureThing 1" in out


# ---------------------------------------------------------------------------
# env_apps paging, both server generations
# ---------------------------------------------------------------------------

def test_new_server_next_offset_requires_the_next_page(capsys):
    code, cache, _ = _run(["--deployments", f"{TEST}={_fx('env-apps-test-p1.json')}"])
    assert code == 3
    err = capsys.readouterr().err
    assert "INCOMPLETE: env_apps for environment acme-test" in err
    assert f"env_key: {TEST}, offset: 4" in err
    assert not (cache / "meta.json").exists() and not (cache / "deployments.json").exists()


def test_new_server_both_pages_make_the_environment_complete():
    code, cache, _ = _run(["--deployments", f"{TEST}={_fx('env-apps-test-p1.json')}",
                           f"{TEST}={_fx('env-apps-test-p2.json')}"])
    assert code == 0
    st = _json(cache, "deployments.json")["envs"][TEST]
    assert st["status"] == "complete" and st["shown"] == 6 and st["total"] == 6
    assert st["unmatched"] == 1        # ProductionMonitoringAgent is not in the app_list fixture


def test_old_server_truncated_without_next_offset_is_partial_and_builds(capsys):
    # The older server's envelope: 100 of 165, no `next_offset` key at all.
    assert "next_offset" not in _load("env-apps-dev-old-server.json")
    code, cache, tmp = _run(["--deployments", f"{DEV}={_fx('env-apps-dev-old-server.json')}"])
    assert code == 0
    st = _json(cache, "deployments.json")["envs"][DEV]
    assert st["status"] == "partial" and st["total"] == 165 and st["shown"] == 8
    assert "could not be fetched" in st["reason"]
    assert "acme-dev PARTIAL (8 of 165" in capsys.readouterr().out
    assert (tmp / "out.html").exists()


def test_explicit_null_next_offset_is_the_same_partial():
    page = _load("env-apps-dev-old-server.json"); page["next_offset"] = None
    tmp = pathlib.Path(tempfile.mkdtemp())
    code, cache, _ = _run(["--deployments", f"{DEV}={_write(tmp, 'd.json', page)}"])
    assert code == 0
    assert _json(cache, "deployments.json")["envs"][DEV]["status"] == "partial"


def test_second_page_alone_is_incomplete(capsys):
    code, cache, _ = _run(["--deployments", f"{TEST}={_fx('env-apps-test-p2.json')}"])
    assert code == 3
    assert "cover 2 of 6 deployments but the last page is not truncated" in capsys.readouterr().err
    assert not (cache / "meta.json").exists()


def test_repeated_env_apps_page_is_a_bad_page():
    code, cache, _ = _run(["--deployments", f"{TEST}={_fx('env-apps-test-p1.json')}",
                           f"{TEST}={_fx('env-apps-test-p1.json')}"])
    assert code == 1
    assert not (cache / "meta.json").exists()


def test_incomplete_lines_are_reported_together(capsys):
    # app_list truncated AND an env_apps next page: one run names both.
    page = _load("apps-page.json"); page.update(truncated=True, next_offset=29, total=40)
    tmp = pathlib.Path(tempfile.mkdtemp())
    code, _, _ = _run(["--deployments", f"{TEST}={_fx('env-apps-test-p1.json')}"],
                      apps=[_write(tmp, "a.json", page)])
    assert code == 3
    err = capsys.readouterr().err
    assert "app_list returned 29 of 40" in err and "offset: 29" in err
    assert "env_apps for environment acme-test" in err


def test_unfetched_and_skipped_environments_are_labelled():
    code, cache, _ = _run(["--deployments", f"{TEST}={_fx('env-apps-test-p1.json')}",
                           f"{TEST}={_fx('env-apps-test-p2.json')}",
                           "--deployments-skipped", f"{PROD}=env_apps failed: 403"])
    assert code == 0
    envs = _json(cache, "deployments.json")["envs"]
    assert envs[PROD] == {"status": "skipped", "reason": "env_apps failed: 403"}
    assert envs[DEV] == {"status": "skipped", "reason": "not fetched"}


def test_unknown_env_key_is_a_usage_error():
    code, cache, _ = _run(["--deployments", f"not-an-env={_fx('env-apps-prod.json')}"])
    assert code == 2
    assert not (cache / "meta.json").exists()


def test_malformed_deployments_pair_is_a_usage_error():
    code, _, _ = _run(["--deployments", _fx("env-apps-prod.json")])
    assert code == 2


# ---------------------------------------------------------------------------
# deployments.json shape and drift
# ---------------------------------------------------------------------------

def test_deployments_json_shape():
    code, cache, _ = _run(ALL_DEPLOYMENTS)
    assert code == 0
    dep = _json(cache, "deployments.json")
    assert set(dep) == {"fetched_at", "envs", "listedTypes", "assets", "drift"}
    assert isinstance(dep["fetched_at"], int)
    assert set(dep["listedTypes"]) >= {"WebApplication", "MobileApplication", "Agent", "AgentDefinition"}
    asset_keys = {r["assetKey"] for r in _load("apps-page.json")["results"]}
    for k, entries in dep["assets"].items():
        assert k in asset_keys
        for e in entries:
            assert set(e) == {"env", "rev", "date", "url"}
            assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", e["date"])
    # Ordered lowest → highest purpose: dev, test, prod.
    lpa = [e["env"] for e in dep["assets"][KEY["Lending Policy Agent"]]]
    assert lpa == [DEV, TEST]
    # A deployed AgentDefinition with no URL keeps an empty url, not a missing key.
    adv = next(v for k, v in dep["assets"].items() if k.startswith(KEY["Ops Advisor"]))
    assert adv[0]["url"] == ""


def test_drift_is_measured_against_the_highest_deployed_environment():
    code, cache, _ = _run(ALL_DEPLOYMENTS)
    assert code == 0
    drift = _json(cache, "deployments.json")["drift"]
    # latest r13, Production runs r12 (dev/test not listed for it)
    assert drift[KEY["IT Assets Portal"]] == {"env": PROD, "deployed": 12, "latest": 13}
    # latest r11, highest env it is deployed in is test at r8
    assert drift[KEY["TestApp"]] == {"env": TEST, "deployed": 8, "latest": 11}
    # up to date in its highest environment → no drift
    assert KEY["RequestFlowTestApp"] not in drift
    assert KEY["Lending Policy Agent"] not in drift


# ---------------------------------------------------------------------------
# Health overlay
# ---------------------------------------------------------------------------

def test_health_rows_are_classified_and_a_missing_metric_is_unavailable():
    code, cache, _ = _run(ALL_DEPLOYMENTS + ["--health", f"{PROD}={_fx('health-prod.json')}"])
    assert code == 0
    h = _json(cache, "health.json")
    assert h["hours"] == 168 and h["envs"][PROD]["status"] == "complete"
    assert "uniqueUsers" in h["envs"][PROD]["metrics"]           # requested...
    ita = h["assets"][KEY["IT Assets Portal"]]["by_env"][PROD]
    assert ita["cls"] == "errors" and ita["errors"] == 123
    assert "uniqueUsers" not in ita                                # ...absent: unavailable, not 0
    zoo = h["assets"][KEY["ZooApp"]]["by_env"][PROD]
    assert zoo["cls"] == "traffic" and zoo["errors"] == 0
    # The constructed row with no `requests` reading is "no reading", never zero traffic.
    onb = h["assets"][KEY["People Onboarding"]]["by_env"][PROD]
    assert onb == {"cls": "noReading"}
    # The row whose key is not in app_list is counted, not dropped silently.
    assert h["envs"][PROD]["unmatched"] == 1


def test_app_score_never_reaches_the_cache():
    # The "Batch Scheduler" row: appScore 100 with 82% errors.
    row = next(r for r in _load("health-prod.json")["results"] if r["applicationName"] == "Batch Scheduler")
    assert row["appScore"] == 100 and row["errorPercent"] > 80
    code, cache, _ = _run(ALL_DEPLOYMENTS + ["--health", f"{PROD}={_fx('health-prod.json')}"])
    assert code == 0
    assert "appScore" not in (cache / "tenant-data.json").read_text()


def test_deployed_app_without_a_row_is_no_traffic_only_when_complete():
    code, cache, _ = _run(ALL_DEPLOYMENTS + ["--health", f"{PROD}={_fx('health-prod.json')}"])
    assert code == 0
    bas = _json(cache, "health.json")["assets"][KEY["Banking Account Services"]]["by_env"][PROD]
    assert bas == {"cls": "noTraffic", "absent": True}

    code, cache, _ = _run(ALL_DEPLOYMENTS + ["--health", f"{PROD}={_fx('health-prod-undetermined.json')}"])
    assert code == 0
    h = _json(cache, "health.json")
    assert h["envs"][PROD]["status"] == "partial"
    assert "not established to be the whole result set" in h["envs"][PROD]["reason"]
    assert h["assets"][KEY["Banking Account Services"]]["by_env"][PROD] == {"cls": "noReading", "absent": True}


def test_real_empty_production_response_means_no_traffic_for_deployed_apps():
    code, cache, _ = _run(ALL_DEPLOYMENTS + ["--health", f"{PROD}={_fx('health-prod-empty.json')}"])
    assert code == 0
    h = _json(cache, "health.json")
    prod_deployed = {r["applicationKey"] for r in _load("env-apps-prod.json")["results"]}
    assert {k for k, v in h["assets"].items() if v["cls"] == "noTraffic"} == prod_deployed


def test_app_health_failure_skips_the_overlay_and_still_builds(capsys):
    code, cache, tmp = _run(ALL_DEPLOYMENTS + [
        "--health-skipped", f"{PROD}=OS-MONS-40300: analytics are not enabled for this tenant"])
    assert code == 0
    assert (tmp / "out.html").exists()
    st = _json(cache, "health.json")["envs"][PROD]
    assert st == {"status": "skipped", "reason": "OS-MONS-40300: analytics are not enabled for this tenant"}
    out = capsys.readouterr().out
    assert "health: skipped (" in out and "OS-MONS-40300" in out
    assert "None" not in out.split("health:", 1)[1]      # no "Noneh, None -> None"


def test_no_production_environment_records_why_health_is_absent(capsys):
    envs = _load("envs-raw.json")
    envs["results"] = [e for e in envs["results"] if e["purpose"] != "Production"]
    code, cache, _ = _run([], envs=envs)
    assert code == 0
    assert _json(cache, "health.json")["skipped"] == "no Production-purpose environment in this tenant"
    assert "health: skipped (no Production-purpose environment" in capsys.readouterr().out


def test_health_next_page_offset_requires_the_next_page(capsys):
    page = _load("health-prod.json"); page["nextPageOffset"] = 5
    tmp = pathlib.Path(tempfile.mkdtemp())
    code, cache, _ = _run(["--health", f"{PROD}={_write(tmp, 'h.json', page)}"])
    assert code == 3
    assert "plus offset: 5" in capsys.readouterr().err
    assert not (cache / "meta.json").exists()


def test_health_pages_that_add_up_are_complete():
    page = _load("health-prod.json")
    p1 = dict(page, results=page["results"][:3], nextPageOffset=3, noData={"status": "undetermined", "reason": "truncated"})
    p2 = dict(page, results=page["results"][3:], nextPageOffset=0, noData={"status": "undetermined", "reason": "offset"})
    tmp = pathlib.Path(tempfile.mkdtemp())
    code, cache, _ = _run(ALL_DEPLOYMENTS + ["--health", f"{PROD}={_write(tmp, 'h1.json', p1)}",
                                             f"{PROD}={_write(tmp, 'h2.json', p2)}"])
    assert code == 0
    assert _json(cache, "health.json")["envs"][PROD]["status"] == "complete"


def test_health_page_for_another_environment_is_a_bad_page():
    code, cache, _ = _run(["--health", f"{DEV}={_fx('health-prod.json')}"])
    assert code == 1
    assert not (cache / "meta.json").exists()


# ---------------------------------------------------------------------------
# Harness truncation and unreadable pages
# ---------------------------------------------------------------------------

def _codex_truncated(text):
    """The shape Codex gives an over-budget tool result: header, head, marker, tail."""
    return ("Warning: truncated output (original token count: 24310)\nTotal output lines: 1\n\n"
            + text[:1500] + "…22000 tokens truncated…" + text[-800:])


def test_codex_truncated_app_list_page_is_rejected(capsys):
    tmp = pathlib.Path(tempfile.mkdtemp())
    bad = _write(tmp, "apps-page-1.json", _codex_truncated((FIX / "apps-page.json").read_text()))
    code, cache, _ = _run([], apps=[bad])
    assert code == 1
    err = capsys.readouterr().err
    assert "BAD PAGE" in err and "truncation header" in err and "limit" in err
    assert not (cache / "meta.json").exists()


def test_asset_name_with_the_truncation_words_is_not_rejected():
    # The check reads the start of the page (Codex's header) and, for a page
    # that is not valid JSON, the mid-marker. A tenant-chosen name carrying
    # the same words in valid JSON must build.
    tmp = pathlib.Path(tempfile.mkdtemp())
    page = _load("apps-page.json")
    page["results"][0]["name"] = "Notes: 12 tokens truncated"
    code, cache, _ = _run([], apps=[_write(tmp, "p.json", page)])
    assert code == 0
    names = {a["n"] for a in _json(cache, "assets.json")}
    assert "Notes: 12 tokens truncated" in names


def _injected_line(html, const):
    return next(l for l in html.splitlines() if l.lstrip().startswith(f"const {const} "))


def test_placeholder_text_in_an_asset_name_is_not_substituted():
    # Placeholders are filled in one pass, so the deployments JSON lands in
    # `const DEPLOYMENTS`, not inside an asset name that spells the placeholder.
    tmp = pathlib.Path(tempfile.mkdtemp())
    page = _load("apps-page.json")
    page["results"][0]["name"] = "Report /*__DEPLOYMENTS__*/null /*__HEALTH__*/null"
    code, _, out = _run(ALL_DEPLOYMENTS, apps=[_write(tmp, "p.json", page)])
    assert code == 0
    html = (out / "out.html").read_text()
    assert "Report /*__DEPLOYMENTS__*/null /*__HEALTH__*/null" in html
    assert re.search(r"const DEPLOYMENTS\s*=\s*\{", html)


def test_script_breaking_names_are_escaped_in_the_injected_json():
    tmp = pathlib.Path(tempfile.mkdtemp())
    page = _load("apps-page.json")
    page["results"][0]["name"] = "x</script><script>alert(1)</script>"
    page["results"][1]["name"] = "Legacy note <!--<script> keep"
    code, _, out = _run([], apps=[_write(tmp, "p.json", page)])
    assert code == 0
    line = _injected_line((out / "out.html").read_text(), "ASSETS")
    assert "<" not in line
    assert "\\u003c/script>" in line and "\\u003c!--\\u003cscript>" in line


def test_mid_marker_alone_is_enough_to_reject_an_env_apps_page():
    tmp = pathlib.Path(tempfile.mkdtemp())
    text = (FIX / "env-apps-prod.json").read_text()
    bad = _write(tmp, "d.json", text[:600] + "\n…9000 tokens truncated…\n" + text[-300:])
    code, cache, _ = _run(["--deployments", f"{PROD}={bad}"])
    assert code == 1
    assert not (cache / "meta.json").exists()


def test_non_json_page_is_rejected(capsys):
    tmp = pathlib.Path(tempfile.mkdtemp())
    code, _, _ = _run([], apps=[_write(tmp, "p.json", '{"results": [{"assetKey": "x"')])
    assert code == 1
    assert "is not valid JSON" in capsys.readouterr().err


def test_a_saved_mcp_result_envelope_is_unwrapped():
    tmp = pathlib.Path(tempfile.mkdtemp())
    wrapped = {"content": [{"type": "text", "text": (FIX / "apps-page.json").read_text()}]}
    code, cache, _ = _run([], apps=[_write(tmp, "p.json", wrapped)])
    assert code == 0
    assert _json(cache, "meta.json")["count"] == len(_load("apps-page.json")["results"])


# ---------------------------------------------------------------------------
# auth_status
# ---------------------------------------------------------------------------

def test_auth_status_top_level_fields_drive_tenant_json():
    auth = _load("auth-status.json")
    assert auth["tenant_id"] == TENANT and auth["tenant_hostname"] == HOSTNAME
    code, cache, _ = _run([])
    assert code == 0
    tenant = _json(cache, "tenant.json")
    assert tenant["id"] == auth["tenant_id"]
    assert tenant["hostname"] == auth["tenant_hostname"]
    assert tenant["realm"] == "acme"      # first label of tenant_hostname


def test_skill_reads_tenant_id_not_claims_and_has_no_logged_out_branch():
    skill = (_SKILL / "SKILL.md").read_text(encoding="utf-8")
    assert "claims.aid" not in skill
    assert "logged_in: false" not in skill
    assert "tenant_id" in skill and "tenant_hostname" in skill


# ---------------------------------------------------------------------------
# meta.json freshness and cached mode
# ---------------------------------------------------------------------------

def test_meta_records_overlay_fetch_time_and_cached_mode_keeps_overlays():
    code, cache, tmp = _run(ALL_DEPLOYMENTS + ["--health", f"{PROD}={_fx('health-prod.json')}"])
    assert code == 0
    meta = _json(cache, "meta.json")
    assert isinstance(meta["overlays_fetched_at"], int) and meta["overlays_fetched_at"] <= meta["fetched_at"]
    assert build.main(["build.py", str(cache), str(tmp / "cached.html")]) == 0
    assert KEY["IT Assets Portal"] in (tmp / "cached.html").read_text()


def test_a_pre_bundle_cache_is_stale_not_rendered(capsys):
    tmp, cache = _tmp_cache()
    for name in ("assets.json", "envs.json", "tenant.json"):
        (cache / name).write_text("[]" if name != "tenant.json" else "{}")
    assert build.main(["build.py", str(cache), str(tmp / "cached.html")]) == 3
    assert "STALE" in capsys.readouterr().err

def test_asset_name_cannot_close_the_inline_script():
    page = _load("apps-page.json")
    page["results"][0]["name"] = "</script><img src=x onerror=alert(1)>"
    tmp = pathlib.Path(tempfile.mkdtemp())
    code, _, out_tmp = _run([], apps=[_write(tmp, "p.json", page)])
    assert code == 0
    html = (out_tmp / "out.html").read_text()
    assert "</script><img" not in html and "\\u003c/script>" in html


# ---------------------------------------------------------------------------
# End to end: the script as the agent runs it
# ---------------------------------------------------------------------------

def test_end_to_end_subprocess_build_and_cached_rerender():
    tmp, cache = _tmp_cache()
    out = tmp / "tenant-architecture.html"
    cmd = [sys.executable, str(_SCRIPTS / "build.py"), str(cache), str(out),
           "--tenant-id", TENANT, "--tenant-hostname", HOSTNAME,
           "--apps", _fx("apps-page.json"), *ALL_DEPLOYMENTS,
           "--health", f"{PROD}={_fx('health-prod.json')}"]
    res = subprocess.run(cmd, capture_output=True, text=True)
    assert res.returncode == 0, res.stderr
    assert "deployments (as of" in res.stdout and "health (168h" in res.stdout
    html = out.read_text(encoding="utf-8")
    # Every placeholder replaced with the cached data.
    for placeholder, _ in build.PLACEHOLDERS:
        assert placeholder not in html
    assert '"realm":"acme"' in html
    assert KEY["IT Assets Portal"] in html and '"drift":{' in html and '"noTraffic"' in html
    # The pinned graph library: SRI + CORS on the tag, same hash for the fallback.
    tag = re.search(r'<script id="vis-lib"[^>]*>', html, re.S).group(0)
    assert f'integrity="{SRI}"' in tag and 'crossorigin="anonymous"' in tag
    assert "vis-network@9.1.9/standalone/umd/vis-network.min.js" in tag
    assert f'const VIS_SRI      = "{SRI}";' in html
    assert "Graph library could not load" in html        # offline fallback message
    # Cached mode, as Step 5 runs it.
    res2 = subprocess.run([sys.executable, str(_SCRIPTS / "build.py"), str(cache), str(tmp / "cached.html")],
                          capture_output=True, text=True)
    assert res2.returncode == 0, res2.stderr
    # Same cache files in, same page out.
    assert (tmp / "cached.html").read_text(encoding="utf-8") == html



# ---------------------------------------------------------------------------
# The bundle: the render step's only input
# ---------------------------------------------------------------------------

def _bundle(cache):
    return json.loads((cache / "tenant-data.json").read_text(encoding="utf-8"))


def test_render_from_the_bundle_alone_equals_the_fresh_build():
    code, cache, tmp = _run(ALL_DEPLOYMENTS + ["--health", f"{PROD}={_fx('health-prod.json')}"] + AI)
    assert code == 0
    fresh = (tmp / "out.html").read_text()
    only = pathlib.Path(tempfile.mkdtemp())
    shutil.copy(cache / "tenant-data.json", only / "tenant-data.json")   # no raw pages, no meta
    assert build.main(["build.py", str(only), str(only / "o.html")]) == 0
    assert (only / "o.html").read_text() == fresh


def test_malformed_bundle_names_the_field(capsys):
    code, cache, tmp = _run([])
    b = _bundle(cache)
    b["assets"][2]["k"] = 42
    (cache / "tenant-data.json").write_text(json.dumps(b))
    assert build.main(["build.py", str(cache), str(tmp / "o.html")]) == 1
    err = capsys.readouterr().err
    assert "BAD BUNDLE" in err and "assets[2].k: expected a string, got int" in err
    del b["envs"]
    (cache / "tenant-data.json").write_text(json.dumps(b))
    assert build.main(["build.py", str(cache), str(tmp / "o.html")]) == 1
    assert "envs: expected a list, got missing" in capsys.readouterr().err


def test_older_bundle_schema_is_stale(capsys):
    code, cache, tmp = _run([])
    b = _bundle(cache); b["schema"] = 0
    (cache / "tenant-data.json").write_text(json.dumps(b))
    assert build.main(["build.py", str(cache), str(tmp / "o.html")]) == 3
    assert "STALE" in capsys.readouterr().err


def test_unknown_extra_fields_still_render():
    code, cache, tmp = _run([])
    b = _bundle(cache); b["futureField"] = {"x": 1}; b["assets"][0]["extra"] = True
    (cache / "tenant-data.json").write_text(json.dumps(b))
    assert build.main(["build.py", str(cache), str(tmp / "o.html")]) == 0


# ---------------------------------------------------------------------------
# AI governance (merged from outsystems-ai-agent-landscape)
# ---------------------------------------------------------------------------

AI = ["--ai-agents", _fx("ai-agents.json"), "--ai-connections", _fx("ai-connections.json")]
UNLISTED_AGENT = "a00000df-0000-4000-8000-0000000000df"      # AgentMonitoring: indexed, not in app_list


def _apps_with_ai():
    """apps-page.json plus asset rows for every fixture agent/connection except
    UNLISTED_AGENT, as app_list returns them (assetType Agent / AIModelConnection)."""
    page = _load("apps-page.json")
    have = {a["assetKey"] for a in page["results"]}
    for name, t in (("ai-agents.json", "Agent"), ("ai-connections.json", "AIModelConnection")):
        for r in _load(name)["data"]:
            if r["key"] != UNLISTED_AGENT and r["key"] not in have:
                page["results"].append({"assetKey": r["key"], "assetType": t, "isExternal": False,
                                        "name": r["name"], "revision": 1,
                                        "revisionDateTime": "2026-09-01T00:00:00Z"})
    page["total"] = page["displayed"] = len(page["results"])
    return page


def _ai_run(extra=None):
    tmp = pathlib.Path(tempfile.mkdtemp())
    return _run(AI + (extra or []), apps=[_write(tmp, "apps.json", _apps_with_ai())])


def test_ai_rows_join_assets_by_key_and_unlisted_rows_are_kept():
    code, cache, _ = _ai_run()
    assert code == 0
    ai = _bundle(cache)["ai"]
    assert ai["status"] == "complete" and ai["stats"]["totalAgents"] == 6 and ai["stats"]["totalConnections"] == 8
    listed = {r["k"]: r["listed"] for r in ai["agents"] + ai["connections"]}
    assert listed[UNLISTED_AGENT] is False and sum(listed.values()) == 13
    assert ai["unlisted"] == [UNLISTED_AGENT]
    assert ai["coveredTypes"] == ["AIModelConnection", "Agent"]


def test_ai_provider_and_entitlement_not_reported_instead_of_a_wrong_bucket():
    code, cache, _ = _ai_run()
    conns = {c["n"]: c for c in _bundle(cache)["ai"]["connections"]}
    bare = conns["legacy_connection_test"]              # row with no provider/entitlement
    assert bare["provider"] == "not reported" and bare["entitlement"] == "not reported"
    stats = _bundle(cache)["ai"]["stats"]
    assert stats["unreportedEntitlementConns"] >= 1 and stats["unreportedProviderConns"] >= 1


def test_ai_pages_follow_the_chain_and_report_incomplete_in_the_same_listing(capsys):
    tmp = pathlib.Path(tempfile.mkdtemp())
    agents = _load("ai-agents.json")
    p1 = dict(agents, data=agents["data"][:3], truncated=True, next_offset=3,
              pagination={"limit": 3, "offset": 0, "nextPageOffset": 3})
    p2 = dict(agents, data=agents["data"][3:], truncated=False,
              pagination={"limit": 3, "offset": 3, "nextPageOffset": None})
    p2.pop("next_offset", None)
    apps = _write(tmp, "apps.json", _apps_with_ai())
    # page 1 alone: INCOMPLETE naming the offset, together with any other page set
    code, cache, _ = _run(["--ai-agents", _write(tmp, "a1.json", p1),
                           "--ai-connections", _fx("ai-connections.json")], apps=[apps])
    assert code == 3
    err = capsys.readouterr().err
    assert "INCOMPLETE: context_agents" in err and "offset: 3" in err
    assert not (cache / "tenant-data.json").exists()
    # both pages, passed in reverse: complete
    code, cache, _ = _run(["--ai-agents", _write(tmp, "a2.json", p2), _write(tmp, "a1b.json", p1),
                           "--ai-connections", _fx("ai-connections.json")], apps=[apps])
    assert code == 0 and _bundle(cache)["ai"]["stats"]["totalAgents"] == 6
    # a repeated page is refused
    code, _, _ = _run(["--ai-agents", _write(tmp, "r1.json", p1), _write(tmp, "r2.json", p1),
                       "--ai-connections", _fx("ai-connections.json")], apps=[apps])
    assert code == 1


def test_ai_skipped_still_builds_and_says_why(capsys):
    code, cache, _ = _run(["--ai-skipped", "context_agents failed: 503"])
    assert code == 0
    assert _bundle(cache)["ai"] == {"status": "skipped", "reason": "context_agents failed: 503"}
    assert "ai governance: skipped (context_agents failed: 503)" in capsys.readouterr().out


def test_ai_needs_both_sections_or_a_skip_reason(capsys):
    code, _, _ = _run(["--ai-agents", _fx("ai-agents.json")])
    assert code == 2 and "both --ai-agents and --ai-connections" in capsys.readouterr().err


def test_ai_truncation_marker_and_script_breaking_names_are_safe():
    tmp = pathlib.Path(tempfile.mkdtemp())
    conns = _load("ai-connections.json")
    conns["data"][0]["providerName"] = {"_truncated": True, "_originalBytes": 3000}
    conns["data"][1]["name"] = "evil </script><!--<script>"
    code, cache, out = _run(["--ai-agents", _fx("ai-agents.json"),
                             "--ai-connections", _write(tmp, "c.json", conns)],
                            apps=[_write(tmp, "apps.json", _apps_with_ai())])
    assert code == 0
    ai = _bundle(cache)["ai"]
    assert any(c["provider"] == "not reported" for c in ai["connections"])
    line = next(l for l in (out / "out.html").read_text().splitlines() if l.lstrip().startswith("const AI "))
    assert "<" not in line and "\\u003c/script>" in line


def test_ai_codex_header_rejected_but_names_with_the_words_accepted():
    tmp = pathlib.Path(tempfile.mkdtemp())
    text = (FIX / "ai-agents.json").read_text()
    bad = _write(tmp, "cut.json", _codex_truncated(text))
    code, _, _ = _run(["--ai-agents", bad, "--ai-connections", _fx("ai-connections.json")])
    assert code == 1
    agents = _load("ai-agents.json"); agents["data"][0]["name"] = "Agent 12 tokens truncated"
    code, cache, _ = _run(["--ai-agents", _write(tmp, "ok.json", agents),
                           "--ai-connections", _fx("ai-connections.json")])
    assert code == 0

def test_ai_native_connection_is_in_both_type_tables():
    types = _template_types()
    assert types.get("AINativeConnection") == "AI"
    assert build.ASSET_TYPE_HUBS.get("AINativeConnection") == "AI"


def test_skill_is_marked_beta():
    skill = (_SKILL / "SKILL.md").read_text(encoding="utf-8")
    assert re.search(r'^\s*maturity: beta$', skill, re.M)
    assert re.search(r'^description: "\[Beta\] ', skill, re.M)



# ---- review fixes ---------------------------------------------------------

def test_newer_env_apps_page_without_total_but_a_next_offset_is_incomplete(capsys):
    page = _load("env-apps-test-p1.json")
    del page["total"]
    tmp = pathlib.Path(tempfile.mkdtemp())
    code, _, _ = _run(["--deployments", f"{TEST}={_write(tmp, 'p1.json', page)}"])
    cap = capsys.readouterr()
    out = cap.out + cap.err
    assert code == 3 and "INCOMPLETE" in out and "offset: 4" in out


def test_app_list_page_of_fifty_without_envelope_is_a_bad_page(capsys):
    page = _load("apps-page.json")
    rows = (page["results"] * 50)[:50]
    for i, r in enumerate(rows):
        rows[i] = dict(r, assetKey=f"b{i:07d}-0000-4000-8000-000000000000")
    tmp = pathlib.Path(tempfile.mkdtemp())
    code, cache, _ = _run([], apps=[_write(tmp, "bare.json", {"results": rows})])
    assert code == 1
    assert "no envelope" in capsys.readouterr().err
    assert not (cache / "tenant-data.json").exists()


def test_iso_timestamps_with_five_digit_fractions_parse_on_every_python():
    d = build._parse_iso("2026-01-01T00:00:00.12345Z")
    assert d.microsecond == 123450 and d.tzinfo is not None
    assert build._parse_iso("2026-01-01").hour == 0
    with pytest.raises(ValueError):
        build._parse_iso("not a date")


def test_health_fallback_never_says_not_deployed_for_untracked_types():
    html = TEMPLATE.read_text(encoding="utf-8")
    i = html.index("deployment not tracked for this type")
    block = html[i - 400:i + 300]
    assert "!listedTypes.has(a.t)" in block
    assert block.index("!listedTypes.has(a.t)") < block.index("'not deployed here'")

if __name__ == "__main__":
    import pytest
    sys.exit(pytest.main([__file__, "-q"]))
