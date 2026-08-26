#!/usr/bin/env python3
"""Offline validator for Vigil community automation files.

Usage:
    python validate_automation.py automations/foo.yaml [more.yaml ...]
    python validate_automation.py --all

Checks each file against the automation schema (schemas/automation.md), plus
the cross-file rules the server enforces at import time:

  * `action_kind: task` requires a `task` slug resolving under tasks/ and
    forbids a `baseline` key; `action_kind: baseline` is the mirror image —
    supplying both, or the one that does not match action_kind, is an error;
  * `target: host` is not supported: host references are not portable, so the
    validator rejects it and points at `target: tags`;
  * `target_tags` is required and non-empty exactly when `target: tags`;
  * cron fields are strings of at most 64 characters matching ^[\\d*,\\-/]+$ —
    these strings reach a scheduler, so anything that is not a schedule
    (shell metacharacters, spaces, backticks) is rejected.

Uses only the standard library plus PyYAML. Shared rules (field limits, the
placeholder-author rule, the ISO-date rule, the CLI shell, non-recursive
discovery) live in common.py. Exits 0 when every file passes, 1 otherwise;
every failure prints one line to stderr as "<path>: <message>".
"""

from __future__ import annotations

import sys
from pathlib import Path

from common import (
    _HERE,
    _MAX_CRON_FIELD,
    CRON_FIELDS,
    _MAX_DESCRIPTION,
    _MAX_NAME,
    _CRON_FIELD,
    check_author,
    check_boolean,
    check_created,
    check_scalar,
    check_string_list,
    is_str,
    load_yaml,
    resolve_slug,
    run_validator,
)

_AUTOMATIONS_DIR = _HERE / "automations"
_TASKS_DIR = _HERE / "tasks"
_BASELINES_DIR = _HERE / "baselines"
_MIN_SEVERITIES = ("info", "warning", "critical")
_ACTION_KINDS = ("task", "baseline")
_TARGETS = ("event_host", "tags", "all")


def _check_cron(raw: dict, errors: list[str]) -> None:
    """The schedule trigger's `cron` mapping: five string fields, each
    matching the cron-field character set."""
    cron = raw.get("cron")
    if not isinstance(cron, dict):
        errors.append("'cron' must be a mapping with minute, hour, dom, month, dow")
        return
    for field in CRON_FIELDS:
        value = cron.get(field, "*" if field != "minute" else "0")
        if value is None:
            continue
        if not is_str(value):
            errors.append(f"'cron.{field}' must be a string")
        elif len(value) > _MAX_CRON_FIELD:
            errors.append(f"'cron.{field}' is too long (max {_MAX_CRON_FIELD})")
        elif not _CRON_FIELD.match(value):
            errors.append(
                f"'cron.{field}' {value!r} contains characters that are not a "
                f"schedule — only digits, *, comma, dash and slash are allowed")
    for key in cron:
        if key not in CRON_FIELDS:
            errors.append(f"unknown 'cron' field {key!r}")


def _check_trigger(raw: dict, errors: list[str]) -> None:
    trigger = raw.get("trigger")
    if not is_str(trigger) or trigger not in ("event", "schedule"):
        errors.append("'trigger' must be 'event' or 'schedule'")
        return
    if trigger == "event":
        event = raw.get("event")
        if not is_str(event) or not event.strip():
            errors.append("'event' is required when trigger is event")
        severity = raw.get("min_severity")
        if severity is not None:
            if not is_str(severity) or severity not in _MIN_SEVERITIES:
                errors.append(
                    f"'min_severity' must be one of: {', '.join(_MIN_SEVERITIES)}")
        check_string_list(raw, "event_tags", errors)
    else:
        _check_cron(raw, errors)


