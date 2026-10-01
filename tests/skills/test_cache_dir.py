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
