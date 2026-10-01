#!/usr/bin/env python3
"""Tests for the schema-3 bundle: attributes and foreign keys, static-entity
records, action signatures, screen inputs (and the absence of screen
roles), AI model connections, the
dependency-impact cache checks, deployments / revisions, Codex truncation
rejection, and an end-to-end build of the sample fixtures.

Runnable two ways:
    python3 test_build_schema3.py
    pytest tests/skills/app-architecture/

Fixtures under fixtures/sample/ are responses in the server's shapes for
one example app, "IT Assets Portal" (names, keys, hostnames and emails are
invented). connections.json and env-apps-prod.json are synthetic and say so
in their `_comment`.
"""
import argparse
import contextlib
import importlib.util
import inspect
import io
import json
import os
import pathlib
import subprocess
import sys
import tempfile
import time

_SCRIPTS = pathlib.Path(__file__).resolve().parents[3] / "claude" / "skills" / "outsystems-app-architecture" / "scripts"
_spec = importlib.util.spec_from_file_location("arch_build_s3", _SCRIPTS / "build.py")
build = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(build)

FX = pathlib.Path(__file__).resolve().parent / "fixtures" / "sample"
APP = "a0000077-0000-4000-8000-000000000077"
DEV, TEST, PROD = ("a00000b6-0000-4000-8000-0000000000b6", "a000011f-0000-4000-8000-00000000011f",
                   "a000003f-0000-4000-8000-00000000003f")
SRI = "sha384-yxKDWWf0wwdUj/gPeuL11czrnKFQROnLgY8ll7En9NYoXibgg3C6NK/UDHNtUgWJ"


def _tmp():
    return pathlib.Path(tempfile.mkdtemp())


def _args(**over):
    """Namespace over the sample fixtures; override any flag."""
    base = dict(app_info=FX / "app-info.json", screens=[FX / "screens.json"], actions=[FX / "actions.json"],
                entities=[FX / "entities.json"], structures=[FX / "structures.json"], roles=[FX / "roles.json"],
                connections=None, refs=None, refs_cache=None, revisions=None, env_list=None, env_apps=None)
    base.update(over)
    return argparse.Namespace(**base)


def _quiet(fn, *a, **kw):
    err = io.StringIO()
    with contextlib.redirect_stderr(err):
        out = fn(*a, **kw)
    return out, err.getvalue()


def _fixture_bundle(**over):
    return _quiet(build._build_from_raw, _args(**over))[0]


def _entity(bundle, name):
    for group in ("entities", "enums", "inheritedEntities", "inheritedEnums"):
        for e in bundle[group]:
            if e["n"] == name:
                return e
    raise KeyError(name)


def _attr(entity, name):
    return next(a for a in entity["attrs"] if a["n"] == name)


# ---- attributes and foreign keys ----------------------------------------

def test_fk_resolves_owned_to_owned_and_owned_to_inherited_on_real_data():
    b = _fixture_bundle()
    eq = _entity(b, "EquipmentRequest")
    assert _attr(eq, "AssetId")["fk"] == {"n": "Asset", "in": "owned", "k": _entity(b, "Asset")["k"]}
    assert _attr(eq, "RequestStatusId")["fk"]["in"] == "owned"                 # owned static entity
    emp = _attr(eq, "EmployeeId")
    assert emp["fk"]["in"] == "inherited" and emp["fk"]["from"] == "PeopleOnboarding"
    assert emp["fk"]["k"] == _entity(b, "Employee")["k"] and emp["req"] is True
    pk = _attr(eq, "Id")
    assert pk["pk"] and pk["t"] == "Long Integer" and "fk" not in pk
    assert _attr(_entity(b, "AccessBadge"), "Notes") == {"n": "Notes", "t": "Text", "len": "2000"}


