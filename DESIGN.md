# Design

Why this exists, how it works, and the decisions behind it.

---

## Why

Local **stdio** MCP servers (launched via `npx`, `node`, `uvx`, `python`,
`docker`) are real OS processes, spawned **once per open agent session** —
three open Claude Code windows run every stdio server three times. Remote/HTTP
servers cost no local RAM, but every connected server — local or remote —
injects its tool schemas into every request, which is a token cost on latency
and price that no process monitor shows.

So the real question is never "how much RAM is this using" alone. It is
**cost versus benefit**: RAM plus context tokens plus startup time, weighed
against how often the server is actually called. That framing drives the
whole design — the tool doesn't just report numbers, it renders a verdict.

---

## Layout

| Path | Role |
| --- | --- |
| `mcp_dashboard.py` | CLI entry point and orchestration |
| `mcpdash/common.py` | Paths, JSON/TOML IO, atomic writes, formatting |
| `mcpdash/config.py` | Discovery across agents; provenance; enable/disable; profiles |
| `mcpdash/probe.py` | Process table (RAM/CPU); MCP handshake probe |
| `mcpdash/usage.py` | Real usage counts from agent transcripts (cached) |
| `mcpdash/analysis.py` | History, verdicts, recommendations |
| `mcpdash/skills.py` | Skill discovery across all load paths |
| `mcpdash/render.py` | The three-tab HTML dashboard |
| `mcpdash/vaultout.py` | Markdown outputs for Obsidian vaults (registry note, usage report, task filing) |
| `mcpdash/demo.py` | Sample data for reviewing the visual without a real scan |
| `tests/test_dashboard.py` | 37 tests, standard library only |
| `Register-MCPDashboardScan.ps1` | Windows scheduled-task registration |
| `mcp-provenance.json` | Your provenance labels (committed — no secrets) |
| `mcp-profiles.json` | Your named server sets (committed — no secrets) |

Machine-local state, gitignored, never committed: `mcp-registry.json`,
`mcp-history.jsonl`, `mcp-probe-cache.json`, `mcp-usage-cache.json`,
`mcp-disabled.json`, `*.bak-*`, `output/`.

Output paths resolve by searching upward from the script for a folder that
looks like an Obsidian vault (containing `Obsidian Vault Management/`); if
found, markdown outputs go to its `Systems/` folder. Otherwise everything
lands in `output/` next to the script. `MCP_DASHBOARD_VAULT` overrides
either way.

---

## Coverage

| Agent | Config read | Toggle method |
| --- | --- | --- |
| Claude Code | `~/.claude.json` (user + per-project local), each project's `.mcp.json` | `claude mcp remove` / `add-json`, else direct edit |
| OpenAI Codex | `~/.codex/config.toml` (`CODEX_HOME` respected) | `codex mcp remove` / `add`, else TOML edit |
| Gemini CLI | `~/.gemini/settings.json` | Direct edit |
| Cursor | `~/.cursor/mcp.json` | Direct edit |

Every direct edit takes a timestamped `.bak-` backup first, and every write
(config or internal state) goes through a temp-file-then-replace so a crash
or full disk mid-write can never leave a config file truncated.

claude.ai-style hosted connectors are server-side and invisible to local
scanning — their *usage* still appears if the agent that called them also
writes local transcripts.

---

## What it measures, and how

**RAM and CPU** — reads the process table (`psutil` if installed, else `ps`
on POSIX or PowerShell `Get-CimInstance` on Windows), matches each stdio
server's most distinctive command token, and sums the whole process tree.
"Procs" counts root processes, which approximates how many sessions have
that server loaded.

Matching is deliberately conservative: a process only counts if its
executable is a plausible launcher (`node`, `python`, `uvx`, `docker`…) or
the configured command itself, and never if it is a shell, editor, or search
tool — and the scanning process's own ancestors are excluded. Without those
guards, any shell whose command line merely *mentions* a server gets
miscounted as running it; this was a real bug found and fixed during
development, now covered by tests.

**Context cost** (`--probe`, opt-in) — starts each stdio server exactly as an
agent would, completes the MCP `initialize` handshake, and calls
`tools/list`. That yields the tool count, an estimated token cost of the
schemas (~4 characters per token), the startup latency, and, when a server
fails, its real stderr. Cached in `mcp-probe-cache.json` between runs. It's
opt-in because it has the side effect of actually starting every server.

**Usage** — Claude Code writes one JSONL transcript per session under
`~/.claude/projects/<encoded-cwd>/`, where every tool call appears as a
`tool_use` block named `mcp__<server>__<tool>`. Counting those gives calls
per server over 30/90-day windows, last-used date, per-project attribution,
and top tools. Codex rollout logs under `~/.codex/sessions/` are scanned
best-effort. Skill invocations (`Skill` tool calls) are counted the same way.
Transcripts are parsed once per run and cached per file by size and mtime
with day-bucketed counts, so a scheduled scan doesn't re-read hundreds of
sessions on every tick, and timestamps are converted from UTC before
bucketing so the windows don't skew by the local offset.

