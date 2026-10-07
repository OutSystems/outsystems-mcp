"""The bundled skills ship once per harness folder (Claude, Cursor, Kiro).
`claude/skills/` is the source; the other two must be byte-identical copies,
so a fix can never land on one harness only. To sync after an edit:

    for s in tenant-architecture app-architecture dependency-impact design-to-app; do
      for dst in cursor/skills kiro/outsystems/skills; do
        rm -rf "$dst/outsystems-$s" && cp -r "claude/skills/outsystems-$s" "$dst/"
      done
    done
"""
import pathlib

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
SOURCE = REPO / "claude" / "skills"
COPIES = [REPO / "cursor" / "skills", REPO / "kiro" / "outsystems" / "skills"]
SKILLS = ["outsystems-tenant-architecture", "outsystems-app-architecture",
          "outsystems-dependency-impact", "outsystems-design-to-app"]


def _files(root: pathlib.Path):
    return sorted(p.relative_to(root) for p in root.rglob("*")
                  if p.is_file() and "__pycache__" not in p.parts)


@pytest.mark.parametrize("copy_root", COPIES, ids=lambda p: str(p.relative_to(REPO)))
@pytest.mark.parametrize("skill", SKILLS)
def test_copy_is_byte_identical(skill, copy_root):
    src, dst = SOURCE / skill, copy_root / skill
    assert dst.is_dir(), f"{dst.relative_to(REPO)} is missing"
    assert _files(src) == _files(dst), f"file lists differ for {skill}"
    for rel in _files(src):
        assert (src / rel).read_bytes() == (dst / rel).read_bytes(), \
            f"{dst.relative_to(REPO) / rel} differs from {src.relative_to(REPO) / rel}"
