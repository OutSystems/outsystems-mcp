#!/usr/bin/env python3
"""Regression contract for the 0.16.0 publish/polling rules in this skill.

The four rules pinned here were ratified upstream (OutSystems MCP plugin
0.16.0, verified 2026-08-26) and folded into the PAS-canonical Mentor skills
under ledger AH-2026-08-26-008. This skill was one of the two out-of-repo
divergences that round measured: `references/mcp-flow.md` polled
`publish_status` with no `indeterminate` branch at all, so nothing stopped a
model from re-publishing an app whose first publish might still be building -
the move that wedges it.

The publish rules live in the reference file (the full MCP flow) and in
SKILL.md (the in-context summary). Both are checked: a rule that exists only in
the reference is a rule the model may never load.

Run it the way the estate runs unittest suites:

    python3 -m unittest discover -s skills/outsystems-design-to-app/tests -v

A bare `python3 -m unittest discover` from the repo root finds NOTHING here:
discovery only recurses into directories whose names are valid Python
identifiers, and `outsystems-design-to-app` contains hyphens, so the `-s` flag
is required, not decorative.

Stdlib only, so it runs wherever Python does - Codex included, which has no
pytest.
"""

import pathlib
import unittest

SKILL_DIR = pathlib.Path(__file__).resolve().parents[1]
SKILL_MD = SKILL_DIR / "SKILL.md"
MCP_FLOW = SKILL_DIR / "references" / "mcp-flow.md"
WORKFLOW = SKILL_DIR / "references" / "workflow.md"


class PublishContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.skill = SKILL_MD.read_text(encoding="utf-8")
        cls.flow = MCP_FLOW.read_text(encoding="utf-8")
        cls.workflow = WORKFLOW.read_text(encoding="utf-8")

    def test_mentor_poll_floor_is_thirty_seconds(self):
        self.assertIn(
            "**and at least ~30s**",
            self.flow,
            "the Mentor pause must be the served pollAfterMs AND at least ~30s",
        )
        self.assertIn(
            "floor to raise, never one to obey downward",
            self.flow,
            "the advertised interval is a floor, not a target",
        )

    def test_publish_polls_keep_their_own_cadence(self):
        """The ~30s floor is Mentor-only; publish polls (Tier 2) run ~15s."""
        self.assertIn("~15 s, not the Mentor ~30 s minimum", self.flow)
        self.assertIn("(~15 s cadence)", self.skill)

    def test_publish_refusal_is_answered_by_a_mentor_turn(self):
        self.assertIn("refusal is not a publish to retry", self.flow)
        for text, where in ((self.flow, "mcp-flow.md"), (self.skill, "SKILL.md")):
            self.assertIn(
                "turn_error",
                text,
                f"turn_error is the usual cause of a refusal - name it in {where}",
            )
            self.assertRegex(
                text,
                r"never a\s+second\s+`mentor_publish`",
                f"the refusal rule must forbid a second mentor_publish in {where}",
            )

    def test_indeterminate_publish_is_never_republished(self):
        for text, where in ((self.flow, "mcp-flow.md"), (self.skill, "SKILL.md")):
            self.assertIn(
                "indeterminate: true",
                text,
                f"the indeterminate branch must exist in {where}",
            )
            self.assertIn(
                "`publicationKey`",
                text,
                f"the remedy is a re-poll with the publicationKey ({where})",
            )
            self.assertIn(
                "re-publish",
                text,
                f"the never-re-publish rule must be stated in {where}",
            )

    def test_terminal_failure_is_distinguished_from_indeterminate(self):
        self.assertIn(
            "genuinely terminal `failed` outcome",
            self.flow,
            "a failed publish without indeterminate is genuinely terminal",
        )
        self.assertIn("OS-BEW-*", self.flow)

    def test_publish_terminal_state_is_lowercase_succeeded(self):
        """Upstream 241563d's correction: the terminal state is `succeeded`.

        `outsystems-spec-driven-build` took the same 0.16.0 contract and says
        `succeeded` / `failed` / `cancelled`; this skill said "until Completed",
        so the two skills patched together disagreed with each other.
        """
        for text, where in (
            (self.skill, "SKILL.md"),
            (self.flow, "mcp-flow.md"),
            (self.workflow, "workflow.md"),
        ):
            self.assertIn(
                "succeeded",
                text,
                f"the publish terminal state must be named `succeeded` in {where}",
            )
            self.assertNotRegex(
                text,
                r"until\s+`?Completed`?",
                f"'until Completed' is not a publish state the server returns ({where})",
            )

    def test_deploy_is_confirmed_before_reporting(self):
        """A publish that deployed nothing must not be reported as a deploy.

        The Gateway path's `no_changes_detected` flag is not on the
        mentor-publish path (upstream e60425f: it reports `outcome`/`status`),
        so the check is the `env_app` read-back before reporting a change.
        """
        self.assertIn(
            "confirm the deployed inventory via `env_app` before reporting a change",
            self.flow,
        )
        for text, where in ((self.skill, "SKILL.md"), (self.flow, "mcp-flow.md")):
            self.assertNotIn(
                "no_changes_detected",
                text,
                f"no_changes_detected is a Gateway-path flag, not a mentor-publish one ({where})",
            )

    def test_tenant_not_allowed_is_an_allowlist_gate(self):
        for text, where in ((self.flow, "mcp-flow.md"), (self.skill, "SKILL.md")):
            self.assertIn("tenant_not_allowed", text, f"missing in {where}")
            self.assertIn(
                "NOT a lapsed sign-in",
                text,
                f"tenant_not_allowed must not be presented as an auth failure ({where})",
            )


