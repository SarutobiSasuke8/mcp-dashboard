# Installation and onboarding

MCP Dashboard v1 runs on Python 3.10+ with no required runtime dependency and
does not need an API key. `pipx` is the recommended installer because it keeps
the application isolated while exposing the `mcp-dashboard` command globally.

## 1. Install

After the first PyPI release:

```bash
pipx install mcp-dashboard
```

Before PyPI publication, install the release candidate from GitHub:

```bash
pipx install git+https://github.com/SarutobiSasuke8/mcp-dashboard.git
```

Source development remains supported:

```bash
git clone https://github.com/SarutobiSasuke8/mcp-dashboard.git
cd mcp-dashboard
python mcp_dashboard.py --version
```

On Windows, use `py` in place of `python` if that is how Python is installed.
For a pipx installation, add optional live CPU sampling with:

```bash
pipx inject mcp-dashboard psutil
```

`psutil` is not needed for discovery, probing, usage analysis, configuration
controls, or report generation.

## 2. Check the installation

```bash
mcp-dashboard --doctor
```

Diagnostics verify Python, writable platform storage, loopback port
availability, optional CPU sampling, detected agent CLIs, and output paths.
Missing agent CLIs are informational because direct config discovery can still
work.

## 3. First run

```bash
mcp-dashboard open --probe
```

The first run:

1. Discovers MCP definitions from Claude Code, OpenAI Codex, Gemini CLI, and
   Cursor configuration.
2. Reads local Claude Code and Codex transcript metadata for 30-day usage.
3. Starts each enabled stdio server briefly to measure tool schemas, estimated
   context cost, startup time, and errors.
4. Writes the dashboard and local registry/history into platform user storage.
5. Opens an authenticated loopback URL in the default browser.

The probe is deliberate but potentially side-effectful because it starts each
configured command. Review unfamiliar server commands first, or run
`mcp-dashboard open` without `--probe` for discovery and live measurement only.

To prevent transcript-derived usage analysis, add `--no-usage` or set
`MCP_DASHBOARD_NO_USAGE=1`. Config discovery, process measurement, probing,
controls, skills, and reports continue to work.

## 4. Use the dashboard

- **Servers:** inspect state, process count, RAM, CPU, context cost, calls, and
  provenance.
- **Advisor:** work through ranked recommendations; in live mode, use switches
  and profiles to change agent configuration.
- **Skills:** find installed skills, usage, collisions, and the winning copy.

Config changes affect new agent sessions. Every browser mutation asks for
confirmation, creates timestamped config backups, and records a single-use
local recovery point. Restore the most recent dashboard change from the
Advisor or with `mcp-dashboard --restore-last`.

## 5. Open it again

Run this whenever you want the interactive dashboard:

```bash
mcp-dashboard open
```

Add `--probe` after installing or changing MCP servers. A tokenized URL is
printed on every live launch; do not bookmark an old URL because its token
expires with that process. Stop the local server with `Ctrl+C`.

For a static snapshot that does not expose working controls:

```bash
mcp-dashboard --open
```

## Output locations

When launched from an Obsidian vault containing `Obsidian Vault Management/`,
Markdown outputs are written to its `Systems/` folder. Otherwise reports use
the platform state directory:

- Windows: `%LOCALAPPDATA%\mcp-dashboard\state`
- macOS: `~/Library/Application Support/mcp-dashboard/state`
- Linux: `$XDG_STATE_HOME/mcp-dashboard` or `~/.local/state/mcp-dashboard`

Editable profiles and provenance use the platform config directory; probe and
usage caches use the platform cache directory. `MCP_DASHBOARD_HOME` places all
three beneath one portable root. `MCP_DASHBOARD_VAULT`, `--html`, and `--note`
override output discovery.

On first v1 run, existing source-checkout state is copied into these user
directories only when the destination does not exist. Original files are left
in place, making migration non-destructive and reversible.

## Scheduled scans on Windows source checkouts

```powershell
.\Register-MCPDashboardScan.ps1
.\Register-MCPDashboardScan.ps1 -IntervalHours 12 -Report -Probe
.\Register-MCPDashboardScan.ps1 -Unregister
```

The scheduled task refreshes outputs; it is not a permanently running web
service. Open the installed live dashboard with `mcp-dashboard open`.

## Troubleshooting

- **`python` not found on Windows:** try `py`.
- **Port 7817 is busy:** add `--port 7818` (or another free local port).
- **Browser did not open:** copy the complete URL printed in the terminal.
- **Installation looks incomplete:** run `mcp-dashboard --doctor`.
- **A server probe hangs or fails:** retry with a larger
  `--probe-timeout 45`, or run without `--probe` and inspect the reported
  stderr before probing again.
- **CPU is unavailable on Windows:** install the optional `psutil` package.
- **A config change is not visible in an agent:** start a new agent session.
- **A dashboard change was wrong:** use the Advisor recovery action or run
  `mcp-dashboard --restore-last` once.

## Update or remove

Update an installed copy with `pipx upgrade mcp-dashboard`; remove it with
`pipx uninstall mcp-dashboard`. User config, state, recovery points, and cache
are intentionally retained so uninstall cannot destroy reports or disabled
server definitions. Delete those directories manually only after reviewing and
preserving anything needed. MCP Dashboard does not install a background
service; remove a Windows scheduled scan first with the source script's
`-Unregister` option.

Source users update with `git pull` and continue to use
`python mcp_dashboard.py ...` in place of the installed command.