---

## Provenance

Every server gets a badge, so the toolbox distinguishes what you built from
what you installed:

| Label | Meaning |
| --- | --- |
| `self-built` | A local script you wrote — auto-detected when a generic interpreter runs a non-`node_modules` script, or set by hand |
| `official` | `@modelcontextprotocol/*` |
| `vendor` | Known vendor scopes (`@playwright/`, `@figma/`, `@base-org/`…) |
| `community` | Third-party packages, including `owner/name`-style specs |
| `remote` | HTTP/SSE endpoints |
| `unlabeled` | Unrecognised — label it |

Manual labels in `mcp-provenance.json` always beat auto-detection.

---

## Verdicts and recommendations

Each server gets a one-word verdict from cost weighed against use:

| Verdict | Rule |
| --- | --- |
| `earning` | Called in the last 30 days |
| `quiet` | Cheap and idle, or too new to judge — no action needed |
| `dormant` | Used historically, nothing in 30 days |
| `unused` | Never called, and costs RAM or context |
| `expensive` | ≤2 calls in 30 days against high RAM or ≥6k context tokens |
| `broken` | Failing handshake or reported failed |
| `disabled` | Switched off, config stashed |

A seven-day grace period keeps a newly installed server at `quiet` no matter
its cost, so it isn't judged before it has had a chance to be used.

The Advisor view turns verdicts into ranked actions with estimated savings:
disable unused/dormant servers, fix or remove broken ones, demote
single-project servers to project scope, flag slow starters, and surface
plaintext credentials found in config `env` blocks (values redacted, never
echoed in full).

---

## Control surface

Static HTML cannot change config, so control lives in a local HTTP server:

```
python mcp_dashboard.py --serve      # http://127.0.0.1:7817/?t=<token>
```

- **Toggles** — switching a server off removes it from that agent's config
  and stashes the full config in `mcp-disabled.json`; switching on restores
  it.
- **Profiles** — named sets in `mcp-profiles.json`. Applying one enables its
  members and disables everything else, across all agents at once.

Because this endpoint edits real config, it is defended three ways:

1. **Loopback only** — the socket binds to `127.0.0.1`.
2. **Host-header check** — a request whose `Host` isn't loopback is rejected,
   which blocks DNS-rebinding attacks from a page open in the browser.
3. **Per-run token** — required in the query string for the page and in an
   `X-MCP-Token` header for every mutating call. A cross-origin page cannot
   attach a custom header without triggering a CORS preflight, which this
   server never answers with an allow — so the token can't be exfiltrated
   that way either.

Without all three, any website open in the browser could have silently
reconfigured the agent stack. Changes take effect for **new** sessions;
already-running sessions keep their processes until restarted.

---

## Design decisions

1. **Cost/benefit over raw metrics.** RAM alone is trivia — usage data is
   what turns the dashboard from observation into a decision.
2. **Probing is opt-in.** Accurate context-cost measurement requires
   starting every server; that side effect should be the user's choice, not
   the default.
3. **Nothing is destroyed.** Disabling stashes config, every direct edit
   backs up first, and history/usage data accumulate rather than overwrite.
4. **Portable and dependency-free.** Standard library only; `psutil`
   upgrades CPU sampling and process metadata when present, but nothing
   requires it.
5. **Works with or without a vault.** The vault-output path (`vaultout.py`)
   is additive — a clone with no vault nearby still runs standalone, writing
   to `output/`.

---

## Verification

`python -m unittest discover -s tests` runs 37 tests with no third-party
dependencies, against a throwaway `HOME` so no real config is ever touched.
Coverage: config discovery across agents, provenance classification, the
secrets audit's redaction, Codex TOML removal and restoration, disable/enable
round-trips and their backups, profile application, process matching
(including the shells-and-editors exclusions), the MCP handshake probe
against a real stdio server plus its failure paths, usage windows and
timezone handling, the transcript parse cache, verdicts and recommendations,
skill shadowing, HTML escaping, and the note/task writers.

Four defects were caught this way during development and fixed: `owner/name`
packages were labelled `unlabeled` instead of `community`; the seven-day
grace period suppressed only the `unused` verdict, letting a brand-new server
fall through to `expensive` anyway; probe subprocess pipes were left
unclosed; and one `SKILL.md` was listed twice when a scanned root contained
another scanned root, making every skill in the inner root look like it
collided with itself.

---

## Known limits

- Usage attribution is by server *name*; two agents configured with the same
  server name share a usage count.
- Codex transcript parsing is best-effort — its rollout format is less
  stable than Claude Code's transcript format.
- Context-token figures are estimates from schema size (~4 chars/token), not
  tokenizer-exact.
- Remote/HTTP servers cannot be probed for tool count or context cost —
  probing requires a stdio process to start.
- The `ps` fallback reports lifetime-average CPU, not a live sample; install
  `psutil` for a live sample (and for any CPU reading at all on Windows).
