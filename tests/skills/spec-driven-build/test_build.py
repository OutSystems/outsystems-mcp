"""`outsystems-spec-driven-build/scripts/build.py`: the spec check, the interview
assembly, the Mentor prompt and the build report. Runs offline: the
script never calls the MCP."""
import json
import os
import pathlib
import re
import subprocess
import sys

import pytest

SKILL = pathlib.Path(__file__).resolve().parents[3] / "claude" / "skills" / "outsystems-spec-driven-build"
BUILD = SKILL / "scripts" / "build.py"
EXAMPLE = SKILL / "templates" / "example-spec.md"
TEMPLATE = SKILL / "templates" / "spec-template.md"


def run(*args, env=None):
    return subprocess.run([sys.executable, str(BUILD), *map(str, args)],
                          capture_output=True, text=True, encoding="utf-8", env=env)


def validate(path):
    return run("validate-spec", "--spec", path)


def write_spec(tmp_path, text, name="spec.md"):
    p = tmp_path / name
    p.write_text(text, encoding="utf-8")
    return p


def example():
    return EXAMPLE.read_text(encoding="utf-8")


def replace_section(text, num, body):
    """Swap the body of `## num.` (up to the next `## `) for `body`."""
    return re.sub(rf"(## {num}\.[^\n]*\n).*?(?=\n## )", lambda m: m.group(1) + body + "\n",
                  text, count=1, flags=re.S)


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


@pytest.mark.parametrize("num,title", [("1", "Overview"), ("2", "Roles"), ("3", "Data model"),
                                       ("4", "Screens + RBAC"), ("8", "Out of scope")])
def test_missing_required_section_fails(tmp_path, num, title):
    text = example().replace(f"## {num}. {title}", f"## {num}x. {title}", 1)
    p = validate(write_spec(tmp_path, text))
    assert p.returncode == 1
    assert f"## {num}. {title}: missing" in p.stdout


def test_a_nearly_empty_required_section_fails(tmp_path):
    p = validate(write_spec(tmp_path, replace_section(example(), 8, "- Nothing.")))
    assert p.returncode == 1
    assert "## 8. Out of scope: too short" in p.stdout


def test_no_roles_fails(tmp_path):
    text = replace_section(example(), 2, "Everyone who works on the team can use the app, there are no special roles.")
    p = validate(write_spec(tmp_path, text))
    assert p.returncode == 1
    assert "## 2. Roles: no roles found" in p.stdout


def test_no_entities_fails(tmp_path):
    body = ("### Entities\n\nWe will decide the tables later with the team, nothing to list yet.\n\n"
            "### Static enums\n\n- **TaskStatus**: Open, Done")
    p = validate(write_spec(tmp_path, replace_section(example(), 3, body)))
    assert p.returncode == 1
    assert "## 3. Data model: no entities found" in p.stdout


def test_no_screens_fails(tmp_path):
    text = replace_section(example(), 4, "Screens will be designed later by the team, nothing decided yet.")
    p = validate(write_spec(tmp_path, text))
    assert p.returncode == 1
    assert "## 4. Screens + RBAC: no screens found" in p.stdout


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


def test_empty_integrations_warns(tmp_path):
    p = validate(write_spec(tmp_path, replace_section(example(), 6, "")))
    assert p.returncode == 0
    assert "## 6. Integrations: missing or empty" in p.stdout


def test_missing_target_app_warns(tmp_path):
    text = example().replace("**Target app:** TaskTracker (new)", "")
    p = validate(write_spec(tmp_path, text))
    assert p.returncode == 0
    assert "no `**Target app:**` line" in p.stdout


def test_non_ascii_role_names_are_accepted(tmp_path):
    text = example().replace("EngineeringManager", "ÉquipeLead")
    p = validate(write_spec(tmp_path, text))
    assert p.returncode == 0, p.stdout


