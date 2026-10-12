# Tasks

A task is Vigil's task YAML, the same document the task editor saves, plus `uid`,
`author` and `created`. The full language (every action, its params and its outputs)
is in the Vigil wiki under **Task YAML Spec**, **Relevance and branches**, **Hunts** and
**Detection tasks**. This page is the short version.

| Field         | Required | Notes |
|---------------|----------|-------|
| `name`        | yes      | At most 120 characters. The file is named after it, slugified. |
| `uid`         | yes      | A UUID. It's the file's identity, so never change or reuse it. |
| `author`      | yes      | A real name. |
| `created`     | no       | An ISO date. |
| `description` | no       | What breaks, what the task does, what to know before deploying. |
| `risk`        | no       | `low`, `standard` or `high`. A floor; the server raises it to match the actions. |
| `platforms`   | no       | `linux`, `windows`, `darwin`. **A label only**: use `relevant:` to keep a task off a platform. |
| `inputs`      | no       | Values the operator supplies at deploy time, referenced as `${{ inputs.<id> }}`. |
| `relevant`    | no       | `all:` / `any:` / `not:` tree of `hunt_*` probes. No match means the host reports *not applicable*. |
| `severity`, `cves`, `boost` | no | Make it a **detection task**: a match becomes a finding on the Vulnerabilities page. |
| `actions`     | yes      | Steps (`id`, `type`, `params`, optional `when:`, `outcome:`) or branches (`if:` / `then:` / `else:`). |

A step can read earlier steps in `when:` and `if:` through `steps.<id>.status` and
`steps.<id>.result.<output>`, plus `inputs.*` and `agent.os`, `agent.arch` and
`agent.pkg_manager`.

```yaml
name: Keep Nginx Running
uid: d6772f24-63d4-4616-a313-8eb2de343916
author: Connor Haggerty
risk: standard
relevant:
  all:
    - hunt_package: {name: nginx}
actions:
  - id: check
    type: check_service
    params: {service_name: nginx}
    outcome: Already running
  - if: steps.check.result.active == False
    then:
      - id: restart
        type: restart_service
        params: {service_name: nginx}
        outcome: Restarted
```