def _check_action(raw: dict, errors: list[str],
                  tasks_dir: Path, baselines_dir: Path) -> None:
    action_kind = raw.get("action_kind")
    if not is_str(action_kind) or action_kind not in _ACTION_KINDS:
        errors.append(f"'action_kind' must be one of: {', '.join(_ACTION_KINDS)}")
        return

    keys = {key for key in ("task", "baseline") if raw.get(key) is not None}
    if len(keys) > 1:
        errors.append(
            "supply exactly one of 'task' or 'baseline', matching 'action_kind'")
        return
    expected = action_kind
    if not keys:
        errors.append(
            f"'{expected}' is required when action_kind is {action_kind!r}")
    else:
        supplied = keys.pop()
        if supplied != expected:
            errors.append(
                f"action_kind is {action_kind!r} but {supplied!r} was supplied — "
                f"supply a {expected!r} slug instead")
            return
        slug = raw.get(expected)
        if not is_str(slug) or not slug.strip():
            errors.append(f"'{expected}' must be a non-empty slug")
            return
        root = tasks_dir if expected == "task" else baselines_dir
        if resolve_slug(root, slug) is None:
            errors.append(
                f"'{expected}' slug {slug.strip()!r} does not resolve to a file "
                f"in {expected}s/")

    override = raw.get("params_override")
    if override is not None:
        if not isinstance(override, dict):
            errors.append("'params_override' must be a mapping")
        else:
            for key, value in override.items():
                if not isinstance(value, dict):
                    errors.append(
                        f"'params_override' value for {key!r} must be a mapping")


def _check_target(raw: dict, errors: list[str]) -> None:
    target = raw.get("target")
    if target is None:
        target = "event_host"
    if target == "host":
        errors.append(
            "target: host is not supported in community automations — host "
            "references are not portable across installations; use "
            "target: tags instead")
        return
    if not is_str(target) or target not in _TARGETS:
        errors.append(
            f"'target' must be one of: {', '.join(_TARGETS)} "
            f"('host' is not supported in community automations)")
        return
    tags = raw.get("target_tags")
    if target == "tags":
        if not isinstance(tags, list) or not tags:
            errors.append(
                "'target_tags' is required and must be non-empty when "
                "target is tags")
        else:
            for index, item in enumerate(tags):
                if not is_str(item) or not item.strip():
                    errors.append(
                        f"'target_tags'[{index}] must be a non-empty string")
    elif tags is not None:
        errors.append("'target_tags' is forbidden unless target is tags")


def validate_automation_text(text: str,
                             tasks_dir: Path | None = None,
                             baselines_dir: Path | None = None) -> list[str]:
    """Validate automation YAML source.

    Returns a list of error strings; an empty list means the file is valid.
    """
    raw, error = load_yaml(text)
    if error is not None:
        return [error]
    if not isinstance(raw, dict):
        return ["top-level YAML must be a mapping"]

    if tasks_dir is None:
        tasks_dir = _TASKS_DIR
    if baselines_dir is None:
        baselines_dir = _BASELINES_DIR

    errors: list[str] = []
    check_scalar(raw, "name", _MAX_NAME, required=True, errors=errors)
    check_scalar(raw, "description", _MAX_DESCRIPTION, errors=errors)
    check_author(raw, errors)
    check_created(raw, errors)
    check_boolean(raw, "enabled", errors)
    _check_trigger(raw, errors)
    _check_action(raw, errors, tasks_dir, baselines_dir)
    _check_target(raw, errors)
    return errors


def validate_automation_file(path, tasks_dir: Path | None = None,
                             baselines_dir: Path | None = None) -> list[str]:
    """Validate one automation file; returns a list of error strings."""
    path = Path(path)
    if not path.is_file():
        return [f"cannot read {path}"]
    return validate_automation_text(path.read_text(encoding="utf-8"),
                                    tasks_dir, baselines_dir)


def main(argv=None) -> int:
    return run_validator(
        label="Validate Vigil community automation files.",
        description="checks automation files against the automation schema",
        content_dir=_AUTOMATIONS_DIR,
        kind="automation",
        validate_file=lambda p: validate_automation_file(p),
        argv=argv,
    )


if __name__ == "__main__":
    sys.exit(main())
