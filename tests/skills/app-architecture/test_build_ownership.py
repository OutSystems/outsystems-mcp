#!/usr/bin/env python3
"""Tests for build.py ownership partitioning and action kinds.

Runnable two ways:
    python3 test_build_ownership.py
    pytest tests/skills/app-architecture/

Fixtures mirror the live Context Service rows observed on 2026-09-03: on an
app-scoped query EVERY row carries the visiting app's key in `ownerAppKey`
and `assetKey`; `isReferenced` is the ownership signal and
`additionalData.actionTypeStr` labels the action kind.
"""
import argparse
import importlib.util
import inspect
import json
import pathlib
import tempfile

_SCRIPTS = pathlib.Path(__file__).resolve().parents[3] / "claude" / "skills" / "outsystems-app-architecture" / "scripts"
_spec = importlib.util.spec_from_file_location("arch_build_own", _SCRIPTS / "build.py")
build = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(build)

APP = "a0000077-0000-0000-0000-000000000000"
UI = "a00000ba-0000-0000-0000-000000000000"


def _row(name, *, owned, static=False, extra=None, producer=("OutSystemsUI", UI)):
    r = {"key": f"k-{name}", "name": name, "description": "", "assetKey": APP,
         "ownerAppKey": APP,            # always the visiting app, even when inherited
         "isReferenced": not owned, "isStatic": static, "isPublic": False,
         "producerAssetKey": APP if owned else producer[1],
         "producerAssetName": None if owned else producer[0],
         "additionalData": extra or {}}
    return r


def _action(name, code, label):
    return _row(name, owned=True, extra={"actionType": code, "actionTypeStr": label})


def _bundle(entities, actions, screens=(), structures=(), roles=()):
    tmp = pathlib.Path(tempfile.mkdtemp())
    def dump(n, rows): p = tmp / n; p.write_text(json.dumps({"data": list(rows)})); return p
    info = tmp / "info.json"; info.write_text(json.dumps({"assetKey": APP, "name": "App", "revision": 3, "assetType": "WebApplication"}))
    args = argparse.Namespace(app_info=info, screens=dump("s.json", screens), actions=dump("a.json", actions),
                              entities=dump("e.json", entities), structures=dump("st.json", structures),
                              roles=dump("r.json", roles), refs=None)
    return build._build_from_raw(args)


def test_inherited_rows_are_not_owned_even_though_ownerappkey_matches():
    b = _bundle(entities=[_row("AccessBadge", owned=True), _row("Gradient", owned=False, static=True),
                          _row("Employee", owned=False, producer=("EmployeeDir_DB", "lib-emp"))], actions=[])
    assert [e["n"] for e in b["entities"]] == ["AccessBadge"]
    assert b["enums"] == []                                   # inherited static enum is not the app's
    assert [e["n"] for e in b["inheritedEntities"]] == ["Employee"]   # user library: listed with attribution
    assert b["inheritedEntities"][0]["fromModule"] == "EmployeeDir_DB"
    assert b["inheritedEnums"] == []                          # OutSystemsUI enum: platform module, counted only
    assert b["inheritedCount"] == 2 and b["inheritedBuiltinCount"] == 1


def test_owned_static_entity_is_an_enum():
    b = _bundle(entities=[_row("AssetStatus", owned=True, static=True)], actions=[])
    assert [e["n"] for e in b["enums"]] == ["AssetStatus"] and b["entities"] == []


def test_action_kinds_follow_actiontypestr():
    b = _bundle(entities=[], actions=[_action("ValidateSeedApiKey", 0, "ServerAction"),
                                      _action("DoLogin", 1, "ClientAction"),
                                      _action("Notify", 7, "ServiceAction")])   # label wins over any code
    kinds = {a["n"]: a["kind"] for a in b["actions"]}
    assert kinds == {"ValidateSeedApiKey": "action", "DoLogin": "client", "Notify": "service"}
    assert "function" not in kinds.values()


def test_action_kind_falls_back_to_numeric_code_without_label():
    b = _bundle(entities=[], actions=[_row("Old", owned=True, extra={"actionType": 1}),
                                      _row("Unknown", owned=True, extra={"actionType": 5})])
    kinds = {a["n"]: a["kind"] for a in b["actions"]}
    assert kinds == {"Old": "client", "Unknown": "action"}   # no guessed kinds for unknown codes