def test_fk_to_platform_and_unknown_entities():
    rows = [
        {"key": "e1", "name": "Ticket", "isReferenced": False, "additionalData": {"attributes": [
            {"name": "OwnerId", "dataType": "User Identifier"},
            {"name": "LegacyId", "dataType": "Legacy Thing Identifier"},
            {"name": "Title", "dataType": "Text"}]}},
        {"key": "u1", "name": "User", "isReferenced": True, "producerAssetName": "(System)", "additionalData": {}},
    ]
    b = _bundle_from_rows(entities=rows)
    t = _entity(b, "Ticket")
    assert _attr(t, "OwnerId")["fk"] == {"n": "User", "in": "platform", "k": "u1", "from": "(System)"}
    assert _attr(t, "LegacyId")["fk"] == {"n": "Legacy Thing", "in": "external"}
    assert "fk" not in _attr(t, "Title")
    assert b["inheritedBuiltinCount"] == 1          # the platform row is counted, not listed


def test_owned_name_wins_over_inherited_name():
    rows = [{"key": "own", "name": "Status", "isReferenced": False, "isStatic": True, "additionalData": {}},
            {"key": "lib", "name": "Status", "isReferenced": True, "producerAssetName": "Lib", "isStatic": True, "additionalData": {}},
            {"key": "t", "name": "Task", "isReferenced": False, "additionalData": {"attributes": [{"name": "StatusId", "dataType": "Status Identifier"}]}}]
    b = _bundle_from_rows(entities=rows)
    assert _attr(_entity(b, "Task"), "StatusId")["fk"]["k"] == "own"


def _bundle_from_rows(entities=(), actions=(), screens=(), structures=(), roles=()):
    tmp = _tmp()
    def dump(n, rows):
        p = tmp / n; p.write_text(json.dumps({"data": list(rows), "total": len(rows), "truncated": False,
                                              "pagination": {"limit": 100, "offset": 0, "total": len(rows)}})); return [p]
    info = tmp / "info.json"; info.write_text(json.dumps({"assetKey": APP, "name": "App", "revision": 3}))
    return _quiet(build._build_from_raw, argparse.Namespace(
        app_info=info, screens=dump("s.json", screens), actions=dump("a.json", actions),
        entities=dump("e.json", entities), structures=dump("st.json", structures), roles=dump("r.json", roles)))[0]


# ---- static-entity records -------------------------------------------------

def test_records_parse_the_json_string_from_real_data():
    b = _fixture_bundle()
    st = _entity(b, "AssetStatus")
    assert st["records"] == ["InStock", "Assigned", "Retired", "InRepair"] and st["recordCount"] == 4
    assert _entity(b, "EmployeeStatus")["records"] == []          # "[]" on an inherited static entity


def test_records_malformed_is_empty_with_a_warning_and_the_list_is_capped():
    (recs, n, cut), err = _quiet(build._parse_records, "[not json", "Broken")
    assert recs == [] and n == 0 and cut is None and "Broken" in err and "warning" in err
    (recs, n, _), err = _quiet(build._parse_records, '{"a": 1}', "NotAList")
    assert recs == [] and "NotAList" in err
    many = json.dumps([f"R{i}" for i in range(build.RECORDS_KEEP + 7)])
    recs, n, _ = build._parse_records(many, "Many")
    assert len(recs) == build.RECORDS_KEEP and n == build.RECORDS_KEEP + 7
    recs, _, _ = build._parse_records([{"Identifier": "A"}, {"Label": "B"}, 3], "Mixed")
    assert recs == ["A", "B", "3"]
    assert build._parse_records(None, "Absent") == ([], 0, None)


# ---- the server's truncation marker ({"_truncated": true, "_originalBytes": N}) ----

MARKER = {"_truncated": True, "_originalBytes": 4711}


def test_truncated_records_are_reported_as_truncated_not_as_none():
    assert build._parse_records(MARKER, "Country") == ([], None, 4711)
    tmp = _tmp()
    page = json.loads((FX / "entities.json").read_text())
    st = next(e for e in page["data"] if e["name"] == "AssetStatus")
    st["additionalData"]["records"] = MARKER
    p = tmp / "e.json"; p.write_text(json.dumps(page))
    r = _run(tmp / "cache", tmp / "out.html", *_six(tmp, **{"--entities": p}))
    assert r.returncode == 0, r.stderr
    b = json.loads((tmp / "cache" / "app-data.json").read_text())
    item = next(e for e in b["enums"] if e["n"] == "AssetStatus")
    assert item["records"] == [] and item["recordCount"] is None and item["recordsTruncatedBytes"] == 4711


