#!/usr/bin/env python3
"""Tests for build.py: env-row field names and app_list pagination.

Runnable two ways:
    python3 test_build_pages.py
    pytest tests/skills/tenant-architecture/

Fixtures mirror the server's `env_list` and `app_list` envelopes
(portfolios/v2 environments with `builtinDomain`; app_list capped
at 500 rows per page with `total/displayed/truncated/next_offset`).
"""
import importlib.util
import json
import pathlib
import tempfile

_SCRIPTS = pathlib.Path(__file__).resolve().parents[3] / "claude" / "skills" / "outsystems-tenant-architecture" / "scripts"
_spec = importlib.util.spec_from_file_location("tenant_build", _SCRIPTS / "build.py")
build = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(build)

TENANT = "a0000093-0000-4000-8000-000000000093"

ENVS_V2 = {"results": [
    {"builtinDomain": "acme-dev.example.app", "defaultDomain": "acme-dev.example.app",
     "hosting": "oscloud", "key": "e1", "name": "acme-dev", "order": 0,
     "portfolioKey": "p1", "purpose": "Development", "region": "us-east-1", "status": "Ready"},
    {"builtinDomain": "acme.example.app", "defaultDomain": "acme.example.app",
     "hosting": "oscloud", "key": "e3", "name": "acme", "order": 1000,
     "portfolioKey": "p1", "purpose": "Production", "region": "us-east-1", "status": "Ready"},
]}

ENVS_LEGACY = {"results": [
    {"key": "e1", "name": "acme-dev", "purpose": "Development",
     "hostname": "acme-dev.example.app", "region": "us-east-1"},
]}


def _asset(i: int) -> dict:
    return {"assetKey": f"k{i:04d}", "name": f"Asset {i}", "assetType": "WebApplication",
            "revision": i % 7 + 1, "revisionDateTime": "2026-09-01T00:00:00Z", "isExternal": False}


def _page(rows, total, offset):
    truncated = offset + len(rows) < total
    return {"results": rows, "total": total, "displayed": len(rows),
            "truncated": truncated, "next_offset": (offset + len(rows)) if truncated else None,
            "pagination_hint": f"Showing {len(rows)} of {total}."}


def _run(envs, pages):
    """Run main() against a temp cache; returns (exit_code, cache_dir)."""
    tmp = pathlib.Path(tempfile.mkdtemp())
    cache = tmp / "cache"; cache.mkdir()
    (cache / "envs-raw.json").write_text(json.dumps(envs), encoding="utf-8")
    page_paths = []
    for i, p in enumerate(pages, 1):
        path = tmp / f"apps-page-{i}.json"
        path.write_text(json.dumps(p), encoding="utf-8")
        page_paths.append(str(path))
    code = build.main(["build.py", str(cache), str(tmp / "out.html"),
                       "--tenant-id", TENANT, "--apps", *page_paths])
    return code, cache


def _part(cache, key):
    return json.loads((cache / "tenant-data.json").read_text())[key]


def test_env_rows_use_builtin_domain():
    code, cache = _run(ENVS_V2, [_page([_asset(i) for i in range(3)], 3, 0)])
    assert code == 0
    envs = _part(cache, "envs")
    assert [e["host"] for e in envs] == ["acme-dev.example.app", "acme.example.app"]
    tenant = _part(cache, "tenant")
    assert tenant["realm"] == "acme" and tenant["region"] == "us-east-1" and tenant["hosting"] == "oscloud"


def test_legacy_hostname_rows_still_work():
    code, cache = _run(ENVS_LEGACY, [_page([_asset(0)], 1, 0)])
    assert code == 0
    assert _part(cache, "envs")[0]["host"] == "acme-dev.example.app"


def test_truncated_single_page_is_refused_and_writes_nothing():
    # 515 assets, one page of 500: the shape of a tenant over the cap.
    code, cache = _run(ENVS_V2, [_page([_asset(i) for i in range(500)], 515, 0)])
    assert code == 3
    assert not (cache / "tenant-data.json").exists()
    assert not (cache / "meta.json").exists()


