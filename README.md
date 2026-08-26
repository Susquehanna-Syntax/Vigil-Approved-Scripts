# Vigil Approved Scripts

Community content library for [Vigil](https://github.com/Susquehanna-Syntax/Vigil),
the self-hosted host management server. Every file in this repository is a
validated YAML document that an operator can deploy from the Vigil UI to any
connected host: a **task** that does one thing, a **baseline** that does a
sequence of things, or an **automation** that does one of those automatically.
The Vigil server fetches this repository and lists the content in its
Community tab, so anything merged here is immediately available to every Vigil
installation that can reach it.

## The three content types

| Type         | Directory        | What it is                                              | Validator                    |
|--------------|------------------|---------------------------------------------------------|------------------------------|
| Task         | `tasks/`         | One named set of actions, run by hand or as a baseline step. | `validate_task.py`           |
| Baseline     | `baselines/`     | A named, ordered sequence of tasks that runs on enrollment or on demand. | `validate_baseline.py`       |
| Automation   | `automations/`   | A trigger (event or schedule) bound to a task or baseline, run on a set of hosts. | `validate_automation.py`     |

Each type lives in its own directory, **flat**, and each has its own schema
document in `schemas/`:

- `tasks/` — a task declares a name, an author, and one or more actions drawn
  from the action reference. The task schema is documented in the Vigil
  wiki's Task YAML Spec.
- `baselines/` — a baseline names its tasks by slug and runs them in `order`.
  See `schemas/baseline.md`.
- `automations/` — an automation binds a trigger to a task or baseline and a
  target to a set of hosts. See `schemas/automation.md`.

The server lists each directory through the GitHub contents API and does not
recurse, so a file placed in a subdirectory such as `baselines/linux/` is
invisible to the Community tab. There are no subdirectories, and there should
never be — if a file belongs in one of these directories, it belongs directly
in it.

## How content references other content

A baseline does not copy its tasks; it references them **by slug** — the
filename of the target file without its extension. A step with
`task: remove-pycharm-process-lock` refers to
`tasks/remove-pycharm-process-lock.yaml`. The same rule applies to automations:
an automation that runs a baseline names it by the stem of the file in
`baselines/`. Every reference must resolve to a file that exists in this
repository; the validators resolve each slug against the filesystem and reject
a file that points at nothing. A baseline whose step names a task that is not
there would import as a baseline that silently does nothing, which is worse
than a rejected file.

Host references are a different matter. A community automation can target
`event_host` (the host that raised the event), `tags` (hosts carrying one of
`target_tags`), or `all` (every managed host) — but it cannot target a single
host by id. Host ids are not portable across installations, so the community
schema does not support `target: host` and the validator rejects it. If you
need "the machines that are my web servers," that is a tag.

## Validating locally

Each type has its own offline validator. They share the same interface:

```sh
pip install pyyaml
python validate_task.py --all              # every file under tasks/
python validate_baseline.py --all          # every file under baselines/
python validate_automation.py --all        # every file under automations/
python validate_task.py tasks/foo.yaml     # a single file, or several
```

Each validator exits non-zero with one `<path>: <message>` line per problem to
stderr and a `N passed, M failed` summary. CI runs all three, plus the unit
tests, on every push and pull request, so a file that passes locally will pass
there. The shared rules (field limits, the placeholder-author rule, the
ISO-date rule, the CLI shell, non-recursive discovery) live in `common.py`,
imported by all three validators, so the rules are enforced identically.

`references/actions.json` is the machine-readable action reference: every
action type the Vigil server knows, with its label, risk tier, and required
and optional parameters. It is generated from the server's `ACTION_REGISTRY`
by `manage.py dump_actions` in the Vigil repository. Because it is generated,
it can lag a Vigil release: right after a Vigil update that adds or changes an
action, the file here may be stale until it is regenerated and committed. If a
valid task fails because of an action this file does not know about, the
reference is probably behind the server — check the Vigil release notes before
changing your task.

## What a task file looks like

A task declares a name, who wrote it, when, and one or more actions drawn from
the action reference:

```yaml
name: Remove PyCharm Process Lock
author: Connor Haggerty
created: 2026-07-05
description: Removes a stale PyCharm lock file.
relevance: "Machine Effected"
risk: high

actions:
  - id: remove lock
    type: delete_path
    params:
      path: "{{ inputs.lock_path }}"
```

Actions must name only types found in `references/actions.json`, and each must
carry that type's required parameters. Because a community task runs on
anyone's machine, machine-specific paths are never hardcoded: a task that
needs a path declares it as an `inputs` entry and references it with
`{{ inputs.<id> }}`, so the operator supplies the value at deploy time. See
`CONTRIBUTING.md` for the full submission process and `schemas/` for the
baseline and automation schemas.