def test_truncated_descriptions_do_not_crash_and_say_so():
    tmp = _tmp()
    ents = json.loads((FX / "entities.json").read_text())
    owned = next(e for e in ents["data"] if not e.get("isReferenced") and e["additionalData"].get("attributes"))
    owned["additionalData"]["attributes"][0]["description"] = MARKER
    acts = json.loads((FX / "actions.json").read_text())
    with_params = next(a for a in acts["data"] if a["additionalData"].get("parameters"))
    with_params["additionalData"]["parameters"][0]["description"] = MARKER
    pe, pa = tmp / "e.json", tmp / "a.json"
    pe.write_text(json.dumps(ents)); pa.write_text(json.dumps(acts))
    r = _run(tmp / "cache", tmp / "out.html", *_six(tmp, **{"--entities": pe, "--actions": pa}))
    assert r.returncode == 0 and "Traceback" not in r.stderr, r.stderr
    b = json.loads((tmp / "cache" / "app-data.json").read_text())
    ent = next(e for e in b["entities"] + b["enums"] if e["k"] == owned["key"])
    assert any("truncated it (4711 bytes)" in a.get("d", "") for a in ent["attrs"])
    act = next(a for a in b["actions"] if a["k"] == with_params["key"])
    assert any("truncated it (4711 bytes)" in x.get("d", "") for x in act["in"] + act["out"])


# ---- deployments: asset types env_apps cannot list, null revisions, degraded inputs ----

def _deps_for(app_type, env_apps):
    envs = json.loads((FX / "env-list.json").read_text())
    return build._build_deployments(envs, env_apps, "k-app", 5, "2026-09-29T00:00:00Z", app_type)


def test_workflows_are_unknown_everywhere_never_not_deployed():
    d = _deps_for("Workflow", {e["key"]: {"results": [], "total": 0} for e in
                               json.loads((FX / "env-list.json").read_text())["results"]})
    assert {e["status"] for e in d["envs"]} == {"unknown"}
    assert all("workflows" in e["reason"] for e in d["envs"])


def test_libraries_are_not_applicable_and_carry_no_drift():
    d = _deps_for("LowCodeLibrary", {})
    assert {e["status"] for e in d["envs"]} == {"n/a"}
    assert not any("behind" in e for e in d["envs"])


def test_a_null_deployed_revision_is_deployed_at_an_unknown_revision():
    envs = json.loads((FX / "env-list.json").read_text())["results"]
    first = envs[0]["key"]
    d = _deps_for("WebApplication", {first: {"results": [{"applicationKey": "k-app", "revision": None,
                                                          "deploymentDateTime": "2026-09-01T00:00:00Z"}]}})
    row = next(e for e in d["envs"] if e["k"] == first)
    assert row["status"] == "deployed" and row["rev"] is None and "behind" not in row


def test_missing_or_failed_optional_inputs_degrade_instead_of_failing():
    tmp = _tmp()
    err = tmp / "err.json"; err.write_text(json.dumps({"isError": True, "content": [{"type": "text", "text": "boom"}]}))
    envs = json.loads((FX / "env-list.json").read_text())["results"]
    r = _run(tmp / "cache", tmp / "out.html", *_six(tmp),
             "--refs", str(tmp / "missing-refs.json"), "--revisions", str(err),
             "--env-list", str(FX / "env-list.json"),
             "--env-apps", *[f"{e['key']}={err}" for e in envs])
    assert r.returncode == 0, r.stderr
    b = json.loads((tmp / "cache" / "app-data.json").read_text())
    assert b["revisions"] is None
    # every env_apps call failed: the section is still there, every environment unknown
    assert b["deployments"] and {e["status"] for e in b["deployments"]["envs"]} == {"unknown"}


def test_connection_rows_are_named_by_their_own_key_and_name():
    rows = [{"key": "c1", "name": "MyAzure", "isReferenced": True, "providerName": "Azure OpenAI"},
            {"key": "k-app", "name": "TheAppItself", "isReferenced": False}]
    assert build._connection_deps(rows, "k-app") == [
        {"k": "c1", "n": "MyAzure", "kind": "Azure OpenAI", "cat": "AIModel", "rev": ""}]


