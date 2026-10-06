"""`outsystems-spec-driven-build/scripts/build.py`: the spec check, the interview
assembly, the Mentor prompt and the build report. Runs offline: the script
never calls the MCP."""
import json
import pathlib
import re
import subprocess
import sys

import pytest

SKILL = pathlib.Path(__file__).resolve().parents[3] / "claude" / "skills" / "outsystems-spec-driven-build"
BUILD = SKILL / "scripts" / "build.py"
EXAMPLE = SKILL / "templates" / "example-spec.md"
TEMPLATE = SKILL / "templates" / "spec-template.md"


def run(*args):
    return subprocess.run([sys.executable, str(BUILD), *map(str, args)],
                          capture_output=True, text=True)


def validate(path):
    return run("validate-spec", "--spec", path)


def write_spec(tmp_path, text, name="spec.md"):
    p = tmp_path / name
    p.write_text(text, encoding="utf-8")
    return p


def example():
    return EXAMPLE.read_text(encoding="utf-8")


# ------------------------------------------------------------------ validate-spec

def test_example_spec_passes_without_warnings():
    p = validate(EXAMPLE)
    assert p.returncode == 0, p.stdout
    assert "OK: 0 warning(s)" in p.stdout


def test_blank_template_fails_on_placeholders():
    p = validate(TEMPLATE)
    assert p.returncode == 1
    assert "unfilled template placeholders" in p.stdout
    assert "<EntityName>" in p.stdout


def test_screen_without_role_fails(tmp_path):
    text = re.sub(r"(\| Dashboard \|[^|]*\|)[^|]*\|", r"\1 |", example())
    p = validate(write_spec(tmp_path, text))
    assert p.returncode == 1
    assert "screen 'Dashboard' has no role" in p.stdout


def test_screen_with_undefined_role_fails(tmp_path):
    text = example().replace(
        "| EngineerList | View all team members + their workload | EngineeringManager |",
        "| EngineerList | View all team members + their workload | Admin |")
    p = validate(write_spec(tmp_path, text))
    assert p.returncode == 1
    assert "'EngineerList' names role(s) not defined" in p.stdout
    assert "Admin" in p.stdout


def test_builtin_roles_and_role_notes_are_accepted():
    # The example uses Anonymous, All authenticated and "Engineer (own tasks edit, all view)".
    assert validate(EXAMPLE).returncode == 0


@pytest.mark.parametrize("num,title", [("1", "Overview"), ("2", "Roles"), ("3", "Data model"),
                                       ("4", "Screens + RBAC"), ("8", "Out of scope")])
def test_missing_required_section_fails(tmp_path, num, title):
    text = example().replace(f"## {num}. {title}", f"## {num}x. {title}", 1)
    p = validate(write_spec(tmp_path, text))
    assert p.returncode == 1
    assert f"## {num}. {title}: missing" in p.stdout


def test_no_relationships_warns(tmp_path):
    text = example()
    text = re.sub(r"\(Long FK → [^)]*\)", "(Long Integer)", text)
    text = text.replace("FK to Engineer (twice — creator + assignee)", "—")
    text = text.replace("FK to Task + Engineer", "—")
    text = text.replace("FK to the ODC User who signs in (UserId)", "—")
    p = validate(write_spec(tmp_path, text))
    assert p.returncode == 0
    assert "no relationships stated" in p.stdout


def test_missing_integrations_warns(tmp_path):
    text = re.sub(r"## 6\. Integrations.*?(?=## 7\.)", "", example(), flags=re.S)
    p = validate(write_spec(tmp_path, text))
    assert p.returncode == 0
    assert "## 6. Integrations: missing or empty" in p.stdout


def test_missing_target_app_warns(tmp_path):
    text = example().replace("**Target app:** TaskTracker (new)", "")
    p = validate(write_spec(tmp_path, text))
    assert p.returncode == 0
    assert "no `**Target app:**` line" in p.stdout


# ------------------------------------------------------------------ assemble-spec

ANSWERS = {
    "purpose": "LeaveDesk. Employees request time off and managers approve it.",
    "app_shell": "LeaveDesk (new)",
    "style_direction": "Apply OutSystems UI defaults (recommended for v1)",
    "roles": "Employee: requests leave, sees own requests\nManager: approves team requests",
    "entities": "Employee: Name (Text 100), ManagerId (FK Employee)\n"
                "LeaveRequest: EmployeeId (FK Employee), StartDate (Date), Status (LeaveStatus)",
    "enums": "LeaveStatus: Pending, Approved, Rejected",
    "screens_and_rbac": "MyRequests | list own requests | Employee\nApprovals | pending requests | Manager",
    "integrations": "None",
    "out_of_scope": "No email notifications, no calendar sync, no public endpoints.",
}


def assemble(tmp_path, answers):
    a = tmp_path / "answers.json"
    a.write_text(json.dumps(answers), encoding="utf-8")
    out = tmp_path / "spec.md"
    p = run("assemble-spec", "--answers", a, "--output", out)
    assert p.returncode == 0, p.stderr
    return out


def test_assembled_spec_follows_the_template_and_passes(tmp_path):
    out = assemble(tmp_path, ANSWERS)
    text = out.read_text(encoding="utf-8")
    for expected in ("**Purpose:**", "**Target app:** LeaveDesk (new)", "**Style direction:**",
                     "- **Employee**:", "### Entities", "### Static enums",
                     "| Screen | Purpose | Accessible by (roles) |", "| Approvals | pending requests | Manager |"):
        assert expected in text
    p = validate(out)
    assert p.returncode == 0, p.stdout
    assert "OK: 0 warning(s)" in p.stdout