def test_two_pages_merge_and_meta_total_is_the_server_total():
    p1 = _page([_asset(i) for i in range(500)], 515, 0)
    p2 = _page([_asset(i) for i in range(500, 515)], 515, 500)
    code, cache = _run(ENVS_V2, [p1, p2])
    assert code == 0
    assets = _part(cache, "assets")
    meta = json.loads((cache / "meta.json").read_text())
    assert len(assets) == 515
    assert meta["total"] == 515 and meta["count"] == 515  # what the limit:1 probe reports


def test_overlapping_pages_are_deduplicated():
    p1 = _page([_asset(i) for i in range(10)], 12, 0)
    p1["truncated"] = True; p1["next_offset"] = 10
    p2 = _page([_asset(i) for i in range(8, 12)], 12, 8)  # overlaps 8, 9
    code, cache = _run(ENVS_V2, [p1, p2])
    assert code == 0
    assert len(_part(cache, "assets")) == 12


def test_envelope_without_total_falls_back_to_row_count():
    code, cache = _run(ENVS_V2, [{"results": [_asset(i) for i in range(4)]}])
    assert code == 0
    assert json.loads((cache / "meta.json").read_text())["total"] == 4


def test_only_the_second_page_is_refused_even_though_it_is_not_truncated():
    # The agent forgot page 1 after the exit-3 loop: 15 rows, truncated false, total 515.
    p2 = _page([_asset(i) for i in range(500, 515)], 515, 500)
    assert p2["truncated"] is False
    code, cache = _run(ENVS_V2, [p2])
    assert code == 3
    assert not (cache / "meta.json").exists()


def test_pages_out_of_order_still_build_when_every_asset_is_present():
    p1 = _page([_asset(i) for i in range(500)], 515, 0)
    p2 = _page([_asset(i) for i in range(500, 515)], 515, 500)
    code, cache = _run(ENVS_V2, [p2, p1])
    assert code == 0
    assert json.loads((cache / "meta.json").read_text()) ["count"] == 515


def test_repeated_page_is_a_bad_page():
    p1 = _page([_asset(i) for i in range(500)], 515, 0)
    code, cache = _run(ENVS_V2, [p1, p1])
    assert code == 1
    assert not (cache / "meta.json").exists()


def test_clamped_page_saved_without_envelope_is_a_bad_page():
    code, cache = _run(ENVS_V2, [{"results": [_asset(i) for i in range(500)]}])
    assert code == 1
    assert not (cache / "meta.json").exists()


def test_missing_tenant_id_is_a_usage_error():
    tmp = pathlib.Path(tempfile.mkdtemp())
    assert build.main(["build.py", str(tmp), str(tmp / "o.html"), "--apps", str(tmp / "p.json")]) == 2


def test_a_page_file_passed_as_the_tenant_id_is_a_usage_error():
    tmp = pathlib.Path(tempfile.mkdtemp()); cache = tmp / "cache"; cache.mkdir()
    (cache / "envs-raw.json").write_text(json.dumps(ENVS_V2))
    p1 = tmp / "p1.json"; p1.write_text(json.dumps(_page([_asset(i) for i in range(3)], 3, 0)))
    assert build.main(["build.py", str(cache), str(tmp / "o.html"),
                       "--apps", str(p1), "--tenant-id", str(p1)]) == 2
    assert not (cache / "meta.json").exists()


def test_the_1_6_positional_form_is_a_usage_error_not_a_misparse():
    # build.py <cache> <out> <page> <page> <tenant-id>: pages are no longer positional.
    tmp = pathlib.Path(tempfile.mkdtemp()); cache = tmp / "cache"; cache.mkdir()
    (cache / "envs-raw.json").write_text(json.dumps(ENVS_V2))
    p1 = tmp / "p1.json"; p1.write_text(json.dumps(_page([_asset(i) for i in range(500)], 515, 0)))
    p2 = tmp / "p2.json"; p2.write_text(json.dumps(_page([_asset(i) for i in range(500, 515)], 515, 500)))
    assert build.main(["build.py", str(cache), str(tmp / "o.html"), str(p1), str(p2), TENANT]) == 2
    assert not (cache / "meta.json").exists()


if __name__ == "__main__":
    import inspect
    fns = [f for n, f in sorted(globals().items()) if n.startswith("test_") and inspect.isfunction(f)]
    for f in fns:
        f(); print(f"PASS {f.__name__}")
    print(f"{len(fns)} tests passed")
