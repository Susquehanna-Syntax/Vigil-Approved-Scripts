"""Regression test over the real seed content in the repo.

Unlike the other validator tests (which use temp-directory fixtures), this
test walks the actual tasks/, baselines/ and automations/ directories and
asserts the matching validator reports success for every real file — so a
future seed cannot be merged broken, and it is the test the CI job leans on.
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from common import list_content_files  # noqa: E402
from validate_automation import validate_automation_file  # noqa: E402
from validate_baseline import validate_baseline_file  # noqa: E402
from validate_task import validate_task_file  # noqa: E402

_HERE = Path(__file__).resolve().parent.parent

# kind -> (validator, minimum number of real seed files expected)
_SEED_KINDS = {
    "tasks": (validate_task_file, 3),
    "baselines": (validate_baseline_file, 2),
    "automations": (validate_automation_file, 2),
}


class TestEverySeedValidates(unittest.TestCase):
    def test_every_seed_validates(self):
        failures = []
        for kind, (validate, minimum) in _SEED_KINDS.items():
            files, nested = list_content_files(_HERE / kind)
            if len(files) < minimum:
                failures.append(
                    f"{kind}/: expected at least {minimum} seed files, "
                    f"found {len(files)}")
            for path in nested:
                failures.append(
                    f"{path}: {kind} files must sit directly in {kind}/ — "
                    f"the Vigil server does not list subdirectories")
            for path in files:
                errors = validate(path)
                for message in errors:
                    failures.append(f"{path}: {message}")
        self.assertEqual(failures, [], "\n".join(failures))


if __name__ == "__main__":
    unittest.main()
