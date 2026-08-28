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
- [x] Skills directory across Claude, `.agents`, `.codex`, and plugin roots,
      with usage counts and shadowing warnings
- [x] Responsive dashboard redesign with filters, keyboard tabs, persistent
      automatic/light/dark theme, and mobile card views
- [x] Recursive config-secret redaction plus nonce-based live-page browser
      hardening headers
- [x] Agent-aware usage attribution and globally deduplicated process trees
- [x] Transactional profile application, collision-proof backups, and
      fail-safe atomic vault outputs
- [x] Probe config fingerprints, strict `tools/list` validation, and spawned
      process-tree cleanup
- [x] `HttpOnly` loopback control session with exact-origin mutation checks
- [x] Test suite (73 tests, stdlib only) with hard sandbox isolation —
      `Path.home` patched, agent CLIs stubbed, so tests can never touch
      real config
- [x] CI across Ubuntu / Windows / macOS, Python 3.10 and 3.13
- [x] MIT licensed
- [x] Backup pruning — the tool keeps its newest 10 backups per config
      file and never touches hand-made ones

## Release status

The repository is a **packaged v1 release candidate**, not yet a published
stable release. Packaging, installed commands, platform user storage,
diagnostics, recovery, privacy controls, and release automation are
implemented. The unchecked gates now require hosted CI evidence, maintainer
administration, real-machine control/probe validation, and the actual tag.

### Public-preview gate

- [x] Public repository, clear purpose, MIT license, screenshot, and CI badge
- [x] Zero-required-dependency Python 3.10+ runtime
- [x] Cross-platform unit CI on Windows, macOS, and Linux
- [x] Authenticated loopback controls, backups, rollback, output redaction, and
      a sandboxed test suite
- [x] Source installation, first-run, daily-use, privacy, security, and
      troubleshooting documentation
- [x] Contribution guide, issue forms, pull-request template, and security policy

### Stable v1 release gate — required

- [x] **Package and isolate state** — add `pyproject.toml`, an
      `mcp-dashboard` console entry point, platform-appropriate user data/cache
      directories, clean uninstall behavior, and a successful installed-wheel
      smoke test in a fresh isolated environment; final PyPI/pipx proof is in
      the release checklist
- [ ] **Version and artifacts** — `--version`, changelog, validated sdist/wheel,
      and checksum generation are implemented; tag the reviewed commit and
      verify the generated GitHub release assets/notes
- [ ] **Release CI** — workflows now build packages, install the wheel into a clean
      environment, run CLI smoke tests, and publish only from an approved tag
      using trusted publishing; merge and obtain a green hosted run
- [x] **First-run diagnostics** — add a `--doctor` command covering Python,
      optional `psutil`, config paths, filesystem permissions, output location,
      supported agent CLIs, and port availability
- [ ] **Real-machine compatibility evidence** — complete clean onboarding,
      discovery, static output, live control, and probe smoke tests on current
      Windows, macOS, and Linux machines; document known agent/version limits
- [x] **Mutation UX** — add explicit confirmation and a visible last-backup or
      undo path for individual toggles and profile changes
- [x] **Privacy review** — document local sources, retained state, recovery
      sensitivity, output disclosure, removal, and add CLI/environment opt-out
      for transcript-derived usage collection
- [ ] **Release administration** — private vulnerability reporting is enabled
      and the package name is currently available; reserve it, configure branch
      protection and the approved `pypi` environment/trusted publisher, use the
      repository hero as the social preview, and confirm all default-branch links
- [ ] **Beta exit evidence** — resolve all known P0/P1 defects, complete one
      week of normal use without data-loss or rollback failures, and publish a
      first versioned GitHub release

## Next product improvements

- [x] **PowerShell 5.1 compatibility for the scheduler script** —
      `Register-MCPDashboardScan.ps1` no longer uses the PowerShell 7+ `?.`
      operator, so it parses on stock Windows PowerShell 5.1
- [ ] **Probe remote servers** — HTTP/SSE connectors have context cost too;
      complete the handshake over HTTP and count their schemas
- [ ] **One-click re-scoping** — the Advisor already says "only used in
      project X, move it to that project's `.mcp.json`"; add the button that
      does the move
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
