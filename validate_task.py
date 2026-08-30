#!/usr/bin/env python3
"""Offline validator for Vigil community task files.

Usage:
    python validate_task.py tasks/foo.yaml [more.yaml ...]
    python validate_task.py --all

Checks each file against the subset of the Vigil task schema that a YAML file
is checked against server-side (see the Vigil server's parse_and_validate),
plus two community-repo-specific rules the server does not enforce:

  * no hardcoded home-directory paths under /home/, /Users/ or C:\\Users\\ —
    a community task must work for anyone, so machine-specific paths are
    declared as inputs and supplied at deploy time;
  * author must be a real name, not a placeholder (Admin, TODO, Unknown).

Uses only the standard library plus PyYAML. The action reference is loaded
from references/actions.json beside this script, so it can run from any
working directory in a bare checkout. Exits 0 when every file passes, 1
otherwise; every failure prints one line to stderr as "<path>: <message>".

Shared rules (field limits, the placeholder-author rule, the ISO-date rule,
the CLI shell, non-recursive discovery) live in common.py, imported here and
by the baseline and automation validators.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from common import (
    check_uid,
    _HERE,
    _MAX_ACTION_ID,
    _MAX_ACTIONS,
    _MAX_DESCRIPTION,
    _MAX_NAME,
    _MAX_RELEVANCE,
    _VALID_RISK,
    check_author,
    check_created,
    check_scalar,
    is_str,
    load_yaml,
    run_validator,
)

_ACTIONS_REF = _HERE / "references" / "actions.json"
_TASKS_DIR = _HERE / "tasks"

# A path that hardcodes one person's home directory: /home/<user>/,
# /Users/<user>/, or C:\Users\<user>\ (case-insensitive on the Windows form).
_HOME_PATH = re.compile(
    r"/home/[^/\s]+/"
    r"|/Users/[^/\s]+/"
    r"|(?i:c:[\\/]users[\\/][^\\/\s]+[\\/])"
)


def load_actions_reference(path=None) -> dict:
    """Load references/actions.json (relative to this script, not the CWD)."""
    ref_path = Path(path) if path is not None else _ACTIONS_REF
    with open(ref_path, encoding="utf-8") as fh:
        payload = json.load(fh)
    if not isinstance(payload, dict) or not isinstance(payload.get("actions"), dict):
        raise ValueError(f"{ref_path} is not a valid action reference")
    return payload["actions"]


def _string_values(value, path="params"):
    """Yield (dotted_path, string) for every string value under params."""
    if isinstance(value, str):
        yield path, value
    elif isinstance(value, dict):
        for key, item in value.items():
            yield from _string_values(item, f"{path}.{key}")
    elif isinstance(value, list):
        for index, item in enumerate(value):
            yield from _string_values(item, f"{path}[{index}]")


def validate_task_text(text: str, actions: dict) -> list[str]:
    """Validate task YAML source against the action reference.

    Returns a list of error strings; an empty list means the file is valid.
    """
    raw, error = load_yaml(text)
    if error is not None:
        return [error]
    if not isinstance(raw, dict):
        return ["top-level YAML must be a mapping"]

    errors: list[str] = []
    check_scalar(raw, "name", _MAX_NAME, required=True, errors=errors)
    for field, limit in (("description", _MAX_DESCRIPTION),
                         ("relevance", _MAX_RELEVANCE)):
        check_scalar(raw, field, limit, errors=errors)
    check_uid(raw, errors)
    check_author(raw, errors)
    check_created(raw, errors)
    risk = raw.get("risk")
    if risk is not None:
        if not is_str(risk):
            errors.append("'risk' must be a string")
        elif risk.strip().lower() not in _VALID_RISK:
            errors.append(f"'risk' must be one of: {', '.join(_VALID_RISK)}")

    actions_raw = raw.get("actions")
    if not isinstance(actions_raw, list) or not actions_raw:
        errors.append("'actions' must be a non-empty list")
    elif len(actions_raw) > _MAX_ACTIONS:
        errors.append(f"too many actions (max {_MAX_ACTIONS})")
    else:
        seen_ids: set = set()
        for index, entry in enumerate(actions_raw):
            if not isinstance(entry, dict):
                errors.append(f"action #{index + 1} must be a mapping")
                continue

            action_type = entry.get("type")
            if not is_str(action_type) or not action_type.strip():
                errors.append(f"action #{index + 1} missing 'type'")
                continue
            where = f"action #{index + 1} ({action_type})"
            if action_type not in actions:
                errors.append(f"{where}: unknown type {action_type!r}")
                continue

            action_id = entry.get("id") or f"step{index + 1}"
            if not is_str(action_id):
                errors.append(f"{where}: 'id' must be a string")
                action_id = f"step{index + 1}"
            if len(action_id) > _MAX_ACTION_ID:
                errors.append(f"{where}: 'id' is too long (max {_MAX_ACTION_ID})")
            if action_id in seen_ids:
                errors.append(f"{where}: duplicate action id {action_id!r}")
            seen_ids.add(action_id)

            params = entry.get("params")
            if params is None:
                params = {}
            if not isinstance(params, dict):
                errors.append(f"{where}: 'params' must be a mapping")
                params = {}

            for required in actions[action_type]["required"]:
                if required not in params:
                    errors.append(
                        f"{where} missing required param {required!r}")
                    break

            for where_param, value in _string_values(params):
                match = _HOME_PATH.search(value)
                if match:
                    errors.append(
                        f"{where}: {where_param} hardcodes a home directory "
                        f"({match.group(0)}...) — declare it as an inputs entry "
                        f"so the operator supplies the path")

    return errors


def validate_task_file(path, actions: dict | None = None) -> list[str]:
    """Validate one task file; returns a list of error strings."""
    path = Path(path)
    if not path.is_file():
        return [f"cannot read {path}"]
    if actions is None:
        actions = load_actions_reference()
    return validate_task_text(path.read_text(encoding="utf-8"), actions)


def main(argv=None) -> int:
    return run_validator(
        label="Validate Vigil community task files.",
        description="checks task files against the task schema",
        content_dir=_TASKS_DIR,
        kind="task",
        validate_file=lambda p: validate_task_file(p),
        argv=argv,
    )


if __name__ == "__main__":
    sys.exit(main())
