# Baselines

A **baseline** is a named, ordered sequence of tasks from this repository.
Vigil runs the whole sequence for you: a baseline is a task you do not click
every time. It is the "set of things I want done on every fresh machine" —
install the packages, apply the tweaks, run the checks — and it can be run
on demand from the UI, or automatically when hosts enroll.

Baselines live **flat inside `baselines/`**, the same way tasks live flat in
`tasks/`. The server lists the directory without recursing, so a file in a
subdirectory would never appear. Name the file after the baseline's `name`
with the same slug rules as tasks: lowercase, non-alphanumerics collapsed to
a single hyphen, at most 60 characters, `.yaml` extension.

## How a baseline names its tasks

A baseline does not copy tasks. Each step in `steps` names a task **by
slug** — the filename of a file in `tasks/` without its extension. A step
with `task: restart-nginx` refers to `tasks/restart-nginx.yaml`. The file
must exist in this repository; the validator resolves every slug against
`tasks/` and rejects a baseline that points at a file that is not there.
A baseline whose step names nothing would import as a baseline that silently
does nothing, which is worse than a rejected file, so the reference must
resolve.

The same slug rule applies in reverse from automations: an automation that
runs a baseline names it by the stem of the file in `baselines/`.

## Fields

| Field             | Type   | Required | Notes                                                        |
|-------------------|--------|----------|--------------------------------------------------------------|
| `name`            | string | yes      | At most 120 characters.                                      |
| `description`     | string | no       | At most 2000 characters.                                     |
| `author`          | string | yes      | At most 80 characters. Must be a real name, not a placeholder — `Admin`, `TODO`, `Unknown` and the empty string are rejected, the same rule as tasks. |
| `created`         | date   | no       | ISO date, `YYYY-MM-DD`.                                      |
| `target_tags`     | list   | no       | At most 32 strings. When set, only hosts carrying at least one of these tags receive the baseline at enrollment. When omitted, every approved host does. |
| `allow_high_risk` | bool   | no       | Defaults to `false`. See the high-risk rule below.           |
| `steps`           | list   | yes      | Non-empty, at most 32 entries. Each entry is a step (below). |

Each step is a mapping with:

| Field             | Type    | Required | Notes                                                                 |
|-------------------|---------|----------|------------------------------------------------------------------------|
| `task`            | string  | yes      | The slug of a file in `tasks/`. Must resolve to an existing file.      |
| `order`           | integer | no       | Defaults to the step's position in the list, 1-based. `order` values must be **unique within the baseline**, mirroring the server's unique constraint on `(baseline, order)`. |
| `params_override` | mapping | no       | Per-step input overrides, merged over the task's own action parameters when the baseline runs. Keys are the action's zero-based index as a string; values are mappings of parameter name to value. |

## The high-risk rule

If any step's task declares `risk: high`, the baseline must set
`allow_high_risk: true`. This mirrors the server's gate exactly: on the
server, turning that flag on is itself a 2FA-confirmed act, because a
baseline dispatches with nobody watching. The validator checks it by loading
each referenced task and reading its `risk` field — a task that omits
`risk` is treated as `standard`, the same default the server applies.

## Example

```yaml
name: New Server Build
author: Connor Haggerty
created: 2026-08-20
description: >-
  Brings a fresh Ubuntu host to the standard state: updates the package
  cache, installs the baseline tooling, and runs the health check.
target_tags:
  - web
allow_high_risk: false

steps:
  - task: refresh-package-cache
    order: 1
  - task: install-common-tools
    order: 2
  - task: run-health-check
    order: 3
    params_override:
      "0":
        extra_checks: ["disk"]
```

The `params_override` on the last step passes `extra_checks: ["disk"]` into
action `0` of `run-health-check` on top of whatever that task declares.
Because none of the three tasks is `risk: high`, `allow_high_risk` may stay
`false`.

Validate locally before you open a pull request:

```sh
python validate_baseline.py --all
python validate_baseline.py baselines/new-server-build.yaml
```
