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
    (base / folder / "raw").mkdir(parents=True)
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
    """Every shell command a SKILL.md tells the agent to run is one its
    `allowed-tools` grants (python3, cp, mkdir)."""
    import re
    text = (SKILLS / name / "SKILL.md").read_text(encoding="utf-8")
    allowed = re.search(r"^allowed-tools: (.*)$", text, re.M).group(1)
    assert "Bash(python3 *)" in allowed and "Bash(cp *)" in allowed and "Bash(mkdir *)" in allowed
    for block in re.findall(r"```bash\n(.*?)```", text, re.S):
        for line in block.splitlines():
            cmd = line.strip()
            if not cmd or cmd.startswith("#") or cmd.startswith("--") or cmd.endswith("\\") and not cmd.split()[0].isalpha():
                continue
            first = cmd.split()[0]
            if first.startswith('"') or first.startswith("-"):
                continue                       # a continuation line of the previous command
            assert first in ("python3", "cp", "mkdir"), f"{name}: `{cmd}` is not in allowed-tools"
    for banned in ("rm -rf", "head -c", "foreground `sleep`", "date +%s"):
        assert banned not in text, f"{name}: tells the agent to run {banned!r}"
