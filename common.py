#!/usr/bin/env python3
"""Shared helpers for the community-repo validators.

``validate_task.py``, ``validate_baseline.py`` and ``validate_automation.py``
all import from here so that the shared rules (field limits, the
placeholder-author rule, the ISO-date rule, the CLI shell, non-recursive
directory discovery) live in exactly one module. Each validator keeps its
own content-specific rules in its own file.

Uses only the standard library plus PyYAML, like the validators themselves.
"""

from __future__ import annotations

import argparse
import datetime
import re
import sys
from pathlib import Path

import yaml

_HERE = Path(__file__).resolve().parent
_MAX_NAME = 120
_MAX_DESCRIPTION = 2000
_MAX_RELEVANCE = 255
_MAX_AUTHOR = 80
_MAX_ACTIONS = 32
_MAX_ACTION_ID = 60
_VALID_RISK = ("low", "standard", "high")
_ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
# Community files are attributable — these are not authors.
_PLACEHOLDER_AUTHORS = {"admin", "todo", "unknown"}

# One cron field: digits and the characters cron itself understands
# (wildcards, lists, ranges, steps). Anything else — shell metacharacters,
# spaces, backticks, parentheses — is not a schedule and is rejected.
_CRON_FIELD = re.compile(r"^[\d*,\-/]+$")
_MAX_CRON_FIELD = 64
# The five classic cron fields, in order.
CRON_FIELDS = ("minute", "hour", "dom", "month", "dow")


def is_str(value) -> bool:
    return isinstance(value, str)


def load_yaml(text: str):
    """Parse YAML source. Returns (document, error); on failure the
    document is None and the error is a string."""
    try:
        return yaml.safe_load(text), None
    except (yaml.YAMLError, ValueError) as exc:
        return None, f"invalid YAML: {' '.join(str(exc).split())}"


def check_scalar(raw: dict, field: str, limit: int, required: bool = False,
                 errors: list[str] | None = None) -> None:
    """Check an optional (or required) string field against a length limit."""
    if errors is None:
        errors = []
    value = raw.get(field)
    if value is None:
        if required:
            errors.append(f"'{field}' is required")
    elif not is_str(value):
        errors.append(f"'{field}' must be a string")
    elif required and not value.strip():
        errors.append(f"'{field}' must be non-empty")
    elif len(value) > limit:
        errors.append(f"'{field}' is too long (max {limit})")


def check_author(raw: dict, errors: list[str]) -> None:
    """The placeholder-author rule shared by all three content types:
    `author` must be a real name, not Admin/TODO/Unknown/empty."""
    author = raw.get("author")
    if is_str(author):
        if len(author) > _MAX_AUTHOR:
            errors.append(f"'author' is too long (max {_MAX_AUTHOR})")
        stripped = author.strip()
        if not stripped:
            errors.append(
                "'author' must not be empty — community files are attributable")
        elif stripped.lower() in _PLACEHOLDER_AUTHORS:
            errors.append(
                f"'author' {stripped!r} is a placeholder — put a real name")


def check_created(raw: dict, errors: list[str]) -> None:
    """`created` is an optional ISO date; PyYAML parses a bare YYYY-MM-DD
    into a datetime.date, so both a date object and an ISO string are
    accepted."""
    created = raw.get("created")
    if (created is not None
            and (isinstance(created, datetime.datetime)
                 or not isinstance(created, (str, datetime.date)))):
        errors.append("'created' must be a date (YYYY-MM-DD)")
    elif isinstance(created, str) and not _ISO_DATE.match(created):
        errors.append(f"'created' {created!r} must be an ISO-8601 date (YYYY-MM-DD)")


