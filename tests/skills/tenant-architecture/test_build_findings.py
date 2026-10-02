#!/usr/bin/env python3
"""Tests for the fixes from the 2026-10-02 live run on a dev tenant:
deployments of assets missing from app_list, the fetch time taken from the
page files (and the warning for a page reused from an earlier run), the
test/demo name heuristic on display names and compact names, the flagged
names on the report line, and the compact form of the AI governance pages.

Runnable two ways:
    python3 test_build_findings.py
    pytest tests/skills/tenant-architecture/
"""
import importlib.util
import json
import os
import pathlib
import shutil
import sys
import tempfile
import time

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import test_build_overlays as t  # noqa: E402  (shared fixtures and helpers)

build = t.build
_fx, _load, _run, _write, _bundle = t._fx, t._load, t._run, t._write, t._bundle
TEST, PROD, DEV = t.TEST, t.PROD, t.DEV
UNLISTED = "a00000df-0000-4000-8000-0000000000df"   # ProductionMonitoringAgent: in env_apps, not in app_list


def _copy(tmp, name, mtime=None):
    """A fixture copied into `tmp`, with an explicit save time."""
    dst = tmp / name
    shutil.copy(t.FIX / name, dst)
    if mtime is not None:
        os.utime(dst, (mtime, mtime))
    return str(dst)


# ---------------------------------------------------------------------------
# Deployments of assets that app_list does not list
# ---------------------------------------------------------------------------

def test_deployed_assets_missing_from_app_list_are_kept_not_dropped(capsys):
    code, cache, _ = _run(t.ALL_DEPLOYMENTS)
    assert code == 0
    dep = _bundle(cache)["deployments"]
    assert dep["envs"][TEST]["unmatched"] == 1
    assert dep["unlisted"] == [{
        "k": UNLISTED, "n": "ProductionMonitoringAgent",
        "deps": [next(e for e in dep["unlisted"][0]["deps"])],
    }]
    entry = dep["unlisted"][0]["deps"][0]
    assert entry["env"] == TEST and set(entry) == {"env", "rev", "date", "url"}
    assert UNLISTED not in dep["assets"]          # still no node: no type, no drift
    out = capsys.readouterr().out
    assert "1 deployed asset(s) with no app_list record" in out and "acme-test 1" in out


def test_unlisted_production_deployments_are_named_on_the_report_line(capsys):
    prod = _load("env-apps-prod.json")
    prod["results"].append(dict(prod["results"][0], applicationKey=UNLISTED,
                                name="ProductionMonitoringAgent", deploymentKey="d-unlisted"))
    prod["total"] = prod["displayed"] = len(prod["results"])
    tmp = pathlib.Path(tempfile.mkdtemp())
    code, cache, _ = _run(["--deployments", f"{PROD}={_write(tmp, 'prod.json', prod)}"])
    assert code == 0
    assert "acme 1: ProductionMonitoringAgent" in capsys.readouterr().out


def test_template_lists_unlisted_deployments_and_keeps_the_table_clear_of_the_panel():
    html = t.TEMPLATE.read_text(encoding="utf-8")
    assert "DEPLOYMENTS.unlisted" in html and "Deployed, not in the asset list" in html
    assert ".graph-wrap.has-detail .table-view" in html
    assert "overlay.classList.add('is-visible')" in html.split("const showOverlay")[1][:200]
    assert html.count("overlay.classList.add('is-visible')") == 1   # every panel opens through showOverlay


def test_unlisted_rows_carry_the_asset_type_when_the_server_sends_it(capsys):
    tmp = pathlib.Path(tempfile.mkdtemp())
    p2 = _load("env-apps-test-p2.json")
    for r in p2["results"]:
        if r["applicationKey"] == UNLISTED:
            r["assetType"] = "AgentDefinition"
    code, cache, _ = _run(["--deployments", f"{TEST}={_fx('env-apps-test-p1.json')}",
                           f"{TEST}={_write(tmp, 'p2.json', p2)}"])
    assert code == 0
    assert _bundle(cache)["deployments"]["unlisted"][0]["t"] == "AgentDefinition"
    assert "with no app_list record, AgentDefinition 1" in capsys.readouterr().out
    # without the field (servers before it): no `t`, no type in the line
    code, cache, _ = _run(t.ALL_DEPLOYMENTS)
    assert "t" not in _bundle(cache)["deployments"]["unlisted"][0]


