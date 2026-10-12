# Playbooks

A playbook runs tasks from this repository in order on each host, and can branch on
how earlier tasks went. Vigil decides each branch on the server once the tasks before
it finish on that host.

| Field             | Required | Notes |
|-------------------|----------|-------|
| `name`, `uid`, `author`, `created`, `description` | as for tasks | |
| `target_tags`     | no       | Tags the playbook is meant for. |
| `allow_high_risk` | no       | `true` to allow high-risk tasks as steps. Defaults to `false`. |
| `steps`           | yes      | 1–32 steps, nested at most 3 levels deep. |

A **step**:

| Key                 | Notes |
|---------------------|-------|
| `task`              | The task's slug (its file name without `.yaml`). |
| `uid`               | The task's uid. It must match the file `task` names. |
| `id`                | Optional. Names the step so a later `if:` can read it. Quote `yes`/`no`/`on`/`off`. |
| `order`             | Optional positive integer, unique within the playbook. |
| `on_not_applicable` | `stop` (default) or `skip`. |
| `on_failure`        | `stop` (default) or `continue`, which makes the failure *handled* so a later `if:` can recover. |
| `outcome`           | Up to 40 characters, naming what reaching this step means. |
| `color`             | `rose`, `peach`, `lemon`, `mint`, `sky` or `lavender`, for the flow canvas. |
| `params_override`   | A mapping of input values for that task. |

A **branch** is `if:` (reading `steps.<id>.status`, which is `ok` / `failed` /
`not_applicable` / `skipped`, or `steps.<id>.result.<output>`), then `then:` and an
optional `else:`, each a list of steps or branches. A condition may only name steps
that come before it.

See `keep-the-web-tier-healthy.yaml` and `onboard-a-container-host.yaml`.
