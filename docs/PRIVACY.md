# Privacy and local data

MCP Dashboard is local-first. It has no telemetry, analytics, remote assets,
account system, or network upload path. The loopback dashboard is served only
to the local machine.

## Data read

- MCP definitions in Claude Code, OpenAI Codex, Gemini CLI, and Cursor config.
- The local process table for command, ancestry, RAM, and CPU attribution.
- Claude Code and Codex JSONL transcript metadata for MCP/skill tool names,
  timestamps, and project attribution. Prompt and response text is not needed.
- Installed skill metadata such as name, source, description, and lock state.
- MCP tool schemas and stderr produced when the user explicitly runs a probe.

Use `--no-usage` or `MCP_DASHBOARD_NO_USAGE=1` to skip all transcript reads.
This does not disable config discovery, process measurement, probing, skills,
controls, or report generation.

## Data retained

- Config directory: editable profiles and provenance labels.
- State directory: registry, bounded history, disabled-server stash, reports,
  and up to ten active local recovery points.
- Cache directory: probe results and per-transcript day-bucket usage counts.
- Beside agent config: the newest ten dashboard-created timestamped backups.

Recovery points and backups can contain full agent configuration, including
credentials already present in that configuration. They stay local and receive
restrictive file permissions where supported. Treat them as sensitive.

## Sharing

HTML, Markdown, and JSON output can contain server names, agent names, project
names, command paths, and local filesystem paths. JSON exports recursively
redact credential-like config values, authenticated URLs, sensitive arguments,
headers, environment entries, and vendor-specific credential blocks, but they
are not an anonymity transform. Review every artifact before sharing it.

## Removal

Uninstalling the Python package deliberately leaves user data in place to avoid
destroying disabled-server definitions or reports. Review and remove the
platform config, state, and cache directories manually when that data is no
longer needed.