def test_a_defined_role_with_and_in_its_name_is_not_split(tmp_path):
    text = example().replace("- **EngineeringManager**:", "- **Sales and Marketing**:").replace(
        "| EngineerList | View all team members + their workload | EngineeringManager |",
        "| EngineerList | View all team members + their workload | Sales and Marketing |")
    p = validate(write_spec(tmp_path, text))
    assert "'EngineerList' names role(s) not defined" not in p.stdout, p.stdout


def test_two_roles_joined_by_a_non_english_word_are_split(tmp_path):
    text = example().replace(
        "| EngineerList | View all team members + their workload | EngineeringManager |",
        "| EngineerList | View all team members + their workload | Engineer e EngineeringManager |")
    p = validate(write_spec(tmp_path, text))
    assert p.returncode == 0, p.stdout


def test_underscores_keep_role_names_distinct(tmp_path):
    text = example().replace("**EngineeringManager**", "**Engineering_Manager**")
    p = validate(write_spec(tmp_path, text))
    assert p.returncode == 1
    assert "names role(s) not defined in ## 2. Roles: EngineeringManager" in p.stdout


def test_bold_and_plain_role_definitions_both_count(tmp_path):
    text = example().replace("- **EngineeringManager**:", "- EngineeringManager:")
    p = validate(write_spec(tmp_path, text))
    assert p.returncode == 0, p.stdout


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


def test_a_missing_required_answer_is_reported_as_such(tmp_path):
    answers = dict(ANSWERS)
    del answers["app_shell"]
    out = assemble(tmp_path, answers)
    assert "(NOT PROVIDED — required)" in out.read_text(encoding="utf-8")
    p = validate(out)
    assert p.returncode == 1
    assert "## 1. Overview: a required answer was not provided" in p.stdout


def test_screen_line_without_roles_fails_after_assembly(tmp_path):
    answers = dict(ANSWERS, screens_and_rbac="MyRequests | list own requests")
    p = validate(assemble(tmp_path, answers))
    assert p.returncode == 1
    assert "screen 'MyRequests' has no role" in p.stdout


def test_a_skipped_integrations_answer_still_warns(tmp_path):
    answers = dict(ANSWERS)
    del answers["integrations"]
    p = validate(assemble(tmp_path, answers))
    assert p.returncode == 0
    assert "## 6. Integrations: missing or empty" in p.stdout


def test_list_answers_become_lines_not_python_reprs(tmp_path):
    answers = dict(ANSWERS, roles=["Admin: all", "Viewer: read"],
                   screens_and_rbac=["Home | landing | Admin, Viewer"])
    text = assemble(tmp_path, answers).read_text(encoding="utf-8")
    assert "- **Admin**: all" in text and "- **Viewer**: read" in text
    assert "['" not in text


def test_dash_prefixed_role_lines_become_bold_roles(tmp_path):
    answers = dict(ANSWERS, roles="- Employee: requests leave\nManager: approves team requests")
    out = assemble(tmp_path, answers)
    text = out.read_text(encoding="utf-8")
    assert "- **Employee**: requests leave" in text and "- **Manager**: approves team requests" in text
    assert validate(out).returncode == 0


def test_title_comes_from_the_app_name_not_the_purpose(tmp_path):
    answers = dict(ANSWERS, app_shell="LeaveDesk (new)",
                   purpose="Employees request time off and managers approve it.")
    text = assemble(tmp_path, answers).read_text(encoding="utf-8")
    assert text.splitlines()[0] == "# App Spec: LeaveDesk"


def test_non_ascii_names_in_the_interview_become_roles(tmp_path):
    answers = dict(ANSWERS, roles="Técnico: cria e fecha as suas tarefas\nÉquipeLead: vê todas as tarefas",
                   screens_and_rbac="Lista | todas as tarefas | Técnico, ÉquipeLead")
    out = assemble(tmp_path, answers)
    text = out.read_text(encoding="utf-8")
    assert "- **ÉquipeLead**: vê todas as tarefas" in text
    p = validate(out)
    assert p.returncode == 0, p.stdout


