"""Tests for validate_automation.py — plain unittest, no Django.

Fixture YAML files are written into a tempfile.TemporaryDirectory() inside
each test rather than committed, so the `--all` runs in CI never pick them
up as real content.
"""

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from validate_automation import validate_automation_text  # noqa: E402

STANDARD_TASK = """\
name: Clean Stale Files
author: Connor Haggerty
created: 2026-07-05
description: Removes stale temp files.
risk: standard

actions:
  - type: delete_path
    params:
      path: "/tmp/stale"
"""

BASELINE_FILE = """\
name: Nightly Cleanup
author: Connor Haggerty
created: 2026-07-05
description: Cleans up nightly.

steps:
  - task: clean-stale-files
"""


def automation_text(trigger: str, action: str, target: str = "",
                    extra: str = "") -> str:
    return (
        "name: Disk Alert Cleanup\n"
        "author: Connor Haggerty\n"
        "created: 2026-07-05\n"
        "description: Runs cleanup when a disk alert fires.\n"
        + extra
        + trigger
        + action
        + target
    )


EVENT_TRIGGER = "trigger: event\nevent: alert\n"
TASK_ACTION = "action_kind: task\ntask: clean-stale-files\n"
BASELINE_ACTION = "action_kind: baseline\nbaseline: nightly-cleanup\n"


class AutomationFixtureCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)
        tasks_dir = self.root / "tasks"
        baselines_dir = self.root / "baselines"
        tasks_dir.mkdir()
        baselines_dir.mkdir()
        (tasks_dir / "clean-stale-files.yaml").write_text(STANDARD_TASK,
                                                          encoding="utf-8")
        (baselines_dir / "nightly-cleanup.yaml").write_text(BASELINE_FILE,
                                                            encoding="utf-8")
        self.kwargs = {"tasks_dir": tasks_dir,
                       "baselines_dir": baselines_dir}

    def validate(self, text: str) -> list[str]:
        return validate_automation_text(text, **self.kwargs)


class TestAutomationRejectsTargetHost(AutomationFixtureCase):
    def test_automation_rejects_target_host(self):
        errors = self.validate(
            automation_text(EVENT_TRIGGER, TASK_ACTION,
                            target="target: host\n"))
        self.assertTrue(
            any("portable" in e and "target: tags" in e for e in errors),
            f"expected the portability message, got: {errors}")


class TestAutomationRejectsMismatchedActionKind(AutomationFixtureCase):
    def test_automation_rejects_mismatched_action_kind(self):
        errors = self.validate(
            automation_text(EVENT_TRIGGER,
                            "action_kind: task\nbaseline: nightly-cleanup\n"))
        self.assertTrue(
            any("action_kind is 'task'" in e and "baseline" in e
                for e in errors),
            f"expected the mismatch error, got: {errors}")


class TestAutomationRejectsCronInjection(AutomationFixtureCase):
    def test_automation_rejects_cron_injection(self):
        for bad in ('"0; rm -rf /"', '"* $(whoami)"', '"0 && curl evil"',
                    '"`id`"'):
            with self.subTest(bad=bad):
                errors = self.validate(
                    automation_text(
                        'trigger: schedule\ncron:\n  minute: ' + bad + "\n",
                        TASK_ACTION))
                self.assertTrue(
                    any("cron.minute" in e for e in errors),
                    f"expected the cron field to be rejected, got: {errors}")


class TestAutomationAcceptsValidCron(AutomationFixtureCase):
    def test_automation_accepts_valid_cron(self):
        for good in ('"*/15"', '"0"', '"1,3,5"', '"1-5"', '"*"'):
            with self.subTest(good=good):
                errors = self.validate(
                    automation_text(
                        'trigger: schedule\ncron:\n  minute: ' + good + "\n",
                        TASK_ACTION))
                self.assertEqual(
                    errors, [], f"unexpected errors: {errors}")


class TestAutomationAcceptsValidEvent(AutomationFixtureCase):
    def test_automation_accepts_valid_event_automation(self):
        errors = self.validate(
            automation_text(EVENT_TRIGGER, TASK_ACTION))
        self.assertEqual(errors, [], f"unexpected errors: {errors}")


class TestAutomationTargetTagsRule(AutomationFixtureCase):
    def test_automation_target_tags_required_for_tags_target(self):
        errors = self.validate(
            automation_text(EVENT_TRIGGER, TASK_ACTION,
                            target="target: tags\n"))
        self.assertTrue(
            any("target_tags" in e and "non-empty" in e for e in errors),
            f"expected the target_tags error, got: {errors}")

    def test_automation_target_tags_forbidden_outside_tags_target(self):
        errors = self.validate(
            automation_text(EVENT_TRIGGER, TASK_ACTION,
                            target="target: all\ntarget_tags:\n  - web\n"))
        self.assertTrue(
            any("target_tags" in e and "forbidden" in e for e in errors),
            f"expected the forbidden error, got: {errors}")


if __name__ == "__main__":
    unittest.main()