# ---- action signatures, screens, structures ---------------------------------

def test_action_signatures_split_inputs_and_outputs():
    b = _fixture_bundle()
    login = next(a for a in b["actions"] if a["n"] == "DoLogin")
    assert [p["n"] for p in login["in"]] == ["Username", "Password"]
    assert all(p["req"] for p in login["in"])
    assert [(p["n"], p["t"]) for p in login["out"]] == [("Success", "Boolean"), ("ErrorMessage", "Text")]
    csv = next(a for a in b["actions"] if a["n"] == "GetAssetsCSV")
    assert csv["in"] == [] and csv["out"][0]["t"] == "Binary Data"
    ins, outs = build._signature({"additionalData": {"parameters": [
        {"name": "X", "dataType": "Integer", "parameterType": 1}, {"name": "Y", "dataType": "Text", "parameterType": 0}]}})
    assert [p["n"] for p in outs] == ["X"] and [p["n"] for p in ins] == ["Y"]   # numeric code without the label


def test_screen_inputs_and_title():
    b = _fixture_bundle()
    reset = next(s for s in b["screens"] if s["n"] == "RecoverPasswordReset")
    assert reset["inputs"] == [{"n": "VerificationCode", "t": "Text"}, {"n": "Email", "t": "Email", "req": True}]
    assert reset["title"] == "Set a new password"                 # expression junk stripped
    assert "title" not in next(s for s in b["screens"] if s["n"] == "MaintenanceContracts")   # null title


def test_screen_roles_never_reach_the_bundle_or_the_html():
    # The payload's additionalData.roles comes from the model's screen.Roles list
    # without the access mode: a screen open to Everyone
    # can list the app role. Nothing may present it, so it is not in the bundle.
    tmp = _tmp()
    page = json.loads((FX / "screens.json").read_text())
    assert all(r["additionalData"]["roles"] for r in page["data"])      # the payload carries them
    for r in page["data"]:
        r["additionalData"]["roles"].append({"key": "zz-role", "name": "ScreenOnlyRoleXyz", "isReferenced": True})
    p = tmp / "screens.json"; p.write_text(json.dumps(page))
    r = _run(tmp / "cache", tmp / "out.html", *_six(tmp, **{"--screens": p}))
    assert r.returncode == 0, r.stderr
    bundle = json.loads((tmp / "cache" / "app-data.json").read_text())
    assert all("roles" not in s for s in bundle["screens"])
    html = (tmp / "out.html").read_text()
    assert "ScreenOnlyRoleXyz" not in html and "zz-role" not in html
    assert "Screen → role" not in html and "Roles recorded" not in html
    assert not hasattr(build, "_screen_roles")


def test_structure_attributes_are_kept():
    b = _fixture_bundle()
    rec = next(s for s in b["structures"] if s["n"] == "StaticRecord")
    assert rec["attrs"] == [{"n": "Id", "t": "Integer"}, {"n": "Label", "t": "Text", "len": "50"}]


# ---- AI model connections + dedupe ------------------------------------------

def test_context_connections_become_aimodel_deps():
    b = _fixture_bundle(connections=[FX / "connections.json"], refs=FX / "refs.json")
    ai = [d for d in b["deps"] if d["cat"] == "AIModel"]
    assert [(d["n"], d["kind"]) for d in ai] == [("AzureOpenAIDefault", "Azure OpenAI")]
    assert sorted(d["n"] for d in b["deps"] if d["cat"] == "Library") == ["PeopleOnboarding", "vendor_contracts"]
    assert b["depsSource"] == "app_refs"


