# Automations

An **automation** binds a trigger to an action: when something happens (or
when the clock says so), a task or a baseline runs on a set of hosts without
anyone clicking anything. It is the "when X, do Y" of the community repo.

Automations live **flat inside `automations/`**, the same way tasks live flat
in `tasks/`. Name the file after the automation's `name` with the same slug
rules as tasks: lowercase, non-alphanumerics collapsed to a single hyphen, at
most 60 characters, `.yaml` extension.

## Two trigger kinds

An automation's `trigger` is either `event` or `schedule`.

### `trigger: event`

Fires when a lifecycle event happens — an alert, a host approval, and so on.

| Field          | Type   | Required | Notes                                                        |
|----------------|--------|----------|--------------------------------------------------------------|
| `event`        | string | yes      | The name of the event to watch.                               |
| `min_severity` | string | no       | One of `info`, `warning`, `critical`. Alert events only: fire only when the alert is at least this severe. |
| `event_tags`   | list   | no       | Strings. Alert events only: fire only for events on hosts carrying one of these tags. |

### `trigger: schedule`

Fires on a cron schedule. The schedule is a single `cron` mapping with five
keys, one per classic cron field:

| Key      | Type   | Required | Notes                                                       |
|----------|--------|----------|-------------------------------------------------------------|
| `minute` | string | no       | Defaults to `0` (the top of the hour).                      |
| `hour`   | string | no       | Defaults to `*`.                                            |
| `dom`    | string | no       | Day of month. Defaults to `*`.                              |
| `month`  | string | no       | Defaults to `*`.                                            |
| `dow`    | string | no       | Day of week. Defaults to `*`.                               |

Every value must be a **string** of at most 64 characters made up only of
digits, `*`, `,`, `-`, and `/` — the characters cron itself understands.
Anything else is rejected: these strings reach a scheduler, and a permissive
cron field is a place to hide something that is not a schedule. So
`minute: "0; rm -rf /"`, `hour: "* $(whoami)"`, and the like fail validation
outright. The five fields flatten back onto the server's `cron_minute`,
`cron_hour`, `cron_dom`, `cron_month`, `cron_dow` columns one-to-one.

## The action

The action is one of two kinds, chosen by `action_kind`:

| Field         | Type   | Required | Notes                                                        |
|---------------|--------|----------|--------------------------------------------------------------|
| `action_kind` | string | yes      | `task` or `baseline`.                                        |
| `task`        | string | when `action_kind: task` | The slug of a file in `tasks/`. Must resolve. When `action_kind` is `baseline`, this key is forbidden. |
| `baseline`    | string | when `action_kind: baseline` | The slug of a file in `baselines/`. Must resolve. When `action_kind` is `task`, this key is forbidden. |
| `params_override` | mapping | no   | Input overrides merged over the action's parameters at dispatch. Keys are the action's zero-based index as a string; values are mappings of parameter name to value. |

Exactly one of `task` or `baseline` must be present, and it must match
`action_kind`. Supplying both, or supplying the one that does not match
`action_kind`, is an error.

## The target

The target is which hosts the action runs on:

| Field         | Type   | Required | Notes                                                        |
|---------------|--------|----------|--------------------------------------------------------------|
| `target`      | string | no       | Defaults to `event_host`. One of `event_host`, `tags`, or `all`. **`host` is not supported** in community automations — see below. |
| `target_tags` | list   | when `target: tags` | Non-empty list of strings. Hosts carrying at least one of these tags receive the action. Required and non-empty exactly when `target: tags`; forbidden otherwise. |

`target: event_host` (the default) runs the action on the host that raised
the event — the useful case for alert automations: "when disk-critical fires
on a host, run the cleanup task on *that* host." `target: all` runs it on
every managed host, which is what a scheduled sweep wants.

### Why there is no `target: host`

The server's model also has a `target: host` option that names one specific
host by its primary key. That key means nothing outside the server that owns
it — a community file cannot reference a host id that will not exist in
another installation — so the community schema does not support it and the
validator rejects `target: host` with a message pointing you at
`target: tags` instead. If you need "run this on the machines that are
my web servers," that is a tag, and `target: tags` is how you name it.

## Fields

| Field         | Type   | Required | Notes                                                        |
|---------------|--------|----------|--------------------------------------------------------------|
| `name`        | string | yes      | Non-empty, at most 120 characters.                            |
| `description` | string | no       | At most 2000 characters.                                      |
| `author`      | string | yes      | At most 80 characters. Must be a real name, not a placeholder. |
| `created`     | date   | no       | ISO date, `YYYY-MM-DD`.                                       |
| `enabled`     | bool   | no       | Defaults to `true`. A disabled automation is stored but does not fire. |
| `trigger`     | string | yes      | `event` or `schedule`.                                        |

Plus the trigger, action, and target fields described above, which are
required as a group according to the `trigger` and `action_kind` values.

## Example

```yaml
name: Clean Up On Disk Critical
author: Connor Haggerty
created: 2026-08-20
description: >-
  When a disk-critical alert fires, run the cleanup task on the host that
  raised it.
enabled: true

trigger: event
event: alert
min_severity: critical
event_tags:
  - web

action_kind: task
task: clean-stale-files

target: event_host
```

A scheduled variant, running a baseline nightly at 2am on the web hosts:

```yaml
name: Nightly Web Baseline
author: Connor Haggerty
description: Runs the standard web-server baseline every night at 02:00.

trigger: schedule
cron:
  minute: "0"
  hour: "2"

action_kind: baseline
baseline: new-server-build

target: tags
target_tags:
  - web
```

Validate locally before you open a pull request:

```sh
python validate_automation.py --all
python validate_automation.py automations/clean-up-on-disk-critical.yaml
```
