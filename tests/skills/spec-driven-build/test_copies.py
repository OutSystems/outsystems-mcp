"""outsystems-spec-driven-build ships once per harness folder (Claude, Cursor,
Kiro). `claude/skills/` is the source; the other two must be byte-identical.
To sync after an edit:

    for dst in cursor/skills kiro/outsystems/skills; do
      rm -rf "$dst/outsystems-spec-driven-build" && cp -R claude/skills/outsystems-spec-driven-build "$dst/"
    done
"""
import pathlib

import pytest

REPO = pathlib.Path(__file__).resolve().parents[3]
NAME = "outsystems-spec-driven-build"
SOURCE = REPO / "claude" / "skills" / NAME
COPIES = [REPO / "cursor" / "skills" / NAME, REPO / "kiro" / "outsystems" / "skills" / NAME]


def _files(root):
    return sorted(p.relative_to(root) for p in root.rglob("*")
                  if p.is_file() and "__pycache__" not in p.parts)


@pytest.mark.parametrize("copy", COPIES, ids=lambda p: str(p.relative_to(REPO)))
def test_copy_is_byte_identical(copy):
    assert copy.is_dir(), f"{copy.relative_to(REPO)} is missing"
    assert _files(SOURCE) == _files(copy)
    for rel in _files(SOURCE):
        assert (SOURCE / rel).read_bytes() == (copy / rel).read_bytes(), f"{copy.relative_to(REPO) / rel} differs"