def test_connection_and_app_refs_rows_for_the_same_asset_dedupe_to_aimodel():
    conn = build._connection_deps([{"key": "c1", "name": "GPT", "producerAssetKey": "c1", "producerAssetName": "GPT",
                                    "isReferenced": True, "assetKey": APP},
                                   {"key": APP, "name": "Self", "isReferenced": False, "assetKey": APP}], APP)
    assert [d["n"] for d in conn] == ["GPT"]                        # the app itself is skipped
    refs = build._refs_deps({"references": [{"producerAssetKey": "c1", "producerAssetName": "GPT", "kinds": ["actions"]},
                                            {"name": "gpt", "kind": "eSpace"},          # keyless, same name
                                            {"producerAssetKey": "l1", "producerAssetName": "Lib", "kinds": ["entities"]}]})
    merged = build._merge_deps(conn, refs)
    assert [(d["n"], d["cat"]) for d in merged] == [("GPT", "AIModel"), ("Lib", "Library")]


# ---- dependency-impact refs cache -------------------------------------------

def _cache_file(tmp, payload, age_s=0.0):
    p = tmp / "tenant-1" / "refs" / f"{APP}.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(payload))
    t = time.time() - age_s
    os.utime(p, (t, t))
    return p


def test_refs_cache_failed_placeholder_is_a_miss():
    tmp = _tmp()
    p = _cache_file(tmp, {"assetKey": APP, "failed": True, "reason": "timeout"})
    raw, reason = build._refs_cache_verdict(p, APP, None)
    assert raw is None and "failed" in reason


def test_refs_cache_older_than_the_revision_is_a_miss_and_fresh_is_a_hit():
    tmp = _tmp()
    good = {"assetKey": APP, "references": [{"producerAssetKey": "l1", "producerAssetName": "Lib", "kinds": ["entities"]}]}
    p = _cache_file(tmp, good, age_s=3600)                         # written an hour ago
    saved_after = build._parse_ts(time.strftime("%Y-%m-%dT%H:%M:%S.12345Z", time.gmtime(time.time() - 60)))
    raw, reason = build._refs_cache_verdict(p, APP, saved_after)
    assert raw is None and "revision" in reason
    saved_before = build._parse_ts(time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(time.time() - 7200)))
    raw, reason = build._refs_cache_verdict(p, APP, saved_before)
    assert reason is None and raw == good
    old = _cache_file(_tmp(), good, age_s=25 * 3600)
    assert "24h" in build._refs_cache_verdict(old, APP, None)[1]
    other = _cache_file(_tmp(), dict(good, assetKey="another-app"))
    assert "another app" in build._refs_cache_verdict(other, APP, None)[1]


def test_refs_cache_is_found_under_the_cache_root_and_used_when_app_refs_failed():
    tmp = _tmp()
    root = tmp / "outsystems-dependency-impact"
    _cache_file(root, {"assetKey": APP, "references": [{"producerAssetKey": "l1", "producerAssetName": "CachedLib", "kinds": ["entities"]}]})
    assert build._find_refs_cache(root, APP).name == f"{APP}.json"
    failed = tmp / "refs-raw.json"; failed.write_text(json.dumps({"assetKey": APP, "failed": True}))
    b = _fixture_bundle(refs=failed, refs_cache=root)
    assert [d["n"] for d in b["deps"]] == ["CachedLib"] and b["depsSource"] == "dependency-impact cache"
    # A cache written before the app's revision (app_info.revisionDateTime = 2026-09-01) is refused.
    stale = _cache_file(tmp / "stale", {"assetKey": APP, "references": [{"producerAssetName": "Old", "kinds": ["entities"]}]})
    t = time.mktime((2026, 8, 1, 0, 0, 0, 0, 0, 0)); os.utime(stale, (t, t))
    b, err = _quiet(build._build_from_raw, _args(refs_cache=tmp / "stale"))
    assert b["deps"] == [] and b["depsSource"] is None and "not used" in err


def test_parse_ts_accepts_the_servers_five_digit_fraction():
    ts = build._parse_ts("2026-08-14T02:50:26.41323Z")
    assert ts is not None and ts.microsecond == 413230 and ts.utcoffset().total_seconds() == 0
    assert build._parse_ts("2026-08-14T03:50:26+01:00") == build._parse_ts("2026-08-14T02:50:26Z")
    assert build._parse_ts("garbage") is None


# ---- deployments and revisions ----------------------------------------------

def _env_apps(rows, truncated=False, total=None):
    return {"results": rows, "displayed": len(rows), "total": len(rows) if total is None else total, "truncated": truncated}


