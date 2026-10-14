# MCP Dashboard

[![ci](https://github.com/SarutobiSasuke8/mcp-dashboard/actions/workflows/ci.yml/badge.svg)](https://github.com/SarutobiSasuke8/mcp-dashboard/actions/workflows/ci.yml)
[![tests](https://github.com/SarutobiSasuke8/mcp-dashboard/actions/workflows/tests.yml/badge.svg)](https://github.com/SarutobiSasuke8/mcp-dashboard/actions/workflows/tests.yml)
[![license: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](https://github.com/SarutobiSasuke8/mcp-dashboard/blob/main/LICENSE)
[![PyPI](https://img.shields.io/pypi/v/mcp-dashboard.svg)](https://pypi.org/project/mcp-dashboard/)
[![Python](https://img.shields.io/pypi/pyversions/mcp-dashboard.svg)](https://pypi.org/project/mcp-dashboard/)

A local dashboard for the cost and benefit of your MCP toolbox across
**Claude Code, OpenAI Codex, Gemini CLI, and Cursor**. It shows what each
server costs in RAM, CPU, context tokens, and startup time, set against how
often you actually call it, with working on/off switches and a skills
directory.

**Zero required runtime dependencies and no remote UI assets.** Python 3.10
or newer and the standard library are enough. `psutil` is an optional extra
for live CPU sampling. No API key is required. Version 1.0.0 is published on
PyPI.

![MCP Server Dashboard](https://raw.githubusercontent.com/SarutobiSasuke8/mcp-dashboard/main/docs/screenshot.png)

Design record: [DESIGN.md](DESIGN.md). What is next: [ROADMAP.md](ROADMAP.md).
Install detail, privacy choices, and troubleshooting:
[docs/GETTING_STARTED.md](docs/GETTING_STARTED.md).

## What it shows

The generated page has three views. The header theme control cycles
automatic, light, and dark. The theme is stored in the browser, and the open
view is kept in the URL hash, so both survive a live-control reload. On
narrow screens, tables collapse into labelled cards.

### Servers

Summary tiles: configured servers (and how many are off), processes running
locally, local RAM, context cost, calls in 30 days, and how many servers
were built by you.

Under the tiles:

- a filter for name, agent, scope, or verdict
- a chart of local MCP RAM over time
- a **local stdio** table: server, status and verdict, calls in 30 days,
  context cost, process count, CPU, RAM with a sparkline, and an on/off
  switch
- a **remote** table: server, status, calls in 30 days, context cost, and an
  on/off switch

Only stdio servers cost local RAM. Remote HTTP and SSE servers still add
tool schemas to context. Connectors that exist only on claude.ai are not
listed here.

Each server row shows its agent, scope, transport, and command, plus a
provenance badge: `yours`, `official`, `vendor`, `community`, `remote`, or
`unlabeled`.

### Advisor

Summary tiles: items that need attention, reclaimable RAM, context tokens,
and how many plaintext credentials were found in config.

Under the tiles:

- ranked recommendations, with estimated RAM savings and, in live mode, a
  switch-off button
- profile buttons that enable a named set and disable every other togglable
  server
- in live mode, a recovery button that restores the files from the most
  recent successful dashboard config change
- a bar chart of the most-used servers over 30 days
- a bar chart of the heaviest servers by RAM
- a credentials section when plaintext secrets are present in config

A static report shows the same layout, but the switches and profile buttons
do nothing. Use `mcp-dashboard open` when you want working controls.

### Skills

Summary tiles: skills installed, skills used in 30 days, how many sources
were found, and name collisions.

The directory is built from vault and project `.agents/skills`,
`.codex/skills`, and `.claude/skills`, then synced skills, user skills,
`CODEX_HOME`, and plugin copies. Each row shows the source, calls in 30
days, last use, and description. A `locked` chip comes from
`skills-lock.json`. When the same name is defined more than once, a
collision note names the copy that wins.

## Setup

Prerequisite: Python 3.10 or newer. No API key.

```bash
pipx install mcp-dashboard
mcp-dashboard --doctor
```

`pipx` keeps the application isolated and puts `mcp-dashboard` on your
`PATH`. Diagnostics check Python, writable config, state, and cache
directories, whether port 7817 is free, optional CPU sampling, and whether
the Claude, Codex, Gemini, and Cursor CLIs are on `PATH`. A missing CLI is
informational: config files can still be read directly.

Optional live CPU sampling, which is also the only way to get a CPU figure
on Windows:

```bash
pipx inject mcp-dashboard psutil
```

The same extra is declared as `mcp-dashboard[cpu]` if you install with pip.

From a source checkout, without installing the package:

```bash
git clone https://github.com/SarutobiSasuke8/mcp-dashboard.git
cd mcp-dashboard
python mcp_dashboard.py --doctor
```

On Windows, use `py` instead of `python` when that is how Python is
installed. `python -m mcpdash` is the packaging-independent fallback and
accepts the same arguments.

To install the current default branch rather than the PyPI release:

```bash
pipx install git+https://github.com/SarutobiSasuke8/mcp-dashboard.git
```

## Run

The usual first look, including a one-off probe of enabled stdio servers:

```bash
mcp-dashboard open --probe
```

That discovers local MCP configuration, reads transcript metadata for 30-day
usage, starts each enabled stdio server once to measure tools and startup,
writes the dashboard, and opens `http://127.0.0.1:7817/` with a one-time
token. Keep the terminal open while you use the switches. Stop the server
with `Ctrl+C`. Do not bookmark the tokenised URL: the token is new on every
run. If the browser does not open, copy the URL the command prints. If port
7817 is busy, pass `--port` with another free local port.

For a faster read-only first look, omit `--probe`:

```bash
mcp-dashboard open
```

Other commands that exist today:

```bash
mcp-dashboard scan                  # write a static dashboard and directory note
mcp-dashboard --open                # static report, then open it in a browser
mcp-dashboard --doctor              # check Python, storage, port, and CLIs
mcp-dashboard --report              # append a usage snapshot
mcp-dashboard --tasks               # file high-severity findings as tasks
mcp-dashboard --profile coding      # apply a named server set, then exit
mcp-dashboard --list-profiles
mcp-dashboard --restore-last        # undo the most recent dashboard config change
mcp-dashboard --no-usage            # do not read agent transcripts
mcp-dashboard --json out.json       # machine-readable snapshot, secrets redacted
mcp-dashboard --demo --open         # preview the page with sample data
mcp-dashboard --version
```

`open` is shorthand for `--serve --open`. `scan` is the default write-only
run. `--probe` can be slow because each enabled stdio server is started
once; `--probe-timeout` defaults to 25 seconds. `--no-usage`, or
`MCP_DASHBOARD_NO_USAGE=1`, skips transcript reading. Discovery, process
measurement, probing, controls, skills, and reports still run.

The seed profiles in the source checkout are `minimal`, `coding`, and
`research`. Applying a profile changes configuration for **new** agent
sessions. Processes that are already running keep going until that session
restarts. Live changes ask for confirmation in the browser, write a
timestamped backup, and record one local recovery point. Restore it from
the Advisor view or with `mcp-dashboard --restore-last`.

### Scheduled scans on Windows

From a source checkout:

```powershell
.\Register-MCPDashboardScan.ps1
.\Register-MCPDashboardScan.ps1 -IntervalHours 12 -Report -Probe
.\Register-MCPDashboardScan.ps1 -Unregister
```

The task refreshes outputs. It is not a permanently running web service.
Open the live dashboard with `mcp-dashboard open`.

## Where outputs go

If the working directory or the checkout sits inside an Obsidian vault (a
directory that contains `Obsidian Vault Management/`), the HTML dashboard,
directory note, and usage report are written to
`Obsidian Vault Management/Systems/`. Otherwise those three files go to
`<state>/reports/`.

Config, state, and cache never go into site-packages:

| Platform | Config | State | Cache |
| --- | --- | --- | --- |
| Windows | `%APPDATA%\mcp-dashboard` | `%LOCALAPPDATA%\mcp-dashboard\state` | `%LOCALAPPDATA%\mcp-dashboard\cache` |
| macOS | `~/Library/Application Support/mcp-dashboard` | the same tree, under `state/` | `~/Library/Caches/mcp-dashboard` |
| Linux | `$XDG_CONFIG_HOME/mcp-dashboard` or `~/.config/mcp-dashboard` | `$XDG_STATE_HOME/mcp-dashboard` or `~/.local/state/mcp-dashboard` | `$XDG_CACHE_HOME/mcp-dashboard` or `~/.cache/mcp-dashboard` |

`MCP_DASHBOARD_HOME` places config, state, and cache under one portable
root. `MCP_DASHBOARD_VAULT` selects the vault. `--html` and `--note` override
those two output paths.

Generated names, when you do not override them:

| File | What |
| --- | --- |
| `MCP Server Dashboard.html` | The dashboard page |
| `MCP Directory.md` | Living registry note |
| `MCP Usage Report.md` | Rolling snapshots from `--report` |

Profiles, provenance labels, the disabled-server stash, probe cache, usage
cache, history, and recovery points live in the platform directories above.

## How it measures

- **Config:** `~/.claude.json` (user and per-project entries), each project's
  `.mcp.json`, `~/.codex/config.toml` (`CODEX_HOME` is respected),
  `~/.gemini/settings.json`, and `~/.cursor/mcp.json`.
- **RAM and CPU:** the process table via psutil, otherwise `ps` or PowerShell
  `Get-CimInstance`. Each server is matched on its most distinctive command
  token, and the process tree is summed. Shells, editors, search tools, and
  this program's own ancestors are never counted. A tree that matches more
  than one configured definition is counted once and marked as estimated.
  Without psutil, Windows reports RAM but not CPU.
- **Context cost (`--probe`):** starts each enabled stdio server, completes
  the MCP `initialize` handshake, calls `tools/list`, and records tool count,
  estimated schema tokens, startup latency, and stderr on failure. Results
  are cached. A configuration fingerprint marks a cached probe as stale.
- **Usage:** `tool_use` blocks named `mcp__<server>__<tool>` in Claude Code
  transcripts (`~/.claude/projects/**/*.jsonl`), plus a best-effort reading
  of Codex rollout logs. Counts stay separated by agent. Skill invocations
  are counted the same way.

## Verdicts

`earning` (used in the last 30 days), `quiet` (cheap and idle), `dormant`
(used before, not lately), `unused` (never called, still costing),
`expensive` (high cost and two calls or fewer), `broken` (failing),
`disabled`. A server installed fewer than seven days ago is not judged
unused.

Provenance is detected automatically. Override it in the user-config copy of
`mcp-provenance.json`. Values are `self-built`, `official`, `vendor`, or
`community`, or an object with `provenance` and `note`. The badge `yours`
is the self-built label. Manual labels beat auto-detection. The source
checkout ships a seed file; the running tool reads the copy under the
platform config directory.

## Development

This repository has no `package.json` and no npm scripts. The checks below
are the ones the project actually runs:

```bash
python -m pip install -e .
python -m pip install "ruff==0.15.10" "build==1.6.0"
ruff check mcp_dashboard.py mcpdash tests scripts
python -m build
python -m unittest discover -s tests -v
```

The suite is 73 tests and uses only the standard library. It patches
`Path.home` and stubs agent CLIs, so it does not edit your real config.

[`.github/workflows/ci.yml`](.github/workflows/ci.yml) runs that install,
lint, build, and test sequence on Ubuntu with Python 3.13.
[`.github/workflows/tests.yml`](.github/workflows/tests.yml) keeps the wider
matrix: Ubuntu, Windows, and macOS, on Python 3.10 and 3.13, plus Ruff and
an installed-wheel smoke test.

See [CONTRIBUTING.md](CONTRIBUTING.md) before opening a pull request, and
[CHANGELOG.md](CHANGELOG.md) for versioned changes.

## Safety

Every config edit, including edits routed through the `claude` or `codex`
CLIs, takes a timestamped backup first. Disabled servers are stashed in full,
so switching them back on is lossless. Because the live endpoint edits real
config, it binds to loopback only, rejects a non-loopback `Host`, and
requires the per-run token printed by the command. Machine-readable exports
redact credential-like values. The tool reads local configuration and
transcript metadata on this machine and does not send that data anywhere.
Generated reports can contain server names, project names, and local paths,
so review them before sharing. See [SECURITY.md](SECURITY.md).

## Licence

[MIT](LICENSE). Free to use, fork, and build on.
