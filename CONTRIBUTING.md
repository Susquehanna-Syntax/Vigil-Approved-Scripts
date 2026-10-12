# Contributing

A file merged here becomes something every Vigil installation can fork and run on
machines that aren't yours. So it must be **valid**, **safe to run somewhere else**,
and **attributable**.

## The submission path

**Tasks.** Start in Vigil's task editor. Write and save the task (the server validates
it), then click **Submit to Community**. That opens GitHub's new-file form for `tasks/`,
pre-filled with the YAML plus `author`, `created` and a fresh `uid`.

**Playbooks and automations.** Open one in Vigil and click **Edit as YAML**. It shows
exactly the document this repo stores, ready to copy. Or write them by hand under `playbooks/` or `automations/`. Then open a pull
request. If a playbook needs a new task, add both in the same pull request.

## The rules CI enforces

CI runs Vigil's `manage.py validate_community --strict` (see the README), so these are
Vigil's real rules, not an approximation:

- **It parses.** It uses the same parser as the Community page and the task editor. Unknown
  actions, missing required params, bad `relevant:` trees and step references to steps that
  don't exist all fail.
- **No deprecated syntax.** Inputs are `${{ inputs.x }}`; the old `{{ inputs.x }}` fails. Use
  `relevant:` to say where a task applies. The free-text `relevance:` field fails.
- **File name = slugified `name`.** `Keep Nginx Running` is `keep-nginx-running.yaml`.
- **Every file has a `uid`, and uids are unique.** Never edit or reuse one. It is the file's
  identity: change it and every installation forks a second copy. To start a new file from an
  old one, delete the `uid:` line and let Vigil mint one, or use `python -c "import uuid;print(uuid.uuid4())"`.
- **References resolve.** Every playbook step and automation names a file in this repo, and
  its `uid` matches that file's.
- **Events exist.** An event automation listens for one of `alert_sent`, `alert_refired`,
  `host_approved`, `host_rejected`, `task_completed` or `insight_created`.
- **No hardcoded home directories.** A path under `/home/<user>/`, `/Users/<user>/` or
  `C:\Users\<user>\` doesn't exist on someone else's machine. Make it an input.
- **A real author.** Not `Admin`, `TODO` or `Unknown`.
- **Flat directories.** Vigil can't see subdirectories.

## What makes good community content

- **Scope itself.** A task that only makes sense on some hosts says so with `relevant:`
  (a `hunt_service`, `hunt_package` or `hunt_file` probe), so it reports *not applicable*
  elsewhere instead of failing. `platforms:` is only a label. `patch-windows-security`
  probes for the `wuauserv` service, which is what keeps it off Linux.
- **Check before changing.** Read the state, then act only if needed (`if:` on a step's
  outputs), and say which path each host took with `outcome:`. See `keep-nginx-running`.
- **Scoped actions over scripts.** `restart_service`, `delete_path` and `install_package` are
  reviewable and carry an honest risk tier. An inline `execute_script` must be hash-approved
  on every managed host, so it rarely suits community content.
- **An honest risk.** `risk:` is a floor. The server raises it to match the actions, so
  declaring a destructive task `low` doesn't work.
- **A description that says why.** Say what breaks, what the task does, and what to know
  before deploying it.

## What reviewers look for

CI is green. The content is a scoped, honest fix, not a repurposed shell command. It
behaves sensibly on hosts it doesn't apply to. The description lets an operator who has
never seen it decide whether to run it.