def test_null_isreferenced_uses_producerassetkey_before_ownerappkey():
    inherited = _row("Status", owned=False, static=True, producer=("EmployeeDir_DB", "lib-emp")); inherited["isReferenced"] = None
    owned = _row("AccessBadge", owned=True); owned["isReferenced"] = None                       # producer = app
    bare = {"key": "k3", "name": "Bare", "ownerAppKey": APP, "assetKey": APP, "additionalData": {}}  # no producer, no flag
    b = _bundle(entities=[inherited, owned, bare], actions=[])
    assert [e["n"] for e in b["entities"]] == ["AccessBadge", "Bare"]
    assert [e["n"] for e in b["inheritedEnums"]] == ["Status"]
    assert b["inheritedEnums"][0]["fromModule"] == "EmployeeDir_DB"


def test_inherited_static_entities_from_user_libraries_are_listed_and_platform_ones_counted():
    b = _bundle(entities=[_row("Own", owned=True), _row("Gradient", owned=False, static=True),
                          _row("Month", owned=False, static=True, producer=("OutSystemsUI", UI)),
                          _row("EmployeeStatus", owned=False, static=True, producer=("PeopleOnboarding", "onb")),
                          _row("Person", owned=False, producer=("PeopleOnboarding", "onb")),
                          _row("ProcessInstance", owned=False, producer=("(System)", "sys"))], actions=[])
    assert [e["n"] for e in b["inheritedEnums"]] == ["EmployeeStatus"]
    assert [e["n"] for e in b["inheritedEntities"]] == ["Person"]
    assert b["inheritedBuiltinCount"] == 3                     # Gradient, Month (OutSystemsUI), ProcessInstance (System)
    assert b["inheritedCount"] == 5                            # reconciles: 2 listed + 3 platform


def test_context_pages_out_of_order_merge_and_page_two_alone_is_a_missing_page():
    import tempfile
    tmp = pathlib.Path(tempfile.mkdtemp())
    def dump(name, rows, **env):
        p = tmp / name; p.write_text(json.dumps({"data": rows, **env})); return p
    p1 = dump("p1.json", [_row(f"E{i}", owned=True) for i in range(100)], total=130, truncated=True, next_offset=100)
    p2 = dump("p2.json", [_row(f"E{i}", owned=True) for i in range(100, 130)], total=130, truncated=False)
    assert len(build._load_section([p2, p1], "entities")["data"]) == 130       # order does not matter when complete
    try:
        build._load_section([p2], "entities"); assert False, "expected TruncatedSection"
    except build.TruncatedSection as exc:
        assert exc.next_offset is None and exc.received == 30 and exc.total == 130   # missing page, no offset to chase


