#!/usr/bin/env python3
"""Regression contract for the 0.16.0 publish/polling rules in this skill.

The four rules pinned here were ratified upstream (OutSystems MCP plugin
0.16.0, verified 2026-08-26) and folded into the PAS-canonical Mentor skills
under ledger AH-2026-08-26-008. This skill was one of the two out-of-repo
divergences that round measured: Step 5 told the model to honor `pollAfterMs`
at "2-5 s typical", the exact inversion of the rule — each poll costs a whole
model turn, so the served interval is a floor to raise, never one to obey
downward.

Prose drifts. These checks pin the load-bearing claims, not the wording around
them, so an edit that reintroduces a sub-30s Mentor cadence or a re-publish on
`indeterminate` fails here instead of in a live tenant.

Run it the way the estate runs unittest suites:

    python3 -m unittest discover -s skills/outsystems-spec-driven-build/tests -v

A bare `python3 -m unittest discover` from the repo root finds NOTHING here:
discovery only recurses into directories whose names are valid Python
identifiers, and `outsystems-spec-driven-build` contains hyphens, so the `-s`
flag is required, not decorative.

Stdlib only, so it runs wherever Python does - Codex included, which has no
pytest.
"""

import pathlib
import re
import unittest

SKILL_DIR = pathlib.Path(__file__).resolve().parents[1]
SKILL_MD = SKILL_DIR / "SKILL.md"


class PublishContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = SKILL_MD.read_text(encoding="utf-8")

    def test_mentor_poll_floor_is_thirty_seconds(self):
        """The Mentor sleep is the served interval AND at least ~30 s."""
        self.assertRegex(
            self.text,
            r"`pollAfterMs`\s*\n?\s*\*\*and at least ~30 s\*\*",
            "Step 5 must state the ~30 s Mentor poll floor alongside pollAfterMs",
        )

    def test_no_sub_thirty_second_mentor_cadence(self):
        """The old '2-5 s' cadence must not be prescribed for Mentor polls."""
        for bad in ("(2–5 s typical)", "(2-5 s typical)"):
            self.assertNotIn(
                bad,
                self.text,
                f"{bad!r} inverts the 0.16.0 rule - the interval is a floor to raise",
            )
        # The 5-15 s band is legitimate, but only for publish/deploy/extlib polls.
        for match in re.finditer(r"5[–-]15 s", self.text):
            window = self.text[max(0, match.start() - 200):match.end()]
            self.assertRegex(
                window,
                r"publish_status|deploy|extlib",
                "a 5-15 s band must be scoped to publish/deploy/extlib polls",
            )

    def test_long_pause_is_backgrounded_and_ends_the_turn(self):
        """An until-loop is polling in Bash, not the ratified pacing."""
        self.assertRegex(
            self.text,
            r"background-run mechanism\s+and \*\*end the turn\*\*",
            "the ~30 s pause must be backgrounded with the turn ended, not spun in Bash",
        )

    def test_advertised_interval_is_a_floor_not_a_target(self):
        self.assertRegex(
            self.text,
            r"floor to raise,\s+never one to obey downward",
            "the floor-not-target framing is the rule's whole point",
        )

    def test_publish_refusal_is_answered_by_a_mentor_turn(self):
        self.assertRegex(
            self.text,
            r"`mentor_publish` refusal is not a publish to retry",
            "the refusal rule must be stated",
        )
        self.assertRegex(
            self.text,
            r"never a second\s*\n?\s*`mentor_publish`",
            "the refusal rule must forbid a second publish",
        )
        self.assertIn(
            "turn_error",
            self.text,
            "turn_error is the usual cause of a refusal and must be named",
        )

    def test_indeterminate_publish_is_never_republished(self):
        self.assertIn("indeterminate: true", self.text)
        self.assertRegex(
            self.text,
            r"`publicationKey`",
            "the indeterminate remedy is a re-poll with the publicationKey",
        )
        self.assertRegex(
            self.text,
            r"`env_app` — never re-publish",
            "env_app verification and the never-re-publish rule must be stated together",
        )

    def test_tenant_not_allowed_is_an_allowlist_gate(self):
        self.assertIn("tenant_not_allowed", self.text)
        self.assertRegex(
            self.text,
            r"allowlist gate,\s*\n?\s*not a lapsed sign-in",
            "tenant_not_allowed must not be presented as an auth failure",
        )


class MentorPollLoopTest(unittest.TestCase):
    """Step 5's half of the poll loop merged from upstream 241563d.

    The sibling suite in `outsystems-design-to-app` carries the full rationale
    and the measured payload evidence. What this one guards is that the two
    skills do not drift apart again the way they did on the publish terminal
    state, where one said `succeeded` and the other said `Completed`.
    """

    @classmethod
    def setUpClass(cls):
        cls.text = SKILL_MD.read_text(encoding="utf-8")

    def test_details_true_is_what_populates_events(self):
        self.assertIn("`details: true`", self.text)
        self.assertIn(
            "terse by default",
            self.text,
            "the default response shape must be stated, or details:true reads as noise",
        )

    def test_truncated_drains_instead_of_sleeping(self):
        self.assertIn("Top-level `truncated: true`", self.text)
        self.assertIn("immediately to drain", self.text)

    def test_cancelling_is_non_terminal(self):
        self.assertRegex(
            self.text,
            r"`cancelling`[^\n]*non-terminal",
            "`cancelling` must be marked non-terminal",
        )

    def test_change_applied_is_not_a_completion_gate(self):
        self.assertIn(
            "not a write signal",
            self.text,
            "the measured rule about the completion flags must be stated",
        )
        self.assertIn(
            "deleterule-probe-verification.md",
            self.text,
            "the rule must cite the probe that measured it",
        )
        self.assertNotRegex(
            self.text,
            r"(?i)if\s+.{0,40}change_applied\s+is\s+false",
            "change_applied must not gate completion",
        )

    def test_env_app_is_never_called_with_application_key(self):
        self.assertNotRegex(
            self.text,
            r"env_app\s*\{[^}]*application_key",
            "env_app rejects application_key as an unknown parameter",
        )


if __name__ == "__main__":
    unittest.main()