ENVS = {"results": [{"key": "d", "name": "dev", "purpose": "Development", "order": 0},
                    {"key": "p", "name": "prod", "purpose": "Production", "order": 1000},
                    {"key": "t", "name": "test", "purpose": "NonProduction", "order": 100}]}


def test_env_apps_keeps_only_the_exact_app_key():
    lookalike = {"applicationKey": "other", "name": "App Archive", "revision": 99}
    dep = build._build_deployments(ENVS, {"d": _env_apps([lookalike, {"applicationKey": APP, "name": "App", "revision": 13,
                                                                     "deploymentDateTime": "2026-09-01T03:07:37.008Z"}]),
                                          "t": _env_apps([lookalike]),
                                          "p": _env_apps([{"applicationKey": APP, "name": "App", "revision": 9}])},
                                   APP, 13, "2026-09-29T10:00:00Z")
    by = {e["n"]: e for e in dep["envs"]}
    assert [e["n"] for e in dep["envs"]] == ["dev", "test", "prod"]           # env_list order
    assert by["dev"]["status"] == "deployed" and by["dev"]["rev"] == 13 and by["dev"]["behind"] == 0
    assert by["test"]["status"] == "not-deployed"                             # substring match only
    assert by["prod"]["rev"] == 9 and by["prod"]["behind"] == 4
    assert dep["fetchedAt"] == "2026-09-29T10:00:00Z" and dep["latestRevision"] == 13


def test_truncated_env_apps_without_a_match_is_unknown_not_undeployed():
    dep = build._build_deployments(ENVS, {"d": _env_apps([{"applicationKey": "x", "name": "App2"}] * 3, truncated=True),
                                          "t": _env_apps([{"applicationKey": "x", "name": "App2"}], total=150),
                                          "p": _env_apps([{"applicationKey": APP, "name": "App", "revision": 2}], truncated=True)},
                                   APP, 13, "now")
    by = {e["n"]: e for e in dep["envs"]}
    assert by["dev"]["status"] == "unknown" and "truncated" in by["dev"]["reason"]
    assert by["test"]["status"] == "unknown"                                  # displayed < total
    assert by["prod"]["status"] == "deployed"                                 # a match is a match, truncated or not
    dep = build._build_deployments(ENVS, {"d": _env_apps([])}, APP, 13, "now")
    assert {e["n"]: e["status"] for e in dep["envs"]} == {"dev": "not-deployed", "test": "unknown", "prod": "unknown"}
    assert build._build_deployments(None, {}, APP, 13, "now") is None


def test_revisions_are_compact_newest_first():
    r = build._build_revisions(json.loads((FX / "revisions.json").read_text()))
    assert r["total"] == 13 and [x["rev"] for x in r["rows"]] == [13, 12, 11, 10, 9]
    assert r["rows"][0] == {"rev": 13, "at": "2026-09-01T03:07:35.990488Z", "digest": "a0000070-0000-4000-8000-000000000070"}
    r = build._build_revisions({"results": [{"revision": 1, "tag": "v1"}, {"revision": 2}], "total": 2})
    assert r["rows"] == [{"rev": 2, "at": "", "digest": ""}, {"rev": 1, "at": "", "digest": "", "tag": "v1"}]


# ---- harness truncation and bad input ---------------------------------------

def _run(*argv):
    return subprocess.run([sys.executable, str(_SCRIPTS / "build.py"), *map(str, argv)], capture_output=True, text=True)


def _six(tmp, **swap):
    files = {"--app-info": FX / "app-info.json", "--screens": FX / "screens.json", "--actions": FX / "actions.json",
             "--entities": FX / "entities.json", "--structures": FX / "structures.json", "--roles": FX / "roles.json"}
    files.update(swap)
    out = []
    for k, v in files.items():
        out += [k, v]
    return out


