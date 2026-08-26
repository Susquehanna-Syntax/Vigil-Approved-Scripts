#!/usr/bin/env python3
"""Offline validator for Vigil community baseline files.

Usage:
    python validate_baseline.py baselines/foo.yaml [more.yaml ...]
    python validate_baseline.py --all

Checks each file against the baseline schema (schemas/baseline.md), plus the
cross-file rules the server enforces at import time:

  * every step's `task` slug must resolve to an existing file in tasks/ —
    a baseline whose step points at nothing would import as a baseline that
    silently does nothing, so the reference must resolve;
  * `order` values (after defaulting to list position) must be unique,
    mirroring the server's unique constraint on (baseline, order);
  * a step whose task declares `risk: high` requires the baseline to set
    `allow_high_risk: true`, mirroring the server's gate.

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
    _MAX_DESCRIPTION,
    _MAX_NAME,
    check_author,
    check_boolean,
    check_created,
    check_scalar,
    check_string_list,
    is_str,
    load_yaml,
    load_task_risk,
    resolve_slug,
    run_validator,
)

_BASELINES_DIR = _HERE / "baselines"
_TASKS_DIR = _HERE / "tasks"
_MAX_TARGET_TAGS = 32
_MAX_STEPS = 32


def validate_baseline_text(text: str, tasks_dir: Path | None = None) -> list[str]:
    """Validate baseline YAML source.

    Returns a list of error strings; an empty list means the file is valid.
    """
    raw, error = load_yaml(text)
    if error is not None:
        return [error]
    if not isinstance(raw, dict):
        return ["top-level YAML must be a mapping"]

    if tasks_dir is None:
        tasks_dir = _TASKS_DIR

    errors: list[str] = []
    check_scalar(raw, "name", _MAX_NAME, required=True, errors=errors)
    check_scalar(raw, "description", _MAX_DESCRIPTION, errors=errors)
    check_author(raw, errors)
    check_created(raw, errors)
    check_string_list(raw, "target_tags", errors, max_len=_MAX_TARGET_TAGS)
    check_boolean(raw, "allow_high_risk", errors)

    steps = raw.get("steps")
    if not isinstance(steps, list) or not steps:
        errors.append("'steps' must be a non-empty list")
    elif len(steps) > _MAX_STEPS:
        errors.append(f"too many steps (max {_MAX_STEPS})")
    else:
        seen_orders: dict = {}
        for index, step in enumerate(steps):
            where = f"step #{index + 1}"
            if not isinstance(step, dict):
                errors.append(f"{where} must be a mapping")
                continue

            task_slug = step.get("task")
            if not is_str(task_slug) or not task_slug.strip():
                errors.append(f"{where} missing 'task' slug")
                continue

            target = resolve_slug(tasks_dir, task_slug)
            if target is None:
                errors.append(
                    f"{where}: task slug {task_slug.strip()!r} does not resolve "
                    f"to a file in tasks/")
            elif load_task_risk(target) == "high":
                allow = raw.get("allow_high_risk")
                if allow is not True:
                    errors.append(
                        f"{where}: task {task_slug.strip()!r} is risk: high — "
                        f"the baseline must set allow_high_risk: true")

            order = step.get("order")
            if order is None:
                order = index + 1
            elif not isinstance(order, int) or isinstance(order, bool) \
                    or order < 1:
                errors.append(
                    f"{where}: 'order' must be a positive integer")
                order = None
            if order is not None:
                if order in seen_orders:
                    errors.append(
                        f"{where}: duplicate order {order} (order values must "
                        f"be unique within a baseline)")
                seen_orders[order] = index + 1

            override = step.get("params_override")
            if override is not None:
                if not isinstance(override, dict):
                    errors.append(f"{where}: 'params_override' must be a mapping")
                else:
                    for key, value in override.items():
                        if not isinstance(value, dict):
                            errors.append(
                                f"{where}: 'params_override' value for "
                                f"{key!r} must be a mapping")

    return errors


def validate_baseline_file(path, tasks_dir: Path | None = None) -> list[str]:
    """Validate one baseline file; returns a list of error strings."""
    path = Path(path)
    if not path.is_file():
        return [f"cannot read {path}"]
    if tasks_dir is None:
        tasks_dir = _TASKS_DIR
    return validate_baseline_text(path.read_text(encoding="utf-8"), tasks_dir)


def main(argv=None) -> int:
    return run_validator(
        label="Validate Vigil community baseline files.",
        description="checks baseline files against the baseline schema",
        content_dir=_BASELINES_DIR,
        kind="baseline",
        validate_file=lambda p: validate_baseline_file(p),
        argv=argv,
    )


if __name__ == "__main__":
    sys.exit(main())