def test_a_sentence_in_the_roles_answer_is_not_a_role(tmp_path):
    answers = dict(ANSWERS, roles=ANSWERS["roles"] + "\nNo anonymous access anywhere: every screen requires login.")
    out = assemble(tmp_path, answers)
    text = out.read_text(encoding="utf-8")
    assert "- **No anonymous access anywhere**" not in text
    assert "- No anonymous access anywhere: every screen requires login." in text
    assert validate(out).returncode == 0


@pytest.mark.parametrize("content,message", [("{bad", "is not valid JSON"),
                                             ('["a"]', "must hold one JSON object")])
def test_a_bad_answers_file_gives_one_line_not_a_traceback(tmp_path, content, message):
    a = tmp_path / "answers.json"
    a.write_text(content, encoding="utf-8")
    p = run("assemble-spec", "--answers", a, "--output", tmp_path / "spec.md")
    assert p.returncode == 1
    assert message in p.stderr
    assert "Traceback" not in p.stderr


def test_a_broken_install_gives_one_line_not_a_traceback(tmp_path):
    """assemble-spec without its bundled questions file fails cleanly, like list-questions."""
    scripts = tmp_path / "skill" / "scripts"
    scripts.mkdir(parents=True)
    (scripts / "build.py").write_bytes(BUILD.read_bytes())
    a = tmp_path / "answers.json"
    a.write_text(json.dumps(ANSWERS), encoding="utf-8")
    for args in (["assemble-spec", "--answers", a, "--output", tmp_path / "spec.md"], ["list-questions"]):
        p = subprocess.run([sys.executable, str(scripts / "build.py"), *map(str, args)],
                           capture_output=True, text=True, encoding="utf-8")
        assert p.returncode == 1
        assert "questions file" in p.stderr and "Traceback" not in p.stderr


def test_a_questions_file_with_the_wrong_structure_gives_one_line(tmp_path):
    root = tmp_path / "skill"
    (root / "scripts").mkdir(parents=True)
    (root / "templates").mkdir()
    (root / "scripts" / "build.py").write_bytes(BUILD.read_bytes())
    (root / "templates" / "interview-questions.json").write_text("{}", encoding="utf-8")
    a = tmp_path / "answers.json"
    a.write_text(json.dumps(ANSWERS), encoding="utf-8")
    p = subprocess.run([sys.executable, str(root / "scripts" / "build.py"), "assemble-spec",
                        "--answers", str(a), "--output", str(tmp_path / "spec.md")],
                       capture_output=True, text=True, encoding="utf-8")
    assert p.returncode == 1
    assert "unexpected structure" in p.stderr and "Traceback" not in p.stderr


# ------------------------------------------------------------------ build-prompt

def prompt():
    p = run("build-prompt", "--spec", EXAMPLE)
    assert p.returncode == 0, p.stderr
    return p.stdout


def test_the_prompt_carries_the_whole_spec_and_the_guardrails():
    out = prompt()
    assert "<spec>\n# App Spec: TaskTracker" in out and "</spec>" in out
    for section in ("## 3. Data model", "## 4. Screens + RBAC", "## 8. Out of scope"):
        assert section in out
    assert "Respect the role-per-screen assignments" in out
    assert "do NOT reply with a plan" in out
    assert "At the end, summarize" in out


def test_the_prompt_forbids_publishing():
    out = prompt()
    assert "Do NOT publish the app in this turn" in out
    assert out.rstrip().endswith("Do NOT publish the app.")


def test_the_prompt_bootstraps_sample_data_from_a_timer_on_publish():
    out = " ".join(prompt().split())
    for rule in ("Bootstrap the sample data with a Timer that runs when the app is published",
                 "a server action named Bootstrap<Entity> that counts the entity's rows and inserts only when it is empty",
                 "with one generated Create<Entity> call per row",
                 "run BootstrapData from a Timer scheduled to run when the app is published",
                 "Do NOT seed with SQL or Advanced SQL INSERT statements",
                 "a date is a literal date, never CurrDate() or CurrDateTime()"):
        assert rule in out, rule
    assert "OnInitialize" not in out and "EnsureSampleData" not in out