def test_assembled_spec_with_missing_required_answer_fails(tmp_path):
    answers = dict(ANSWERS)
    del answers["out_of_scope"]
    out = assemble(tmp_path, answers)
    assert "(NOT PROVIDED — required)" in out.read_text(encoding="utf-8")
    p = validate(out)
    assert p.returncode == 1
    assert "## 8. Out of scope" in p.stdout


def test_screen_line_without_roles_fails_after_assembly(tmp_path):
    answers = dict(ANSWERS, screens_and_rbac="MyRequests | list own requests")
    p = validate(assemble(tmp_path, answers))
    assert p.returncode == 1
    assert "screen 'MyRequests' has no role" in p.stdout


def test_title_comes_from_the_app_name_not_the_purpose(tmp_path):
    answers = dict(ANSWERS, app_shell="LeaveDesk (new)",
                   purpose="LeaveDesk is a small app where employees request time off and managers approve it.")
    text = assemble(tmp_path, answers).read_text(encoding="utf-8")
    assert text.splitlines()[0] == "# App Spec: LeaveDesk"


def test_a_sentence_in_the_roles_answer_is_not_a_role(tmp_path):
    answers = dict(ANSWERS, roles=ANSWERS["roles"] + "\nNo anonymous access anywhere: every screen requires login.")
    out = assemble(tmp_path, answers)
    text = out.read_text(encoding="utf-8")
    assert "- **No anonymous access anywhere**" not in text
    assert "- No anonymous access anywhere: every screen requires login." in text
    assert validate(out).returncode == 0


# ------------------------------------------------------------------ build-prompt

def test_prompt_carries_spec_and_guardrails():
    p = run("build-prompt", "--spec", EXAMPLE)
    assert p.returncode == 0, p.stderr
    out = p.stdout
    assert "# App Spec: TaskTracker" in out
    assert "Respect the role-per-screen assignments" in out
    assert "Do NOT publish the app in this turn" in out
    assert "At the end, summarize" in out


def test_seed_guardrail_makes_the_seed_run():
    out = run("build-prompt", "--spec", EXAMPLE).stdout
    assert "make it run on its own" in out
    assert "Timer that\n   runs when the app is published" in out


def test_example_links_engineer_to_the_signed_in_user():
    text = example()
    assert "UserId (User Identifier" in text
    assert "GetUserId()" in text


def test_prompt_has_no_design_to_app_rules():
    out = run("build-prompt", "--spec", EXAMPLE).stdout
    for gone in ("<svg", "svg-icon-baking", "theme-collisions", "tablerecords-seeding",
                 "ListAppend", "main-content", "design-to-app/references"):
        assert gone not in out


def test_prompt_no_longer_takes_an_app_key():
    p = run("build-prompt", "--spec", EXAMPLE, "--app-key", "a0000001")
    assert p.returncode == 2
    assert "unrecognized arguments" in p.stderr


# ------------------------------------------------------------------ render-report

RESULT = {"status": "succeeded",
          "result": {"summary": "Created 3 entities, 7 screens, 2 roles."},
          "events": []}


def test_report_has_summary_and_spec_and_no_handoff(tmp_path):
    res = tmp_path / "result.json"
    res.write_text(json.dumps(RESULT), encoding="utf-8")
    out = tmp_path / "report.md"
    p = run("render-report", "--spec", EXAMPLE, "--result", res, "--output", out,
            "--app-key", "a0000001", "--run-id", "run-1")
    assert p.returncode == 0, p.stderr
    text = out.read_text(encoding="utf-8")
    assert "Created 3 entities, 7 screens, 2 roles." in text
    assert "# App Spec: TaskTracker" in text
    assert "`a0000001`" in text and "`run-1`" in text
    assert "Next steps" not in text


# ------------------------------------------------------------------ content of the shipped folder

FORBIDDEN = [
    r"app_create", r"allowed-tools", r"mentor-copilot", r"deploy-preview", r"app-documentation",
    r"mentor-polling-behavior", r"\bCONVENTIONS\b", r"~/", r"\.claude/cache", r"\$\d",
    r"portable-agent-skills", r"\bSFTDD\b", r"\b20\d\d-\d\d-\d\d\b", r"FIELD-FEEDBACK",
    r"tenant_not_allowed", r"\bcancelling\b",
]


def shipped_files():
    return [p for p in SKILL.rglob("*") if p.is_file() and "__pycache__" not in p.parts]


@pytest.mark.parametrize("pattern", FORBIDDEN)
def test_shipped_folder_has_no_forbidden_content(pattern):
    hits = [f"{p.relative_to(SKILL)}:{i}" for p in shipped_files()
            for i, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1)
            if re.search(pattern, line)]
    assert not hits, f"{pattern!r} found in {hits}"


def test_no_tests_ship_inside_the_skill():
    assert not (SKILL / "tests").exists()


def test_description_fits_the_import_limit():
    front = SKILL.joinpath("SKILL.md").read_text(encoding="utf-8").split("---")[1]
    desc = re.search(r"^description: (.*)$", front, re.M).group(1).strip("'\"")
    assert len(desc) <= 1024