def test_a_renamed_asset_keeps_its_deployed_name():
    tmp = pathlib.Path(tempfile.mkdtemp())
    prod = _load("env-apps-prod.json")
    row = next(r for r in prod["results"] if r["name"] == "ZooApp")
    row["name"] = "ZooAppOld"                     # the name at the deployed revision
    code, cache, _ = _run(["--deployments", f"{PROD}={_write(tmp, 'prod.json', prod)}"])
    assert code == 0
    entry = _bundle(cache)["deployments"]["assets"][t.KEY["ZooApp"]][0]
    assert entry["as"] == "ZooAppOld"
    others = [e for k, v in _bundle(cache)["deployments"]["assets"].items() if k != t.KEY["ZooApp"] for e in v]
    assert all("as" not in e for e in others)


def test_every_remaining_env_apps_window_is_named_at_once(capsys):
    """A paging server (offset + next_offset): 280 rows in windows of 100."""
    tmp = pathlib.Path(tempfile.mkdtemp())
    base = _load("env-apps-test-p1.json")
    row = base["results"][0]
    page = dict(base, total=280, displayed=100, truncated=True, next_offset=100,
                results=[dict(row, deploymentKey=f"d{i}") for i in range(100)])
    code, _, _ = _run(["--deployments", f"{TEST}={_write(tmp, 'p1.json', page)}"])
    assert code == 3
    err = capsys.readouterr().err
    assert "has 2 more pages" in err
    assert f"env_key: {TEST}, offset: 100, and again with env_key: {TEST}, offset: 200" in err
    assert "all in one parallel message" in err


def test_skill_doc_passes_limit_only_when_the_schema_offers_it():
    skill = (t._SKILL / "SKILL.md").read_text(encoding="utf-8")
    assert "If the tool's input schema lists a `limit` argument" in skill
    assert "If the schema has no\n  `limit`, don't pass one" in skill


# ---------------------------------------------------------------------------
# Fetch time from the page files
# ---------------------------------------------------------------------------

def test_assets_and_meta_are_dated_by_the_page_files_not_the_build(capsys):
    tmp = pathlib.Path(tempfile.mkdtemp())
    fetched = int(time.time()) - 600                     # fetched 10 min before the build
    apps = _copy(tmp, "apps-page.json", fetched)
    prod = _copy(tmp, "env-apps-prod.json", fetched + 30)
    code, cache, _ = _run(["--deployments", f"{PROD}={prod}"], apps=[apps])
    assert code == 0
    os.utime(cache / "envs-raw.json", (fetched, fetched))
    code, cache, _ = _run(["--deployments", f"{PROD}={prod}"], apps=[apps])
    assert _bundle(cache)["tenant"]["fetched_at"] == fetched
    meta = json.loads((cache / "meta.json").read_text())
    assert meta["fetched_at"] == fetched and meta["overlays_fetched_at"] == fetched + 30


def test_a_page_from_an_earlier_run_is_warned_about(capsys):
    tmp = pathlib.Path(tempfile.mkdtemp())
    now = int(time.time())
    apps = _copy(tmp, "apps-page.json", now)
    old_prod = _copy(tmp, "env-apps-prod.json", now - 3 * 3600)    # saved three hours earlier
    code, cache, _ = _run(["--deployments", f"{PROD}={old_prod}"], apps=[apps])
    assert code == 0
    err = capsys.readouterr().err
    assert "warning: the page files were saved 180 min apart" in err and "env-apps-prod.json" in err
    assert json.loads((cache / "meta.json").read_text())["fetched_at"] == now - 3 * 3600


def test_pages_from_one_fetch_carry_no_warning(capsys):
    tmp = pathlib.Path(tempfile.mkdtemp())
    now = int(time.time())
    apps = _copy(tmp, "apps-page.json", now - 60)
    prod = _copy(tmp, "env-apps-prod.json", now)
    code, _, _ = _run(["--deployments", f"{PROD}={prod}"], apps=[apps])
    assert code == 0 and "warning: the page files" not in capsys.readouterr().err


