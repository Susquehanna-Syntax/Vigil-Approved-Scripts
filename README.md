# Vigil Approved Scripts

Community content library for [Vigil](https://github.com/Susquehanna-Syntax/Vigil),
the self-hosted host management server. Every file here is a YAML document an
operator can fork into their own Vigil from the **Community** page and deploy to
any connected host:

| Type           | Directory      | What it is                                                                 | Schema                     |
|----------------|----------------|----------------------------------------------------------------------------|----------------------------|
| **Task**       | `tasks/`       | One named set of actions. It can decide where it applies (`relevant:`) and branch (`if:`). | `schemas/task.md`          |
| **Playbook**   | `playbooks/`   | Tasks run in order on each host, and they can branch on how earlier tasks went. | `schemas/playbook.md`      |
| **Automation** | `automations/` | A trigger (an event or a schedule) that runs a task or a playbook on a set of hosts. | `schemas/automation.md`    |

The server lists each directory **flat** through the GitHub contents API. A file in
a subdirectory such as `playbooks/linux/` is invisible to it, so there are no
subdirectories.

## What's in here

**Tasks.** These cover hunts (`find-exposed-redis`), a detection task (`xz-backdoor-cve-2024-3094`),
self-scoping fixes (`keep-nginx-running`, `truncate-container-logs`), patching for Linux and Windows,
app management (`keep-firefox-current`), tagging (`tag-container-hosts`), and a few classics
(`install-nginx`, `clear-temp-files`).

**Playbooks.**
- `standard-linux-server-build` is a fresh-host build.
- `container-host-maintenance` keeps container hosts tidy.
- `keep-the-web-tier-healthy` falls back to a recovery step when nginx won't come back.
- `onboard-a-container-host` branches on whether the host runs containers.
- `patch-tuesday` runs on a mixed Windows and Linux fleet.

**Automations.**
- `prune-docker-on-low-disk` runs on a disk alert.
- `restart-nginx-when-it-alerts` runs on an nginx alert.
- `tag-new-container-hosts` runs when a host is approved.
- `weekly-container-maintenance` and `monthly-patch-run` run on a schedule.

Together they form a working set. `tag-new-container-hosts` onboards every approved host. That tags
container hosts `docker`, and `weekly-container-maintenance` and `prune-docker-on-low-disk`
then pick them up by that tag.

## How content references other content

A playbook step or an automation names its target **by slug**, the file name without
`.yaml`, and also by the target's `uid`:

```yaml
steps:
  - id: logs
    task: truncate-container-logs                 # tasks/truncate-container-logs.yaml
    uid: 04954106-4ce1-48d7-a232-408624b49405     # that file's uid
```

Vigil resolves by the uid first. The slug is what a reviewer can follow in a diff. Both
must point at the same file in **this** repository. A file's name must be its `name`,
slugified (lowercase, with each run of other characters turned into one hyphen), because that
is how Vigil finds a forked task again.

Community automations target `event_host`, `tags` or `all`, never one host by id,
since host ids mean nothing on another installation.

## Validation: Vigil's own parsers

There's no separate validator to fall out of date. CI checks out Vigil and runs:

```sh
python manage.py validate_community <this repo> --strict
```

That parses every file with the **same code the Community page uses**, then checks:
every slug and uid resolves, file names match names, uids are unique, events exist,
there are no subdirectories and no hardcoded home directories. `--strict` also fails
deprecated syntax (`{{ inputs.x }}`, free-text `relevance:`).

To run it locally against a Vigil checkout:

```sh
cd ../Vigil/server
USE_SQLITE=1 VIGIL_PUBLIC_URL=http://localhost DJANGO_SECRET_KEY=dev \
VIGIL_SIGNING_KEY_SEED=$(python -c "import os,base64;print(base64.b64encode(os.urandom(32)).decode())") \
  python manage.py validate_community ../../Vigil-Approved-Scripts --strict
```

Needs Vigil 2026.14.1 or newer. See `CONTRIBUTING.md` to submit something.