def test_codex_truncation_markers_are_rejected_with_exit_1():
    real = (FX / "screens.json").read_text()
    head, tail = real[:3000], real[-2000:]
    for marker in ("Warning: truncated output (original token count: 21794)\nTotal output lines: 4\n\n",
                   "…8805 tokens truncated…", "…12000 chars truncated…", "\n[... omitted 21 of 277 lines ...]\n"):
        tmp = _tmp()
        cut = tmp / "screens-raw.json"
        cut.write_text(marker + head + tail if marker.startswith("Warning") else head + marker + tail)
        r = _run(tmp / "cache", tmp / "out.html", *_six(tmp, **{"--screens": cut}))
        assert r.returncode == 1 and "BAD INPUT" in r.stderr and "truncation" in r.stderr, r.stderr
        assert "smaller `limit`" in r.stderr and not (tmp / "cache" / "app-data.json").exists()
    # The same words inside valid JSON (a tenant-chosen description) are data,
    # not a truncation: only the header at the start or an invalid body count.
    tmp = _tmp()
    page = json.loads(real)
    page["data"][0]["description"] = "Warning: truncated output (original token count: 1), 12 tokens truncated"
    p = tmp / "s.json"; p.write_text(json.dumps(page))
    assert _run(tmp / "c", tmp / "o.html", *_six(tmp, **{"--screens": p})).returncode == 0


def test_invalid_json_page_is_bad_input():
    tmp = _tmp()
    p = tmp / "entities-raw.json"; p.write_text('{"data": [ {"key": "a"')
    r = _run(tmp / "cache", tmp / "out.html", *_six(tmp, **{"--entities": p}))
    assert r.returncode == 1 and "BAD INPUT" in r.stderr and "not valid JSON" in r.stderr, r.stderr


def test_env_apps_flag_needs_key_equals_path():
    tmp = _tmp()
    r = _run(tmp / "cache", tmp / "out.html", *_six(tmp), "--env-apps", str(FX / "env-apps-dev.json"))
    assert r.returncode == 1 and "ENV_KEY=PATH" in r.stderr


# ---- schema refusal + end to end ---------------------------------------------

def test_cached_mode_refuses_a_schema_2_bundle():
    tmp = _tmp(); cache = tmp / "cache"; cache.mkdir()
    b2 = {"app": {"key": APP, "name": "App", "type": "WebApplication", "revision": 3, "description": "", "date": ""},
          "uiFlows": [], "screens": [], "actions": [], "entities": [], "inheritedEntities": [], "enums": [],
          "inheritedEnums": [], "structures": [], "roles": [], "deps": [], "inheritedCount": 0, "inheritedBuiltinCount": 0}
    (cache / "app-data.json").write_text(json.dumps(b2))
    r = _run(cache, tmp / "out.html")
    assert r.returncode == 3 and "STALE" in r.stderr and "schema 2" in r.stderr, r.stderr
    assert not (tmp / "out.html").exists()


def test_end_to_end_build_of_the_real_fixtures():
    tmp = _tmp()
    r = _run(tmp / "cache", tmp / "out.html", *_six(tmp),
             "--connections", FX / "connections.json", "--refs", FX / "refs.json", "--revisions", FX / "revisions.json",
             "--env-list", FX / "env-list.json",
             "--env-apps", f"{DEV}={FX / 'env-apps-dev.json'}", f"{TEST}={FX / 'env-apps-test.json'}",
             f"{PROD}={FX / 'env-apps-prod.json'}")
    assert r.returncode == 0, r.stderr
    assert "fkEdges:6" in r.stdout and "aiModels:1" in r.stdout and "r9" in r.stdout
    html = (tmp / "out.html").read_text()
    assert f'integrity="{SRI}"' in html and 'crossorigin="anonymous"' in html
    assert "/*__APP_DATA__*/null" not in html and '"name":"IT Assets Portal"' in html and '"schema":3' in html
    assert "typeof vis === 'undefined'" in html and "renderFallback" in html
    meta = json.loads((tmp / "cache" / "meta.json").read_text())
    assert meta["schema"] == 3 and meta["revision"] == 13 and "deployments_fetched_at" in meta
    b = json.loads((tmp / "cache" / "app-data.json").read_text())
    assert {e["purpose"]: e["status"] for e in b["deployments"]["envs"]} == \
        {"Development": "deployed", "NonProduction": "not-deployed", "Production": "deployed"}
    # Cached re-render of the same bundle works.
    r = _run(tmp / "cache", tmp / "out2.html")
    assert r.returncode == 0 and (tmp / "out2.html").exists(), r.stderr