def test_no_design_to_app_or_mentor_internal_rules():
    out = prompt()
    for gone in ("<svg", "svg-icon-baking", "theme-collisions", "ListAppend", "main-content",
                 "design-to-app/references", "eSpace.AddDependency", "applyModelApiCode"):
        assert gone not in out, gone


def test_the_prompt_is_one_turn_and_takes_no_app_key_or_part():
    for extra in (["--app-key", "a0000001"], ["--part", "data"]):
        p = run("build-prompt", "--spec", EXAMPLE, *extra)
        assert p.returncode == 2 and "unrecognized arguments" in p.stderr


# ------------------------------------------------------------------ render-report

LANDED = {"runId": "run-1", "status": "succeeded",
          "result": {"attemptedChange": True, "changeApplied": True,
                     "validation": {"errorCount": 0, "warningCount": 3}},
          "summary": "Created 3 entities, 2 roles."}


def report(tmp_path, *results):
    args = ["render-report", "--spec", EXAMPLE, "--output", tmp_path / "report.md", "--app-key", "a0000001"]
    for i, r in enumerate(results):
        f = tmp_path / f"result-{i}.json"
        f.write_text(r if isinstance(r, str) else json.dumps(r), encoding="utf-8")
        args += ["--result", f]
    p = run(*args)
    out = tmp_path / "report.md"
    return p, (out.read_text(encoding="utf-8") if out.exists() else "")


def test_report_shows_the_build_and_fix_turns_and_their_summaries(tmp_path):
    fix = dict(LANDED, runId="run-2", summary="Created 7 screens.")
    p, text = report(tmp_path, LANDED, fix)
    assert p.returncode == 0, p.stderr
    assert "## Mentor turn: build" in text and "## Mentor turn: fix 1" in text
    assert "Created 3 entities, 2 roles." in text and "Created 7 screens." in text
    assert "`run-1`" in text and "`run-2`" in text and "`a0000001`" in text
    assert text.count("**Landed:** yes") == 2
    assert "# App Spec: TaskTracker" in text
    assert "Next steps" not in text


@pytest.mark.parametrize("result,reason", [
    ({"error": {"message": "turn timed out"}, "validation": {"errorCount": 3}}, "status is unknown"),
    (dict(LANDED, status="failed"), "status is failed"),
    (dict(LANDED, result={"changeApplied": True, "validation": {"errorCount": 2}}), "2 validation error(s)"),
    (dict(LANDED, result={"changeApplied": False, "validation": {"errorCount": 0}}), "the change was not applied"),
    (dict(LANDED, error="Mentor stopped early"), "turn error: Mentor stopped early"),
])
def test_a_turn_that_did_not_land_is_reported_and_exits_1(tmp_path, result, reason):
    p, text = report(tmp_path, result)
    assert p.returncode == 1
    assert "**Landed:** no" in text and reason in text


@pytest.mark.parametrize("result,reason", [
    (dict(LANDED, result={"change_applied": True, "validation": {"error_count": 2}}), "2 validation error(s)"),
    (dict(LANDED, result={"change_applied": False, "validation": {"error_count": 0}}), "the change was not applied"),
])
def test_snake_case_completion_fields_are_read(tmp_path, result, reason):
    p, text = report(tmp_path, result)
    assert p.returncode == 1
    assert "**Landed:** no" in text and reason in text


def test_a_fix_turn_that_landed_clears_an_earlier_failure(tmp_path):
    failed = dict(LANDED, result={"changeApplied": True, "validation": {"errorCount": 2}})
    p, text = report(tmp_path, failed, dict(LANDED, runId="run-2"))
    assert p.returncode == 0, p.stderr
    assert "**Landed:** no (2 validation error(s))" in text and "**Landed:** yes" in text


def test_a_failed_fix_turn_still_blocks_after_a_landed_build(tmp_path):
    failed = dict(LANDED, status="failed")
    p, _ = report(tmp_path, LANDED, failed)
    assert p.returncode == 1


def test_a_result_without_a_status_is_not_reported_as_succeeded(tmp_path):
    p, text = report(tmp_path, {"error": {"message": "turn timed out"}})
    assert "**Status:** `unknown`" in text and "`succeeded`" not in text


