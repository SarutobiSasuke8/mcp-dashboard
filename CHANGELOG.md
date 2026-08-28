# Changelog

All notable changes follow [Keep a Changelog](https://keepachangelog.com/) and
the project uses semantic versioning.

## [1.0.0] - 2026-08-28

### Added

- Installable Python package with the `mcp-dashboard` console command and
  `python -m mcpdash` fallback.
- `mcp-dashboard open`, `--version`, `--doctor`, `--no-usage`, and
  `--restore-last` workflows.
- Platform-native config, state, cache, report, and recovery directories with
  non-destructive migration from source-checkout state.
- Confirmed browser mutations and a transactional, single-use recovery point
  for every successful individual or profile change.
- Wheel/sdist build validation, isolated package smoke tests, checksums, GitHub
  release automation, and PyPI trusted-publishing workflow.
- Repository hero, complete onboarding guide, security policy, contribution
  guide, issue forms, pull-request checklist, release checklist, and community
  conduct policy.

### Changed

- Standalone reports no longer write beside installed code; they use the
  platform state directory unless a vault or explicit output path is selected.
- Transcript-derived usage can be disabled per run or by environment variable.

### Security

- Recovery files are stored locally with restrictive permissions where the
  operating system supports them and never leave the machine.
- Live configuration changes require explicit browser confirmation and remain
  protected by the authenticated loopback control surface.

[1.0.0]: https://github.com/SarutobiSasuke8/mcp-dashboard/releases/tag/v1.0.0
