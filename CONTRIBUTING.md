# Contributing

A file in this repository becomes something an operator can deploy from the
Vigil UI on every installation that can reach this repository, so the bar is:
it must be valid, it must be safe to run on a machine that is not yours, and
it must be attributable. This page is the path from "I have a fix" to "it is
merged" for all three content types — tasks, baselines, and automations.

## The submission path

For a **task**, the fastest route starts in the Vigil task editor, not in a
text file. Write the task in the editor as you would for your own hosts, save
it so the server has validated the actions and parameters, and click
**Submit to Community**. The editor opens GitHub's new-file form pointed at
`tasks/` in this repository, pre-filled with your task's YAML. It injects the
`author` and `created` fields from your Vigil account and the current date if
they are not already declared, so you do not have to think about them.

**Baselines** and **automations** are filed by hand today — clone the
repository, add a file under `baselines/` or `automations/`, and commit — but
you then owe the same two fields yourself. The submission rules below are the
same for all three types.

## The filename

The file is named after the content's `name`, slugified:

- lowercase;
- every run of non-alphanumeric characters (spaces, punctuation, the like)
  collapses to a single hyphen;
- no leading or trailing hyphen;
- at most 60 characters, with a `.yaml` extension.

So the task `Remove PyCharm Process Lock` becomes
`remove-pycharm-process-lock.yaml`, and the baseline `New Server Build`
becomes `new-server-build.yaml`. Keep the filename and the `name` field in
agreement — they should read the same, only differing in case and punctuation.

## The slug reference rule

Baselines and automations do not copy the things they run; they reference
them **by slug** — the filename of the target file, without its extension.

- A baseline step names its task by the task's file stem: a step with
  `task: restart-nginx` refers to `tasks/restart-nginx.yaml`.
- An automation names its target the same way: `action_kind: task` refers to
  a file under `tasks/`, `action_kind: baseline` to a file under
  `baselines/`.

Every reference must resolve to a file that exists **in this repository**.
The validators check this against the filesystem on every push, so a
reference to a task that is not in the repo fails CI before review. This is
deliberate and not negotiable: a baseline whose step points at a task that is
not there would import as a baseline that silently does nothing — worse than
a rejected file — and a reference to content in another repository would
break the moment the two repos drift.

If you submit a baseline that references a new task in the same pull request,
both files must land together; the validator resolves references against the
tree the pull request produces.

### And the `uid` beside it

A reference may also carry the target's `uid`, and Vigil resolves by that
first. The slug stays because it is what a reviewer reading the diff can
follow; the uid is what actually resolves on the far side.

The distinction matters because a slug is a filename. It changes when a file
is renamed, it collides when two contributors pick the same name, and this
repo does not force a filename to equal the slugified `name` inside it —
`tasks/docker-prune-and-restart-unhealthy.yaml` is called "Docker Prune and
Restart Unhealthy Container". A uid is none of those things, which is what
lets a baseline keep pointing at the right task after somebody renames their
local copy of it.

When a reference carries both, they must agree. The validator rejects a step
whose uid belongs to a different file than its slug does: Vigil trusts the
uid, so such a file would import something other than what the diff showed.

Every file in this repo carries a `uid`, and Vigil's *Submit to Community*
writes one into anything you share. **Never reuse or edit one** — it is the
file's identity, not its version. Change it and every installation treats the
file as new content and forks a second copy alongside the one people already
have. Copy a file to start another and leave the `uid` in place, and the two
now claim to be the same thing; delete the line and let Vigil mint a new one.

### No host references in community automations

A community automation can target `event_host` (the host that raised the
event), `tags` (hosts carrying one of `target_tags`), or `all` (every managed
host). It cannot target a single host by id — the server's model supports
that, but a host id is a primary key on a particular server and means nothing
in another installation, so it is not portable. The validator rejects
`target: host` with a message pointing at `target: tags` instead. If you need
"run this on the machines that are my web servers," the answer is a tag, and
`target: tags` is how you name it.

## What the validators check

A pull request must pass the validator for its content type before it is
reviewed; the repository's CI runs all three — plus the unit tests — on every
push and pull request, and will not merge a red file. Run them yourself before
you push:

```sh
pip install pyyaml
python validate_task.py --all
python validate_baseline.py --all
python validate_automation.py --all
```

The shared rules, enforced identically by all three:

- a non-empty `name` (at most 120 characters);
- a real author — `author` must be a name, not a placeholder. `Admin`,
  `TODO`, `Unknown`, and the empty string are rejected. Community files are
  attributable; when a file causes trouble on a host, the author field is how
  you find out who to talk to;
- `created`, when present, must be an ISO date.

The task-specific rules (non-empty list of actions, every action a known type
from `references/actions.json` with its required parameters) and the
baseline- and automation-specific rules (slug references, the high-risk
opt-in, the cron character set, the target rules) are documented in
`schemas/baseline.md` and `schemas/automation.md`.

The task validator enforces one more community rule the server does not check:

- **No hardcoded home directories.** A string anywhere in the task's
  parameters that points under `/home/<user>/`, `/Users/<user>/`, or
  `C:\Users\<user>\` is rejected. A community task runs on someone else's
  box, where your home path does not exist. If the task genuinely needs a
  machine-specific path, declare it as an `inputs` entry and reference it
  with `{{ inputs.<id> }}`; the operator supplies the value when they deploy.

## What makes a good task

Beyond passing the validator, reviewers judge whether the task is worth
sharing:

- **Scoped actions over shell commands.** If a registry action does the job
  (`delete_path`, `restart_service`, `install_package`), use it. A `rm`
  inside `run_command` is a red flag; a scoped action is reviewable, has a
  declared risk tier, and does exactly what its name says.
- **The risk tier is honest.** `risk` is a floor the server raises to match
  the actions, not a label you can lower. Declaring a destructive task `low`
  to make it feel safe will not work — the effective risk is the maximum of
  what you declare and what the actions warrant.
- **The description tells an operator why.** One or two sentences on what
  breaks, what the task does, and anything they must know before they click
  Deploy. `relevance` is a short tag for what kind of machine this is for.

## What reviewers look for

A pull request is approved when the validator is green, the file sits flat in
its directory with a slugified name, the author is a person, every slug
reference resolves inside the repo, and the content is a scoped, honest fix
rather than a repurposed shell command. If your file trips the
home-directory rule, the fix is almost always the same: move the path into
`inputs`. If it trips the author rule, put a name in. If it trips a slug
reference, add the file it refers to in the same pull request — or fix the
stem.