def test_a_list_of_pages_is_read_as_one_run(tmp_path):
    pages = [{"runId": "run-9", "status": "working",
              "events": [json.dumps({"msgType": "text", "text": "Created the "})]},
             {"runId": "run-9", "status": "succeeded",
              "result": {"changeApplied": True, "validation": {"errorCount": 0}},
              "events": [json.dumps({"msgType": "text", "text": "data model."})]}]
    p, text = report(tmp_path, pages)
    assert p.returncode == 0, p.stderr
    assert "Created the data model." in text and "**Landed:** yes" in text


@pytest.mark.parametrize("content,message", [("{bad", "is not valid JSON"),
                                             ('"text"', "must hold a run result")])
def test_a_bad_result_file_gives_one_line_not_a_traceback(tmp_path, content, message):
    p, _ = report(tmp_path, content)
    assert p.returncode == 1
    assert message in p.stderr and "Traceback" not in p.stderr


# ------------------------------------------------------------------ Windows pipes

@pytest.mark.parametrize("args", [["list-questions"], ["show-spec", "--spec", EXAMPLE],
                                  ["validate-spec", "--spec", TEMPLATE],
                                  ["build-prompt", "--spec", EXAMPLE]])
def test_output_survives_a_cp1252_pipe(args):
    """On Windows a piped stdout uses the ANSI code page; the script must still write
    the spec's arrows and the check marks."""
    env = dict(os.environ, PYTHONIOENCODING="cp1252")
    p = subprocess.run([sys.executable, str(BUILD), *map(str, args)], capture_output=True, env=env)
    assert b"UnicodeEncodeError" not in p.stderr, p.stderr.decode("utf-8", "replace")
    assert p.returncode in (0, 1)


# ------------------------------------------------------------------ content of the shipped folder

FORBIDDEN = [
    r"app_create", r"allowed-tools", r"mentor-copilot", r"deploy-preview", r"app-documentation",
    r"mentor-polling-behavior", r"\bCONVENTIONS\b", r"~/", r"\.claude/cache", r"\$\d",
    r"portable-agent-skills", r"\bSFTDD\b", r"\b20\d\d-\d\d-\d\d\b", r"FIELD-FEEDBACK",
    r"tenant_not_allowed", r"\bcancelling\b", r"Template Web App", r"EnsureSampleData",
]

# The skill describes behaviour, not tools: no tool names, and no harness- or
# vendor-specific features in the copy that also ships to Cursor and Kiro.
TOOL_NAMES = [
    r"\bmentor_[a-z_]+", r"\bapp_(list|info|logs|refs)\b", r"\benv_(app|list|apps)\b",
    r"\bpublish_status\b", r"\bcontext_[a-z]+\b", r"tools/list", r"status[- ]watcher",
    r"\bCodex\b", r"Claude Code has",
]


def shipped_files():
    return [p for p in SKILL.rglob("*") if p.is_file() and "__pycache__" not in p.parts]


@pytest.mark.parametrize("pattern", FORBIDDEN)
def test_shipped_folder_has_no_forbidden_content(pattern):
    hits = [f"{p.relative_to(SKILL)}:{i}" for p in shipped_files()
            for i, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1)
            if re.search(pattern, line)]
    assert not hits, f"{pattern!r} found in {hits}"


@pytest.mark.parametrize("pattern", TOOL_NAMES)
def test_skill_doc_names_no_tools(pattern):
    hits = [i for i, line in enumerate(SKILL.joinpath("SKILL.md").read_text(encoding="utf-8").splitlines(), 1)
            if re.search(pattern, line)]
    assert not hits, f"{pattern!r} on SKILL.md lines {hits}"


def test_no_tests_ship_inside_the_skill():
    assert not (SKILL / "tests").exists()


def test_description_fits_the_import_limit():
    front = SKILL.joinpath("SKILL.md").read_text(encoding="utf-8").split("---")[1]
    desc = re.search(r"^description: (.*)$", front, re.M).group(1).strip("'\"")
    assert len(desc) <= 1024
