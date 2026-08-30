"""uids: the identity a piece of content keeps across every installation.

A slug is a filename. It changes when the file is renamed and it collides when
two contributors pick the same name — and this repo does not force a filename
to match the slugified `name` inside it, so a slug is not even a reliable
handle on the content it names. A uid is neither of those things.

Optional throughout: everything merged before uids existed has none, and the
readers fall back to slug matching for those.
"""

import unittest
from pathlib import Path

from validate_automation import validate_automation_text
from validate_baseline import validate_baseline_text
from validate_task import load_actions_reference, validate_task_text

ROOT = Path(__file__).resolve().parent.parent
TASKS = ROOT / "tasks"

GOOD = "c6c2e640-2958-54eb-a64f-f6be1870c131"
ACTIONS = load_actions_reference()


def _task(uid_line=""):
    return f"name: T\n{uid_line}author: Connor Haggerty\nrisk: low\nactions:\n  - type: clear_temp_files\n"


class TaskUidTests(unittest.TestCase):
    def test_a_task_may_omit_its_uid(self):
        self.assertEqual(validate_task_text(_task(), ACTIONS), [])

    def test_a_valid_uid_is_accepted(self):
        self.assertEqual(validate_task_text(_task(f"uid: {GOOD}\n"), ACTIONS), [])

    def test_a_malformed_uid_is_rejected(self):
        for bad in ("not-a-uuid", "1234", "  "):
            with self.subTest(bad=bad):
                errors = validate_task_text(_task(f"uid: '{bad}'\n"), ACTIONS)
                self.assertTrue(any("uid" in e for e in errors), errors)

    def test_an_empty_uid_reads_as_absent(self):
        """`uid:` with nothing after it is an omission. Whitespace is not —
        somebody typed something, and silently ignoring it would hide a typo
        in the one field whose whole job is to be exact."""
        self.assertEqual(validate_task_text(_task("uid: \n"), ACTIONS), [])

    def test_a_non_string_uid_is_rejected(self):
        self.assertTrue(any("uid" in e for e in validate_task_text(_task("uid: 12345\n"), ACTIONS)))


class BaselineUidTests(unittest.TestCase):
    def _baseline(self, step_uid=""):
        extra = f"    uid: {step_uid}\n" if step_uid else ""
        return ("name: B\nauthor: Connor Haggerty\nsteps:\n"
                f"  - task: clear-temp-files\n{extra}    order: 1\n")

    def test_a_step_may_omit_its_uid(self):
        self.assertEqual(validate_baseline_text(self._baseline(), TASKS), [])

    def test_a_step_uid_matching_its_slug_is_accepted(self):
        self.assertEqual(
            validate_baseline_text(self._baseline(GOOD), TASKS), [])

    def test_a_step_uid_that_contradicts_its_slug_is_rejected(self):
        """The reference would import a different task than the one a reviewer
        read here, because Vigil trusts the uid."""
        errors = validate_baseline_text(
            self._baseline("11111111-1111-4111-8111-111111111111"), TASKS)
        self.assertTrue(any("does not match" in e for e in errors), errors)

    def test_a_malformed_step_uid_is_rejected(self):
        errors = validate_baseline_text(self._baseline("nope"), TASKS)
        self.assertTrue(any("uid" in e for e in errors), errors)


class AutomationUidTests(unittest.TestCase):
    def _automation(self, action_uid=""):
        extra = f"action_uid: {action_uid}\n" if action_uid else ""
        return ("name: A\nauthor: Connor Haggerty\ntrigger: event\n"
                "event: alert_fired\naction_kind: task\n"
                f"task: clear-temp-files\n{extra}target: event_host\n")

    def test_an_automation_may_omit_its_action_uid(self):
        self.assertEqual(validate_automation_text(self._automation()), [])

    def test_a_valid_action_uid_is_accepted(self):
        self.assertEqual(validate_automation_text(self._automation(GOOD)), [])

    def test_a_malformed_action_uid_is_rejected(self):
        errors = validate_automation_text(self._automation("nope"))
        self.assertTrue(any("action_uid" in e for e in errors), errors)


class CatalogUidTests(unittest.TestCase):
    """Every file that ships in this repo carries a uid, and they are unique."""

    def _uids(self):
        import yaml

        found = {}
        for kind in ("tasks", "baselines", "automations"):
            for path in sorted((ROOT / kind).glob("*.yaml")):
                raw = yaml.safe_load(path.read_text()) or {}
                found[f"{kind}/{path.stem}"] = raw.get("uid")
        return found

    def test_every_file_has_one(self):
        missing = [k for k, v in self._uids().items() if not v]
        self.assertEqual(missing, [], f"content without a uid: {missing}")

    def test_they_are_unique(self):
        values = [v for v in self._uids().values() if v]
        self.assertEqual(len(values), len(set(values)),
                         "two files share a uid, which defeats the point")
