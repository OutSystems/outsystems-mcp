"""`build.py --cache-dir`: every skill resolves its own cache folder, so the
skill docs never spell out a home-folder path."""
import pathlib
import subprocess
import sys

import pytest

SKILLS = pathlib.Path(__file__).resolve().parents[2] / "claude" / "skills"
NAMES = ["outsystems-tenant-architecture", "outsystems-app-architecture",
         "outsystems-dependency-impact"]


def _run(name, *args, home):
    env = {"HOME": str(home), "USERPROFILE": str(home), "PATH": "/usr/bin:/bin"}
    return subprocess.run([sys.executable, str(SKILLS / name / "scripts" / "build.py"),
                           "--cache-dir", *args], capture_output=True, text=True, env=env)


@pytest.mark.parametrize("name", NAMES)
def test_cache_dir_is_created_per_skill_and_id(name, tmp_path):
    p = _run(name, "a0000001-0000-4000-8000-000000000001", home=tmp_path)
    assert p.returncode == 0, p.stderr
    path = pathlib.Path(p.stdout.strip())
    assert path == tmp_path / ".cache" / "outsystems-skills" / name / "a0000001-0000-4000-8000-000000000001"
    assert path.is_dir()


@pytest.mark.parametrize("name", NAMES)
def test_sibling_skill_folder_is_printed_not_created(name, tmp_path):
    p = _run(name, "t1", "--skill", "outsystems-tenant-architecture", home=tmp_path)
    assert p.returncode == 0, p.stderr
    path = pathlib.Path(p.stdout.strip())
    assert path.name == "t1" and path.parent.name == "outsystems-tenant-architecture"
    if name != "outsystems-tenant-architecture":
        assert not path.exists()


@pytest.mark.parametrize("name", NAMES)
@pytest.mark.parametrize("bad", [["../etc"], ["a/b"], [""], ["x", "--skill", "../../tmp"], []])
def test_unsafe_ids_are_refused(name, bad, tmp_path):
    p = _run(name, *bad, home=tmp_path)
    assert p.returncode == 2
    assert not (tmp_path / ".cache").exists()


DEP = "outsystems-dependency-impact"


@pytest.mark.parametrize("folder", ["impact", "impact-named"])
def test_dependency_impact_clears_only_its_record_folders(folder, tmp_path):
    """`--clear` replaces the shell `rm -rf` the skill's allowed tools do not grant."""
    p = _run(DEP, "t1", home=tmp_path)
    base = pathlib.Path(p.stdout.strip())
    (base / folder / "raw").mkdir(parents=True, exist_ok=True)
    (base / folder / "old.json").write_text("{}")
    (base / "targets.json").write_text("[]")            # a sibling the clear must keep
    p = _run(DEP, "t1", "--clear", folder, home=tmp_path)
    assert p.returncode == 0, p.stderr
    cleared = pathlib.Path(p.stdout.strip())
    assert cleared == base / folder
    assert sorted(x.name for x in cleared.iterdir()) == ["raw"]
    assert (base / "targets.json").exists()


@pytest.mark.parametrize("bad", ["..", "raw", "", "impact/../.."])
def test_dependency_impact_refuses_any_other_folder(bad, tmp_path):
    p = _run(DEP, "t1", "--clear", bad, home=tmp_path)
    assert p.returncode == 2


def test_dependency_impact_waits_within_bounds(tmp_path):
    script = str(SKILLS / DEP / "scripts" / "build.py")
    ok = subprocess.run([sys.executable, script, "--wait", "1"], capture_output=True, text=True)
    assert ok.returncode == 0 and ok.stdout.strip() == "waited 1s"
    for bad in ("0", "61", "x", ""):
        p = subprocess.run([sys.executable, script, "--wait", bad], capture_output=True, text=True)
        assert p.returncode == 2, bad