# ---------------------------------------------------------------------------
# The test/demo heuristic
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("name,flag", [
    ("AgenticApp_Test", True), ("TestAgent1_0ulh", True), ("Test Agent 1.0 ulh", True),
    ("AgenticIstioRegressionTest", True), ("DemoApp", True), ("XMLTest", True),
    ("test2", True), ("everything_rename_test__", True), ("WIPAgent", True), ("HR Assistant (demo)", True),
    ("Latest Orders", False), ("Contest", False), ("Protester", False),
    ("Temperature", False), ("CloneofLendingFraudAgent", False), ("AgentMonitoring", False),
])
def test_test_demo_heuristic_sees_whole_words_across_case_and_digits(name, flag):
    assert build._looks_test_demo(name) is flag


def test_agents_show_and_are_judged_by_their_asset_list_name(capsys):
    tmp = pathlib.Path(tempfile.mkdtemp())
    apps = t._apps_with_ai()
    agents = _load("ai-agents.json")
    hr = next(r for r in agents["data"] if r["name"] == "HRAssistant")
    for a in apps["results"]:
        if a["assetKey"] == hr["key"]:
            a["name"] = "HR Assistant (demo)"        # the display name; the index says HRAssistant
    code, cache, _ = _run(["--ai-agents", _fx("ai-agents.json"), "--ai-connections", _fx("ai-connections.json")],
                          apps=[_write(tmp, "apps.json", apps)])
    assert code == 0
    row = next(a for a in _bundle(cache)["ai"]["agents"] if a["k"] == hr["key"])
    assert row["n"] == "HR Assistant (demo)" and row["testDemo"] is True
    unlisted = next(a for a in _bundle(cache)["ai"]["agents"] if a["k"] == UNLISTED)
    assert unlisted["n"] == "AgentMonitoring"          # not listed: the indexed name


def test_report_line_names_the_flagged_agents_and_trial_connections(capsys):
    code, _, _ = t._ai_run()
    assert code == 0
    out = capsys.readouterr().out
    assert "Trial connections: TrialClaudeHaiku4_5, TrialGPT5" in out


def test_long_name_lists_are_capped():
    assert build._names([f"n{i}" for i in range(12)]).endswith("n9 (+2 more)")


# ---------------------------------------------------------------------------
# Compact AI governance pages
# ---------------------------------------------------------------------------

def _compact(page):
    keep = ("key", "name", "isPublic", "timestamp", "providerName")
    ad_keep = ("revisionDateTime", "providerId", "entitlement")
    rows = []
    for r in page["data"]:
        c = {k: r[k] for k in keep if k in r}
        ad = r.get("additionalData") or {}
        if any(k in ad for k in ad_keep):
            c["additionalData"] = {k: ad[k] for k in ad_keep if k in ad}
        rows.append(c)
    return dict({k: page[k] for k in ("total", "truncated", "next_offset", "pagination") if k in page},
                data=rows)


def test_compact_ai_pages_build_the_same_governance_view():
    tmp = pathlib.Path(tempfile.mkdtemp())
    apps = _write(tmp, "apps.json", t._apps_with_ai())
    code, full, _ = _run(t.AI, apps=[apps])
    assert code == 0
    agents = _write(tmp, "a.json", json.dumps(_compact(_load("ai-agents.json")), separators=(",", ":")))
    conns = _write(tmp, "c.json", json.dumps(_compact(_load("ai-connections.json")), separators=(",", ":")))
    code, compact, _ = _run(["--ai-agents", agents, "--ai-connections", conns], apps=[apps])
    assert code == 0
    a, b = _bundle(full)["ai"], _bundle(compact)["ai"]
    a.pop("fetched_at"); b.pop("fetched_at")
    assert a == b
    assert len(pathlib.Path(conns).read_text()) < 0.6 * len((t.FIX / "ai-connections.json").read_text())


