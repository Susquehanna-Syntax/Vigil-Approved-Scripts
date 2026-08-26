"""Tests for validate_baseline.py — plain unittest, no Django.

Fixture YAML files are written into a tempfile.TemporaryDirectory() inside
each test rather than committed, so the `--all` runs in CI never pick them
up as real content.
"""

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from validate_baseline import validate_baseline_text  # noqa: E402

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

HIGH_RISK_TASK = """\
name: Delete Old Logs
author: Connor Haggerty
created: 2026-07-05
description: Deletes old log files.
risk: high

actions:
  - type: delete_path
    params:
      path: "/var/log/old"
"""


def baseline_text(steps_yaml: str, extra: str = "") -> str:
    return (
        "name: Nightly Cleanup\n"
        "author: Connor Haggerty\n"
        "created: 2026-07-05\n"
        "description: Cleans up nightly.\n"
        + extra
        + "steps:\n"
        + steps_yaml
    )


class BaselineFixtureCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)
        tasks_dir = self.root / "tasks"
        tasks_dir.mkdir()
        (tasks_dir / "clean-stale-files.yaml").write_text(STANDARD_TASK,
                                                          encoding="utf-8")
        (tasks_dir / "delete-old-logs.yaml").write_text(HIGH_RISK_TASK,
                                                        encoding="utf-8")
        self.tasks_dir = tasks_dir

    def validate(self, text: str) -> list[str]:
        return validate_baseline_text(text, tasks_dir=self.tasks_dir)


class TestBaselineAcceptsMinimalValid(BaselineFixtureCase):
    def test_baseline_accepts_minimal_valid(self):
        errors = self.validate(baseline_text(
            "  - task: clean-stale-files\n"))
        self.assertEqual(errors, [], f"unexpected errors: {errors}")


class TestBaselineRejectsMissingTaskSlug(BaselineFixtureCase):
    def test_baseline_rejects_missing_task_slug(self):
        errors = self.validate(baseline_text(
            "  - task: does-not-exist\n"))
        self.assertTrue(
            any("does-not-exist" in e for e in errors),
            f"expected the missing slug to be named, got: {errors}")


class TestBaselineRejectsDuplicateOrder(BaselineFixtureCase):
    def test_baseline_rejects_duplicate_order(self):
        errors = self.validate(baseline_text(
            "  - task: clean-stale-files\n"
            "    order: 1\n"
            "  - task: clean-stale-files\n"
            "    order: 1\n"))
        self.assertTrue(
            any("duplicate order 1" in e for e in errors),
            f"expected a duplicate-order error, got: {errors}")


class TestBaselineHighRiskRequiresOptin(BaselineFixtureCase):
    def test_baseline_high_risk_requires_optin(self):
        steps = "  - task: delete-old-logs\n"
        errors = self.validate(baseline_text(steps))
        self.assertTrue(
            any("delete-old-logs" in e and "allow_high_risk" in e
                for e in errors),
            f"expected the high-risk error naming the slug, got: {errors}")

        errors = self.validate(baseline_text(
            steps, extra="allow_high_risk: true\n"))
        self.assertEqual(errors, [], f"unexpected errors: {errors}")


if __name__ == "__main__":
    unittest.main()
