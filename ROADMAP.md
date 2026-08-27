# Roadmap

What's done, what's lined up next, and what's parked. Issues and PRs welcome
for anything here — or anything missing from here.

## Done

- [x] Config discovery across Claude Code, OpenAI Codex, Gemini CLI, and Cursor
- [x] RAM/CPU measurement of running stdio servers (psutil, `ps`, or PowerShell)
- [x] MCP handshake probe: tool count, context-token estimate, startup latency,
      real stderr on failure
- [x] Usage counting from Claude Code and Codex transcripts
- [x] Verdicts, ranked recommendations, and reclaimable-RAM estimates
- [x] Working on/off toggles and profiles behind an authenticated loopback server
- [x] Timestamped backup before **every** config edit, CLI paths included
- [x] Skills directory with usage counts and shadowing warnings
- [x] Test suite (38 tests, stdlib only) with hard sandbox isolation —
      `Path.home` patched, agent CLIs stubbed, so tests can never touch
      real config
- [x] CI across Ubuntu / Windows / macOS, Python 3.10 and 3.13
- [x] MIT licensed

## Next

- [ ] **Packaging** — `pip install mcp-dashboard` / `pipx run`, console entry
      point, so nobody needs to clone to try it
- [ ] **Probe remote servers** — HTTP/SSE connectors have context cost too;
      complete the handshake over HTTP and count their schemas
- [ ] **One-click re-scoping** — the Advisor already says "only used in
      project X, move it to that project's `.mcp.json`"; add the button that
      does the move
- [ ] **Backup pruning** — config backups accumulate forever; keep the last N
      per file
- [ ] **Real-world Unix validation** — the `ps` path and Unix process matching
      are written and unit-tested but have had far less real-machine mileage
      than Windows; field reports welcome
- [ ] **Profile editor in the UI** — profiles currently live in
      `mcp-profiles.json`; add create/edit from the Advisor tab

## Later

- [ ] Usage parsing for Gemini CLI and Cursor transcripts (only Claude Code
      and Codex today)
- [ ] Real tokenizer for context cost (currently chars/4 estimate)
- [ ] Longer-horizon trend view: RAM and calls over weeks, not just the
      current history window
- [ ] Watch mode — auto-rescan on config file change instead of on page load
- [ ] Per-server notes and snooze ("I know, stop recommending this")
- [ ] Export the Advisor's findings as a shareable report