def test_skill_doc_carries_the_refresh_and_compact_rules():
    skill = (t._SKILL / "SKILL.md").read_text(encoding="utf-8")
    assert "Write every response of this run." in skill
    assert "never `touch` one" in skill
    assert "Compact form of the AI governance pages." in skill
    assert "before any MCP call" in skill
    assert "this skill's contract\n  overrides it" in skill


# ---------------------------------------------------------------------------
# Error paths the agent reads
# ---------------------------------------------------------------------------

def test_app_list_page_without_results_is_a_bad_page(capsys):
    tmp = pathlib.Path(tempfile.mkdtemp())
    code, _, _ = _run([], apps=[_write(tmp, "apps.json", {"data": []})])
    assert code == 1 and "BAD PAGE: app_list page 1 has no `results` list" in capsys.readouterr().err


def test_an_unwritable_output_path_is_one_clean_line(capsys):
    tmp, cache = t._tmp_cache()
    (tmp / "out.html").mkdir()                       # a folder where the page should go
    code = build.main(["build.py", str(cache), str(tmp / "out.html"), "--tenant-id", t.TENANT,
                       "--apps", _fx("apps-page.json")])
    assert code == 1 and "could not write the output file" in capsys.readouterr().err


def test_every_page_control_works_from_the_keyboard():
    """Filter rows, table rows and target rows are not native controls: each
    template gives them a role, a tab stop and Enter / Space handling."""
    skills = t._SKILL.parent
    tenant = (skills / "outsystems-tenant-architecture" / "assets" / "template.html").read_text()
    assert "role', 'checkbox'" in tenant and 'role="radio"' in tenant and "radiogroup" in tenant
    assert tenant.count("keyActivate(") >= 5          # helper + type rows + radios + two tables
    app = (skills / "outsystems-app-architecture" / "assets" / "template.html").read_text()
    assert "role', 'checkbox'" in app and 'id="view-list"' in app and "function renderListing" in app
    dep = (skills / "outsystems-dependency-impact" / "assets" / "template.html").read_text()
    assert "row.setAttribute('role', 'button')" in dep and "aria-sort" in dep
    for html in (tenant, app):
        assert 'aria-live="polite"' in html


def test_only_http_deployment_urls_reach_the_page():
    tmp = pathlib.Path(tempfile.mkdtemp())
    prod = _load("env-apps-prod.json")
    prod["results"][0]["url"] = "javascript:alert(document.domain)"
    prod["results"][1]["url"] = "https://acme.outsystems.app/RequestFlowTestApp"
    code, cache, _ = _run(["--deployments", f"{PROD}={_write(tmp, 'prod.json', prod)}"])
    assert code == 0
    urls = {e["url"] for v in _bundle(cache)["deployments"]["assets"].values() for e in v}
    assert "https://acme.outsystems.app/RequestFlowTestApp" in urls
    assert not any(u.lower().startswith("javascript:") for u in urls)
    html = t.TEMPLATE.read_text(encoding="utf-8")
    assert "const safeUrl" in html and 'href="${esc(d.url)}"' not in html


def test_an_unwritable_cache_is_one_clean_line(capsys):
    tmp, cache = t._tmp_cache()
    (cache / "tenant-data.json").mkdir()               # a folder where the bundle goes
    code = build.main(["build.py", str(cache), str(tmp / "out.html"), "--tenant-id", t.TENANT,
                       "--apps", _fx("apps-page.json")])
    assert code == 1 and "could not write the cache files" in capsys.readouterr().err


def test_an_agent_exactly_180_days_old_is_stale(capsys):
    import datetime
    tmp = pathlib.Path(tempfile.mkdtemp())
    agents = _load("ai-agents.json")
    when = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=180, hours=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
    agents["data"][0].setdefault("additionalData", {})["revisionDateTime"] = when
    code, cache, _ = _run(["--ai-agents", _write(tmp, "a.json", agents), "--ai-connections", _fx("ai-connections.json")],
                          apps=[_write(tmp, "apps.json", t._apps_with_ai())])
    assert code == 0
    row = next(a for a in _bundle(cache)["ai"]["agents"] if a["k"] == agents["data"][0]["key"])
    assert row["stale"] is True


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q"]))