def check_string_list(raw: dict, field: str, errors: list[str],
                      required: bool = False, non_empty: bool = False,
                      max_len: int | None = None) -> None:
    """Check an optional (or required) list-of-strings field."""
    if errors is None:
        errors = []
    value = raw.get(field)
    if value is None:
        if required:
            errors.append(f"'{field}' is required")
        return
    if not isinstance(value, list):
        errors.append(f"'{field}' must be a list")
        return
    if non_empty and not value:
        errors.append(f"'{field}' must be a non-empty list")
    if max_len is not None and len(value) > max_len:
        errors.append(f"too many entries in '{field}' (max {max_len})")
    for index, item in enumerate(value):
        if not is_str(item) or not item.strip():
            errors.append(f"'{field}'[{index}] must be a non-empty string")


def check_boolean(raw: dict, field: str, errors: list[str]) -> None:
    value = raw.get(field)
    if value is not None and not isinstance(value, bool):
        errors.append(f"'{field}' must be a boolean")


def load_task_risk(path: Path) -> str:
    """Read the `risk` field of a task file, defaulting to `standard` —
    the same default the server applies when a task omits it."""
    raw, error = load_yaml(path.read_text(encoding="utf-8"))
    if error is not None or not isinstance(raw, dict):
        return "standard"
    risk = raw.get("risk")
    if is_str(risk) and risk.strip().lower() in _VALID_RISK:
        return risk.strip().lower()
    return "standard"


def resolve_slug(root: Path, slug) -> Path | None:
    """Resolve a slug to a content file in *root*. The slug is the filename
    stem without its extension: `foo` matches `foo.yaml` or `foo.yml`.
    Returns the resolved path, or None when the file is absent."""
    if not is_str(slug) or not slug.strip():
        return None
    stem = slug.strip()
    for suffix in (".yaml", ".yml"):
        candidate = root / f"{stem}{suffix}"
        if candidate.is_file():
            return candidate
    return None


def list_content_files(content_dir: Path):
    """Discover content files the way the Vigil server does: flat,
    non-recursive. Returns (files, nested) where *files* is the sorted list
    of .yaml/.yml files directly in *content_dir* and *nested* is the sorted
    list of such files in subdirectories — which the server never sees and
    which are reported as errors by the caller.

    Deliberately NOT rglob for discovery: a file in a subdirectory would pass
    CI and then never appear in the UI, which is worse than rejecting it.
    """
    files = sorted(
        p for p in content_dir.glob("*")
        if p.is_file() and p.suffix in (".yaml", ".yml"))
    nested = sorted(
        p for p in content_dir.rglob("*")
        if p.is_file() and p.suffix in (".yaml", ".yml")
        and p.parent != content_dir)
    return files, nested


def nested_files_message(path: Path, kind: str) -> str:
    return (f"{path}: {kind} files must sit directly in their directory — the "
            f"Vigil server does not list subdirectories, so this file would "
            f"never appear in the Community tab")


def run_validator(label: str, description: str, content_dir: Path,
                  kind: str, validate_file, argv=None) -> int:
    """The shared CLI shell for the three validators.

    *validate_file* is a callable taking one path and returning a list of
    error strings. Returns the process exit code.
    """
    parser = argparse.ArgumentParser(description=f"{label}: {description}")
    parser.add_argument("files", nargs="*", help=f"{kind} files to validate")
    parser.add_argument("--all", action="store_true",
                        help=f"validate every .yaml/.yml file under {kind}/")
    args = parser.parse_args(argv)

    nested = []
    if args.all:
        if not content_dir.is_dir():
            print(f"{kind} directory not found: {content_dir}", file=sys.stderr)
            return 2
        files, nested = list_content_files(content_dir)
        for path in nested:
            print(nested_files_message(path, kind), file=sys.stderr)
    elif args.files:
        files = [Path(f) for f in args.files]
    else:
        parser.print_usage(sys.stderr)
        return 2

    passed = failed = 0
    failed += len(nested)
    for path in files:
        errors = validate_file(path)
        if errors:
            for message in errors:
                print(f"{path}: {' '.join(str(message).split())}", file=sys.stderr)
            failed += 1
        else:
            print(f"{path}: OK")
            passed += 1

    print(f"{passed} passed, {failed} failed")
    return 1 if failed else 0
