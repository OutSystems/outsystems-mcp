#!/usr/bin/env python3
"""Unit tests for build.py's app_refs dependency parser (_build_deps).

Runnable two ways:
    python3 test_build_deps.py          # standalone, no deps
    pytest tests/skills/app-architecture/   # discovered as test_* functions

Fixtures are app_refs payloads in the server's shape (schemaVersion 2,
source context-service; schemaVersion 3, source stored-xre; names and keys
invented) plus the legacy and oml-fallback shapes the parser must stay
tolerant of.
"""
from __future__ import annotations

import importlib.util
import json
import pathlib
import tempfile

# Load build.py by path so the test runs regardless of cwd / packaging.
_SCRIPTS = pathlib.Path(__file__).resolve().parents[3] / "claude" / "skills" / "outsystems-app-architecture" / "scripts"
_spec = importlib.util.spec_from_file_location("arch_build", _SCRIPTS / "build.py")
build = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(build)


def _deps_for(payload: dict) -> list[dict]:
    """Write payload to a temp file and run _build_deps against it."""
    with tempfile.NamedTemporaryFile(
        "w", suffix=".json", delete=False, encoding="utf-8"
    ) as fh:
        json.dump(payload, fh)
        path = pathlib.Path(fh.name)
    try:
        return build._build_deps(path, payload.get("assetKey", "app"))
    finally:
        path.unlink(missing_ok=True)


# app_refs response for an example app, WebPortal (a00000f5).
LIVE_CONTEXT_SERVICE = {
    "assetKey": "a00000f5-0000-4000-8000-0000000000f5",
    "schemaVersion": 2,
    "source": "context-service",
    "references": [
        {"kinds": ["entities"], "producerAssetKey": "a000004f-0000-4000-8000-00000000004f", "producerAssetName": "OutSystemsCharts"},
        {"kinds": ["entities"], "producerAssetKey": "a0000061-0000-4000-8000-000000000061", "producerAssetName": "(System)"},
        {"kinds": ["entities"], "producerAssetKey": "a0000062-0000-4000-8000-000000000062", "producerAssetName": "OutSystemsSampleData"},
        {"kinds": ["entities"], "producerAssetKey": "a000007c-0000-4000-8000-00000000007c", "producerAssetName": "UltimatePDF"},
        {"kinds": ["entities"], "producerAssetKey": "a00000ba-0000-4000-8000-0000000000ba", "producerAssetName": "OutSystemsUI"},
        {"kinds": ["entities"], "producerAssetKey": "a00000f7-0000-4000-8000-0000000000f7", "producerAssetName": "WebPortalTheme"},
        {"kinds": ["entities"], "producerAssetKey": "a0000125-0000-4000-8000-000000000125", "producerAssetName": "OutSystemsDataGrid"},
    ],
}


def test_live_context_service_shape_yields_nonbuiltin_deps():
    """The headline bug: the server's producerAssetName/producerAssetKey/kinds shape
    must NOT be dropped. WebPortal has 3 non-builtin refs after filtering."""
    deps = _deps_for(LIVE_CONTEXT_SERVICE)
    names = sorted(d["n"] for d in deps)
    assert names == ["OutSystemsDataGrid", "UltimatePDF", "WebPortalTheme"], names
    by_name = {d["n"]: d for d in deps}
    pdf = by_name["UltimatePDF"]
    assert pdf["k"] == "a000007c-0000-4000-8000-00000000007c", pdf
    assert pdf["kind"] == "entities", pdf           # kinds[] mapped to scalar
    assert pdf["cat"] == "Library", pdf             # entity-import → Library
    # builtins filtered out
    assert "(System)" not in by_name and "OutSystemsUI" not in by_name


def test_legacy_shape_still_parses_and_categorizes_aimodel():
    """Legacy {moduleKey,name,kind,revision} must still work, including the
    AIModelConnection → AIModel categorization."""
    deps = _deps_for({
        "assetKey": "legacy",
        "references": [
            {"moduleKey": "mk-ai", "name": "MyGPT", "kind": "AIModelConnection", "revision": 4},
            {"moduleKey": "mk-lib", "name": "SomeLib", "kind": "eSpace", "revision": 2},
            {"moduleKey": "mk-sys", "name": "(System)", "kind": "eSpace", "revision": 1},
        ],
    })
    by_name = {d["n"]: d for d in deps}
    assert set(by_name) == {"MyGPT", "SomeLib"}
    assert by_name["MyGPT"]["cat"] == "AIModel"
    assert by_name["MyGPT"]["kind"] == "AIModelConnection"
    assert by_name["MyGPT"]["rev"] == "4"
    assert by_name["MyGPT"]["k"] == "mk-ai"
    assert by_name["SomeLib"]["cat"] == "Library"


def test_oml_fallback_importedkind_shape():
    """schemaVersion 2 / oml-fallback uses producerAsset* + importedKind."""
    deps = _deps_for({
        "assetKey": "oml",
        "schemaVersion": 2,
        "source": "oml-fallback",
        "references": [
            {"producerAssetKey": "pk1", "producerAssetName": "SomeLib", "importedKind": "eSpace"},
        ],
    })
    assert len(deps) == 1
    assert deps[0]["n"] == "SomeLib"
    assert deps[0]["k"] == "pk1"
    assert deps[0]["kind"] == "eSpace"
    assert deps[0]["cat"] == "Library"