class MentorPollLoopTest(unittest.TestCase):
    """The Mentor poll loop merged from upstream 241563d, minus its unsafe gate.

    Upstream rewrote this loop against the 0.16.0 contract and got three things
    right that we did not have. Each was measured live against the tenant
    (read-only turns on `FkDeleteRuleProbe`, runs 3ec596af / 78f63e4a) before
    adoption:

      * per-response `pollAfterMs`, observed backing off 2000 -> 4000 -> 8000
        -> 16000 ms inside a single run and returning 0 on the terminal poll;
      * `details: true`, which is what turns the terse default
        (`events: []`, `nextCursor: null`) into a populated event page;
      * `env_app`'s application argument, which is `key` - the live schema
        requires ["key", "env_key"] with additionalProperties false, and a
        recorded call passing `application_key` returned
        `ValidationError: argument error: unknown parameter: application_key`.

    It also got one thing wrong. Upstream gates honest completion on
    `result.change_applied`. A 2026-08-26 tenant probe recorded
    `attempted_change: true` and `change_applied: true` coming back on
    read-only question turns that were told to make no edits
    (`projects/portable-agent-skills/docs/adoption/deleterule-probe-verification.md`,
    "One instrument caveat found on the way"); re-running that shape on
    2026-08-27 returned false / false. The flags are inconsistent rather than
    uniformly wrong, and the direction that breaks a gate is the false
    positive - a turn that wrote nothing reporting `change_applied: true` and
    being reported as done. This class pins the gate's absence.
    """

    @classmethod
    def setUpClass(cls):
        cls.skill = SKILL_MD.read_text(encoding="utf-8")
        cls.flow = MCP_FLOW.read_text(encoding="utf-8")
        cls.workflow = WORKFLOW.read_text(encoding="utf-8")

    def test_change_applied_is_not_a_completion_gate(self):
        """No branch may treat change_applied / attempted_change as proof."""
        for text, where in ((self.flow, "mcp-flow.md"), (self.skill, "SKILL.md")):
            self.assertNotRegex(
                text,
                r"(?i)if\s+.{0,40}change_applied\s+is\s+false",
                f"change_applied must not gate completion in {where}",
            )
            self.assertNotRegex(
                text,
                r"(?i)always\s+check\s+`?result\.change_applied",
                f"change_applied must not be presented as a check in {where}",
            )

    def test_completion_flags_are_named_as_measured_unreliable(self):
        self.assertIn(
            "read-only",
            self.flow,
            "the flags' measured behaviour on read-only turns must be stated",
        )
        self.assertIn(
            "not a write signal",
            self.flow,
            "the measured rule is that the completion flags are not write signals",
        )
        self.assertIn(
            "deleterule-probe-verification.md",
            self.flow,
            "the rule must cite the probe that measured it",
        )

    def test_a_landed_change_is_verified_by_readback(self):
        self.assertRegex(
            self.flow,
            r"(?i)read(ing)?\s+(the\s+)?(model|app state)\s+back|read\s*-?\s*back",
            "the replacement for the gate is a readback, and it must be named",
        )

    def test_mentor_statuses_are_lowercase(self):
        for name in ("succeeded", "failed", "cancelled", "running"):
            self.assertIn(
                f"`{name}`",
                self.flow,
                f"the Mentor status `{name}` must be named in mcp-flow.md",
            )
        for text, where in (
            (self.flow, "mcp-flow.md"),
            (self.skill, "SKILL.md"),
            (self.workflow, "workflow.md"),
        ):
            for stale in ("SUCCESS", "ERROR", "PENDING", "RUNNING"):
                self.assertNotIn(
                    stale,
                    text,
                    f"`{stale}` is not a status this server returns "
                    f"- it is lowercase ({where})",
                )

    def test_cancelling_is_documented_as_non_terminal(self):
        """Measured in the transcripts (36 occurrences); neither side had it.

        A loop that treats `cancelling` as terminal reports a cancel that has
        not finished; one that treats it as unknown may never stop.
        """
        self.assertIn("cancelling", self.flow)
        self.assertRegex(
            self.flow,
            r"`cancelling`[^\n]*non-terminal",
            "`cancelling` must be marked non-terminal",
        )

    def test_details_true_is_what_populates_events(self):
        self.assertIn("details: true", self.flow)
        self.assertRegex(
            self.flow,
            r"events:\s*\[\]",
            "the terse default (events: []) must be shown",
        )

    def test_draining_never_sleeps(self):
        """The pause is for a waiting poller, not a draining one.

        `outsystems-spec-driven-build` and `outsystems-mentor-copilot` both say
        to keep polling immediately while `nextCursor` advances. A loop here
        that slept on every non-truncated running response would contradict
        them and delay normal cursor-page draining, so the branch is pinned.
        """
        self.assertIn(
            "nextCursor advanced",
            self.flow,
            "the cursor-advance drain branch must exist in the loop",
        )
        self.assertIn(
            "drain-don't-sleep",
            self.flow,
            "the drain rule must be stated alongside the truncated rule",
        )
        self.assertIn(
            "must not drift apart",
            self.flow,
            "the loop must name the sibling skills it has to agree with",
        )

    def test_truncated_drains_instead_of_sleeping(self):
        self.assertRegex(
            self.flow,
            r"Top-level `truncated: true`",
            "the top-level truncated flag must carry a rule of its own",
        )
        self.assertRegex(
            self.flow,
            r"poll\s+again immediately",
            "truncated: true means drain now, not sleep",
        )

    def test_env_app_takes_key_not_application_key(self):
        """No CALL SITE may pass application_key.

        Naming it as the rejected argument is the point of the rule, so the
        string itself is allowed - what must not survive is a call shape that
        passes it.
        """
        for text, where in (
            (self.flow, "mcp-flow.md"),
            (self.skill, "SKILL.md"),
            (self.workflow, "workflow.md"),
        ):
            self.assertNotRegex(
                text,
                r"env_app\s*\{[^}]*application_key",
                f"env_app rejects application_key as an unknown parameter ({where})",
            )
        self.assertIn(
            "env_app { env_key, key }",
            self.skill,
            "SKILL.md Step 6 must call env_app with `key`",
        )
        self.assertIn(
            "unknown parameter: application_key",
            self.flow,
            "mcp-flow.md must record the measured rejection verbatim",
        )

    def test_poll_interval_is_reread_from_every_response(self):
        self.assertIn(
            "re-read it from every poll",
            self.flow,
            "pollAfterMs backs off within a run, so it must be re-read",
        )


if __name__ == "__main__":
    unittest.main()