def test_truncated_context_page_exits_3_and_two_pages_merge():
    import subprocess, sys, tempfile
    tmp = pathlib.Path(tempfile.mkdtemp())
    def dump(name, rows, **env):
        p = tmp / name; p.write_text(json.dumps({"data": rows, **env})); return str(p)
    info = tmp / "info.json"; info.write_text(json.dumps({"assetKey": APP, "name": "App", "revision": 3}))
    empty = dump("e.json", [], total=0, truncated=False)
    page1 = dump("ent1.json", [_row(f"E{i}", owned=True) for i in range(100)], total=130, truncated=True, next_offset=100)
    page2 = dump("ent2.json", [_row(f"E{i}", owned=True) for i in range(100, 130)], total=130, truncated=False)
    base = [sys.executable, str(_SCRIPTS / "build.py"), str(tmp / "cache"), str(tmp / "out.html"), "--app-info", str(info),
            "--screens", empty, "--actions", empty, "--structures", empty, "--roles", empty]
    r = subprocess.run(base + ["--entities", page1], capture_output=True, text=True)
    assert r.returncode == 3 and "entities" in r.stderr and "offset: 100" in r.stderr, r.stderr
    assert not (tmp / "cache" / "app-data.json").exists()
    r = subprocess.run(base + ["--entities", page1, page2], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    assert len(json.loads((tmp / "cache" / "app-data.json").read_text())["entities"]) == 130


def test_legacy_rows_without_isreferenced_fall_back_to_ownerappkey():
    mine = {"key": "k1", "name": "Mine", "ownerAppKey": APP, "additionalData": {}}
    theirs = {"key": "k2", "name": "Theirs", "ownerAppKey": "other-app", "additionalData": {}}
    b = _bundle(entities=[mine, theirs], actions=[])
    assert [e["n"] for e in b["entities"]] == ["Mine"]
    assert [e["n"] for e in b["inheritedEntities"]] == ["Theirs"]


def test_screens_structures_roles_use_the_same_rule():
    b = _bundle(entities=[], actions=[],
                screens=[_row("Login", owned=True, extra={"uiFlowKey": "f", "uiFlowName": "Common"}), _row("LibScreen", owned=False, extra={"uiFlowKey": "g", "uiFlowName": "Lib"})],
                structures=[_row("Own", owned=True), _row("Inh", owned=False)],
                roles=[_row("Admin", owned=True), _row("LibRole", owned=False)])
    assert [s["n"] for s in b["screens"]] == ["Login"]
    assert [s["n"] for s in b["structures"]] == ["Own"]
    assert [r["n"] for r in b["roles"]] == ["Admin"]



def test_repeated_context_page_is_a_bad_page_not_incomplete():
    import subprocess, sys, tempfile
    tmp = pathlib.Path(tempfile.mkdtemp())
    def dump(name, rows, **env):
        p = tmp / name; p.write_text(json.dumps({"data": rows, **env})); return str(p)
    info = tmp / "info.json"; info.write_text(json.dumps({"assetKey": APP, "name": "App", "revision": 3}))
    empty = dump("e.json", [], total=0, truncated=False)
    page1 = dump("ent1.json", [_row(f"E{i}", owned=True) for i in range(100)], total=130, truncated=True, next_offset=100)
    r = subprocess.run([sys.executable, str(_SCRIPTS / "build.py"), str(tmp / "cache"), str(tmp / "out.html"), "--app-info", str(info),
                        "--screens", empty, "--actions", empty, "--structures", empty, "--roles", empty,
                        "--entities", page1, page1], capture_output=True, text=True)
    assert r.returncode == 1 and "BAD PAGE" in r.stderr and "repeats" in r.stderr, r.stderr
    assert not (tmp / "cache" / "app-data.json").exists()


def test_cached_mode_refuses_a_bundle_written_by_an_older_build():
    import subprocess, sys, tempfile
    tmp = pathlib.Path(tempfile.mkdtemp()); cache = tmp / "cache"; cache.mkdir()
    old_bundle = {"app": {"key": APP, "name": "App", "type": "WebApplication", "revision": 3, "description": "", "date": ""},
                  "uiFlows": [], "screens": [], "actions": [{"k": "a", "n": "DoLogin", "kind": "function", "desc": "", "pub": False}],
                  "entities": [{"k": "g", "n": "Gradient", "desc": ""}], "inheritedEntities": [], "enums": [], "structures": [],
                  "roles": [], "deps": [], "inheritedCount": 0}          # pre-1.5 shape: no inheritedBuiltinCount
    (cache / "app-data.json").write_text(json.dumps(old_bundle))
    (cache / "meta.json").write_text(json.dumps({"revision": 3, "fetched_at": 0}))
    r = subprocess.run([sys.executable, str(_SCRIPTS / "build.py"), str(cache), str(tmp / "out.html")], capture_output=True, text=True)
    assert r.returncode == 3 and "STALE" in r.stderr, r.stderr
    assert not (tmp / "out.html").exists()


def test_fresh_build_writes_schema_marker():
    b = _bundle(entities=[], actions=[])
    assert "inheritedBuiltinCount" in b and build.BUNDLE_SCHEMA == 3 and b["schema"] == 3


def _ctx_page(rows, offset, next_offset, floor_total=True, pag_total=None):
    """A context_* page as the server emits it. owned_only:false pages carry a floor
    `total` and pagination {limit, offset, nextPageOffset}; owned-only pages carry
    pagination.total."""
    pag = {"limit": 100, "offset": offset, "nextPageOffset": next_offset}
    if pag_total is not None:
        pag["total"] = pag_total
    # Server behaviour (src/models/search.rs fill_cap_contract): while more pages exist the
    # total is offset + rows + 1; on the last page without a real total it is the page's own row count.
    total = pag_total if not floor_total else ((offset + len(rows) + 1) if next_offset is not None else len(rows))
    return {"data": rows, "displayed": len(rows), "total": total, "truncated": next_offset is not None,
            "next_offset": next_offset, "pagination": pag}


def test_context_chain_second_page_alone_is_missing_even_though_total_matches_its_rows():
    import tempfile
    tmp = pathlib.Path(tempfile.mkdtemp())
    p2 = tmp / "p2.json"; p2.write_text(json.dumps(_ctx_page([_row(f"E{i}", owned=True) for i in range(50, 73)], 50, None)))
    assert json.loads(p2.read_text())["total"] == 73 - 50   # the floor total equals the page's own rows
    try:
        build._load_section([p2], "entities"); assert False, "expected TruncatedSection"
    except build.TruncatedSection as exc:
        assert exc.next_offset is None and exc.received == 23 and exc.total_is_floor


def test_context_chain_pages_in_any_order_build_when_contiguous_from_zero():
    import tempfile
    tmp = pathlib.Path(tempfile.mkdtemp())
    p1 = tmp / "p1.json"; p1.write_text(json.dumps(_ctx_page([_row(f"E{i}", owned=True) for i in range(50)], 0, 50)))
    p2 = tmp / "p2.json"; p2.write_text(json.dumps(_ctx_page([_row(f"E{i}", owned=True) for i in range(50, 73)], 50, None)))
    assert len(build._load_section([p2, p1], "entities")["data"]) == 73


def test_context_chain_with_a_gap_is_missing_and_truncated_last_page_asks_for_next_offset():
    import tempfile
    tmp = pathlib.Path(tempfile.mkdtemp())
    p1 = tmp / "p1.json"; p1.write_text(json.dumps(_ctx_page([_row(f"E{i}", owned=True) for i in range(50)], 0, 50)))
    p3 = tmp / "p3.json"; p3.write_text(json.dumps(_ctx_page([_row(f"E{i}", owned=True) for i in range(100, 120)], 100, None)))
    try:
        build._load_section([p1, p3], "entities"); assert False
    except build.TruncatedSection as exc:
        assert exc.next_offset is None                       # gap between 50 and 100
    try:
        build._load_section([p1], "entities"); assert False
    except build.TruncatedSection as exc:
        assert exc.next_offset == 50 and exc.total_is_floor  # fetch the next page


def test_context_chain_tolerates_an_unfaithful_offset_echo_on_later_pages():
    # Only offset 0 has been observed live in pagination.offset; if page 2 echoes 0 too,
    # the pages are taken in the order passed and linked through next_offset.
    import tempfile
    tmp = pathlib.Path(tempfile.mkdtemp())
    p1 = tmp / "p1.json"; p1.write_text(json.dumps(_ctx_page([_row(f"E{i}", owned=True) for i in range(50)], 0, 50)))
    p2 = tmp / "p2.json"; p2.write_text(json.dumps(_ctx_page([_row(f"E{i}", owned=True) for i in range(50, 73)], 0, None)))
    assert len(build._load_section([p1, p2], "entities")["data"]) == 73
    try:
        build._load_section([p1], "entities"); assert False
    except build.TruncatedSection as exc:
        assert exc.next_offset == 50


def test_owned_only_page_with_real_pagination_total_is_not_a_floor():
    import tempfile
    tmp = pathlib.Path(tempfile.mkdtemp())
    p = tmp / "s.json"; p.write_text(json.dumps(_ctx_page([_row(f"S{i}", owned=True) for i in range(11)], 0, None, floor_total=False, pag_total=11)))
    assert len(build._load_section([p], "screens")["data"]) == 11

if __name__ == "__main__":
    fns = [f for n, f in sorted(globals().items()) if n.startswith("test_") and inspect.isfunction(f)]
    for f in fns:
        f(); print(f"PASS {f.__name__}")
    print(f"{len(fns)} tests passed")