def test_stored_xre_importedkind_shape():
    """schemaVersion 3 / stored-xre uses producerAsset* + importedKind, reports
    indexedKinds as [], and names its revision when it is older than the newest."""
    payload = {
        "schemaVersion": 3,
        "source": "stored-xre",
        "assetKey": "stored",
        "degraded": False,
        "references": [
            {"producerAssetKey": "pk1", "producerAssetName": "SomeLib", "importedKind": "Extension"},
        ],
        "indexedKinds": [],
        "fallbackReason": "not_indexed",
        "revision": 7,
        "latestRevision": 8,
    }
    deps = _deps_for(payload)
    assert len(deps) == 1
    assert deps[0]["n"] == "SomeLib"
    assert deps[0]["k"] == "pk1"
    assert deps[0]["kind"] == "Extension"
    assert deps[0]["cat"] == "Library"
    assert build._refs_coverage(payload) == {"source": "stored-xre", "indexedKinds": [], "coverage": None}
    assert "origin" not in deps[0]


def test_stored_xre_rows_keep_their_declared_origin():
    """schemaVersion 3 / stored-xre from a server that marks every row
    `origin: declared`; a row with no kind carries `origin` alone."""
    payload = {
        "schemaVersion": 3,
        "source": "stored-xre",
        "assetKey": "stored",
        "degraded": False,
        "references": [
            {"producerAssetKey": "pk1", "producerAssetName": "SomeLib", "importedKind": "Extension",
             "origin": "declared"},
            {"producerAssetKey": "pk2", "producerAssetName": "OtherLib", "origin": "declared"},
        ],
        "indexedKinds": [],
        "fallbackReason": "not_indexed",
    }
    deps = _deps_for(payload)
    assert [(d["n"], d["kind"], d["origin"]) for d in deps] == [
        ("SomeLib", "Extension", "declared"), ("OtherLib", "", "declared")]
    assert build._refs_coverage(payload) == {"source": "stored-xre", "indexedKinds": [], "coverage": None}


# A context-service answer where the server added the stored graph's declared
# modules because indexedKinds lacks actions, blocks and structures.
MERGED = {
    "assetKey": "a00000f5-0000-4000-8000-0000000000f5",
    "schemaVersion": 2,
    "source": "context-service",
    "degraded": False,
    "indexedKinds": ["entities"],
    "references": [
        {"kinds": ["entities"], "producerAssetKey": "a0000101-0000-4000-8000-000000000101",
         "producerAssetName": "SharedData", "origin": "indexed"},
        {"importedKind": "Extension", "producerAssetKey": "a0000102-0000-4000-8000-000000000102",
         "producerAssetName": "FileTools", "origin": "declared"},
        {"producerAssetKey": "a0000103-0000-4000-8000-000000000103",
         "producerAssetName": "HttpHelpers", "origin": "declared"},
    ],
    "coverage": {"declared": "merged", "revision": 5, "latestRevision": 6,
                 "revisionNote": {"text": "Read from revision 5; the latest is 6."},
                 "note": "The stored app graph adds the modules the app declares."},
}


def test_merged_context_service_answer_keeps_origin_and_coverage():
    deps = _deps_for(MERGED)
    assert [(d["n"], d["kind"], d["origin"]) for d in deps] == [
        ("SharedData", "entities", "indexed"), ("FileTools", "Extension", "declared"),
        ("HttpHelpers", "", "declared")]
    assert all(d["cat"] == "Library" for d in deps)
    assert build._refs_coverage(MERGED) == {
        "source": "context-service", "indexedKinds": ["entities"],
        "coverage": {"declared": "merged", "revision": 5, "latestRevision": 6}}


def test_unavailable_coverage_keeps_its_reason():
    payload = dict(MERGED, references=MERGED["references"][:1],
                   coverage={"declared": "unavailable", "reason": "supplement_late_start", "note": "..."})
    assert build._refs_coverage(payload)["coverage"] == {
        "declared": "unavailable", "reason": "supplement_late_start"}


def test_context_service_answer_without_origin_or_coverage_is_read_as_before():
    """schemaVersion 2 from a server that sends neither `origin` nor `coverage`."""
    payload = {"schemaVersion": 2, "source": "context-service", "indexedKinds": ["entities"],
               "references": [{"kinds": ["entities"], "producerAssetKey": "k1", "producerAssetName": "SharedData"}]}
    deps = _deps_for(payload)
    assert deps == [{"k": "k1", "n": "SharedData", "kind": "entities", "cat": "Library", "rev": ""}]
    assert build._refs_coverage(payload) == {
        "source": "context-service", "indexedKinds": ["entities"], "coverage": None}


def test_unknown_origin_and_malformed_coverage_fields_are_dropped():
    payload = dict(MERGED, references=[dict(MERGED["references"][0], origin="guessed")],
                   coverage={"declared": "merged", "revision": True, "latestRevision": "6", "reason": 3})
    assert "origin" not in _deps_for(payload)[0]
    assert build._refs_coverage(payload)["coverage"] == {"declared": "merged"}
    assert build._refs_coverage(dict(MERGED, coverage="merged"))["coverage"] is None
    assert build._refs_coverage(dict(MERGED, coverage={"declared": None}))["coverage"] is None


def test_builtins_only_yields_empty():
    deps = _deps_for({
        "assetKey": "b",
        "references": [
            {"kinds": ["entities"], "producerAssetKey": "k1", "producerAssetName": "(System)"},
            {"kinds": ["entities"], "producerAssetKey": "k2", "producerAssetName": "OutSystemsUI"},
        ],
    })
    assert deps == []


def test_failed_scan_yields_empty():
    deps = _deps_for({"assetKey": "f", "failed": True})
    assert deps == []


def _run():
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in fns:
        fn()
        print(f"PASS {fn.__name__}")
    print(f"\n{len(fns)} passed")


if __name__ == "__main__":
    _run()