def test_script_close_tag_in_a_description_cannot_break_the_page():
    tmp = _tmp(); cache = tmp / "cache"
    b = _fixture_bundle()
    b["app"]["description"] = "evil </script><script>alert(1)</script> and <!--<script> too"
    cache.mkdir(); (cache / "app-data.json").write_text(json.dumps(b))
    r = _run(cache, tmp / "out.html")
    assert r.returncode == 0, r.stderr
    html = (tmp / "out.html").read_text()
    line = next(l for l in html.splitlines() if l.lstrip().startswith("const APP_DATA"))
    assert "<" not in line
    assert "evil \\u003c/script>" in line and "\\u003c!--\\u003cscript>" in line
    assert html.count("</script>") == 2   # the CDN tag and the app script only


if __name__ == "__main__":
    fns = [f for n, f in sorted(globals().items()) if n.startswith("test_") and inspect.isfunction(f)]
    for f in fns:
        f(); print(f"PASS {f.__name__}")
    print(f"{len(fns)} tests passed")


def test_failed_context_connections_degrades_and_is_shown_as_not_fetched(tmp_path):
    missing = tmp_path / "connections-raw.json"            # the call failed: no file
    bundle, err = _quiet(build._build_from_raw, _args(connections=[missing], refs=FX / "refs.json"))
    assert "AI model connections unavailable" in err
    assert bundle["depsUnavailable"] == ["AI model connections"]
    assert all(d["cat"] != "AIModel" for d in bundle["deps"])
    errfile = tmp_path / "connections-error.json"
    errfile.write_text('{"error": "upstream timed out"}', encoding="utf-8")
    bundle, _ = _quiet(build._build_from_raw, _args(connections=[errfile], refs=FX / "refs.json"))
    assert bundle["depsUnavailable"] == ["AI model connections"]


def test_missing_refs_marks_libraries_as_not_fetched():
    bundle = _fixture_bundle(connections=[FX / "connections.json"])
    assert bundle["depsUnavailable"] == ["libraries"]
    assert "deps-unavailable" in (build.pathlib.Path(build.__file__).parent.parent
                                  / "assets" / "template.html").read_text(encoding="utf-8")


SERVER_ERROR = {"error": "UpstreamError: upstream timed out",
                "data": {"category": "UpstreamError", "code": "upstream_error"}}


def test_server_error_shape_with_data_metadata_is_an_error_not_data(tmp_path):
    assert build._is_error_result(SERVER_ERROR)
    assert not build._is_error_result({"data": [], "error": None})
    f = tmp_path / "err.json"
    f.write_text(json.dumps(SERVER_ERROR), encoding="utf-8")
    # A failed env_apps call renders "unknown", never "not deployed".
    raw, _ = _quiet(build._read_optional, f, "env-apps d")
    dep = build._build_deployments(ENVS, {"d": raw}, APP, 13, "2026-09-29T10:00:00Z")
    assert {e["n"]: e for e in dep["envs"]}["dev"]["status"] == "unknown"
    # A failed context_connections call degrades instead of stopping the build.
    bundle, err = _quiet(build._build_from_raw, _args(connections=[f], refs=FX / "refs.json"))
    assert bundle["depsUnavailable"] == ["AI model connections"]


def test_refs_coverage_is_kept_and_shown():
    raw = json.loads((FX / "refs.json").read_text(encoding="utf-8"))
    assert build._refs_coverage(raw) == {"source": "context-service", "indexedKinds": None}
    raw["indexedKinds"] = ["entities"]
    assert build._refs_coverage(raw) == {"source": "context-service", "indexedKinds": ["entities"]}
    assert build._refs_coverage({"source": "oml-fallback", "references": []})["source"] == "oml-fallback"
    bundle = _fixture_bundle(refs=FX / "refs.json", connections=[FX / "connections.json"])
    assert bundle["refsCoverage"]["source"] == "context-service"
    html = (_SCRIPTS.parent / "assets" / "template.html").read_text(encoding="utf-8")
    assert "D.refsCoverage" in html and "may be missing" in html