@pytest.mark.parametrize("name", NAMES)
def test_skill_docs_use_only_their_allowed_shell_commands(name):
    """`allowed-tools` grants only the skill's own build.py (unquoted and
    quoted path), never an interpreter or a shell command with a wildcard,
    and every shell command in the SKILL.md is that script."""
    import re
    text = (SKILLS / name / "SKILL.md").read_text(encoding="utf-8")
    allowed = re.search(r"^allowed-tools: (.*)$", text, re.M).group(1)
    script = f"${{CLAUDE_PLUGIN_ROOT}}/skills/{name}/scripts/build.py"
    bash = re.findall(r"Bash\(([^)]*)\)", allowed)
    assert bash == [f"python3 {script} *", f'python3 "{script}" *'], bash
    for block in re.findall(r"```bash\n(.*?)```", text, re.S):
        for line in block.splitlines():
            cmd = line.strip()
            if not cmd or cmd.startswith("#") or cmd.startswith("--") or cmd.startswith('"'):
                continue                       # comments and continuation lines
            assert cmd.startswith('python3 "<skill-folder>/scripts/build.py"'), f"{name}: `{cmd}`"
    for banned in ("python3 -c", "rm -rf", "head -c", "foreground `sleep`", "date +%s", "`cp`", "mkdir -p"):
        assert banned not in text, f"{name}: tells the agent to run {banned!r}"


@pytest.mark.parametrize("name", NAMES)
def test_cache_age_and_peek_replace_inline_python(name, tmp_path):
    script = str(SKILLS / name / "scripts" / "build.py")
    import json, time
    (tmp_path / "meta.json").write_text(json.dumps({"fetched_at": int(time.time()) - 90}))
    p = subprocess.run([sys.executable, script, "--cache-age", str(tmp_path)], capture_output=True, text=True)
    assert p.returncode == 0 and "age_s=" in p.stdout
    assert 89 <= int(p.stdout.split("age_s=")[1]) <= 120
    p = subprocess.run([sys.executable, script, "--cache-age", str(tmp_path / "none")], capture_output=True, text=True)
    assert p.returncode == 0 and "no cache" in p.stdout
    (tmp_path / "page.json").write_text("x" * 3000)
    p = subprocess.run([sys.executable, script, "--peek", str(tmp_path / "page.json"), "10"], capture_output=True, text=True)
    assert p.returncode == 0 and p.stdout.strip() == "x" * 10
    for bad in (["--peek"], ["--peek", "f", "0"], ["--peek", "f", "999999"], ["--cache-age"]):
        assert subprocess.run([sys.executable, script, *bad], capture_output=True, text=True).returncode == 2


@pytest.mark.parametrize("name", ["outsystems-app-architecture", "outsystems-dependency-impact"])
def test_copy_writes_only_inside_the_skill_cache(name, tmp_path):
    env = {"HOME": str(tmp_path), "USERPROFILE": str(tmp_path), "PATH": "/usr/bin:/bin"}
    script = str(SKILLS / name / "scripts" / "build.py")
    src = tmp_path / "saved.txt"; src.write_text('{"data": []}')
    inside = tmp_path / ".cache" / "outsystems-skills" / name / "k1" / "screens-raw.json"
    p = subprocess.run([sys.executable, script, "--copy", str(src), str(inside)], capture_output=True, text=True, env=env)
    assert p.returncode == 0, p.stderr
    assert inside.read_text() == '{"data": []}'
    for outside in (tmp_path / "evil.json", tmp_path / ".cache" / "outsystems-skills" / "other" / "x.json",
                    inside.parent / ".." / ".." / ".." / "x.json"):
        p = subprocess.run([sys.executable, script, "--copy", str(src), str(outside)], capture_output=True, text=True, env=env)
        assert p.returncode == 2 and not pathlib.Path(outside).exists(), outside


def test_dependency_impact_cache_dir_creates_the_record_folder(tmp_path):
    p = _run(DEP, "t2", home=tmp_path)
    assert (pathlib.Path(p.stdout.strip()) / "impact" / "raw").is_dir()
