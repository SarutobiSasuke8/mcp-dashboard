# Contributing

Thanks for helping improve MCP Dashboard. Focused issues and pull requests are
welcome, especially real-machine macOS/Linux reports, additional safe config
fixtures, and reproducible MCP client compatibility findings.

## Development setup

```bash
git clone https://github.com/SarutobiSasuke8/mcp-dashboard.git
cd mcp-dashboard
python -m unittest discover -s tests -v
python -m build
python scripts/package_smoke.py
```

The runtime has no required third-party dependencies. Install Ruff only if you
want to run the same lint command used during development:

```bash
python -m pip install ruff
ruff check mcp_dashboard.py mcpdash tests scripts
```

## Before opening a pull request

1. Keep changes narrow and explain the user-visible effect.
2. Add or update tests for behavior changes.
3. Run the complete unit suite on Python 3.10 or newer.
4. Run `git diff --check` and avoid committing generated local state.
5. For UI changes, include before/after screenshots and check light, dark,
   narrow, and wide layouts.
6. For config mutation, probing, or redaction changes, describe the failure
   mode and rollback/security behavior explicitly.

Never include real agent configuration, credentials, transcript content, or
private filesystem details in fixtures, screenshots, issues, or pull requests.

## Design constraints

- Preserve a zero-required-dependency runtime unless a change has a strong
  operational justification.
- Keep all browser assets local.
- Treat agent configuration changes as transactional, backed up, and fail-safe.
- Keep static output read-only; mutations belong behind the authenticated
  loopback service.
- Maintain Python 3.10 compatibility and cross-platform CI.

See [DESIGN.md](DESIGN.md) for architecture and [ROADMAP.md](ROADMAP.md) for
priorities and release gates.
