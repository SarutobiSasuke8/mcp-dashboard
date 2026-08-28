# V1 release checklist

Run this checklist from a clean `main` checkout. A release is complete only
when every item has evidence in the tagged GitHub Actions run or release page.

## Repository administration — maintainer

- [ ] Confirm `mcp-dashboard` is reserved for this project on PyPI.
- [ ] Create a protected GitHub environment named `pypi` with required approval.
- [ ] Configure the PyPI trusted publisher for
      `SarutobiSasuke8/mcp-dashboard`, workflow `release.yml`, environment
      `pypi`.
- [x] Enable private vulnerability reporting. (Enabled 2026-08-28.)
- [ ] Protect `main`: require the test, quality, and package checks; block force
      pushes and deletion.
- [ ] Upload `docs/mcp-dashboard-hero.png` as the GitHub social preview.

## Release candidate

- [ ] Replace `Unreleased` in `CHANGELOG.md` with the release date.
- [ ] Change the README status badge/text from release candidate to stable v1.
- [ ] Confirm `pyproject.toml` and `mcpdash/__init__.py` contain the same version.
- [ ] Run `ruff check mcp_dashboard.py mcpdash tests scripts`.
- [ ] Run `python -m unittest discover -s tests -v`.
- [ ] Run `python -m build` and `python -m twine check dist/*`.
- [ ] Run `python scripts/package_smoke.py`.
- [ ] Complete a source and wheel smoke test on Windows, macOS, and Linux.
- [ ] Exercise one disposable toggle, profile application, and
      `mcp-dashboard --restore-last` on each platform.
- [ ] Review generated HTML, Markdown, and JSON fixtures for credentials,
      private transcript content, unexpected project names, and avoidable paths.
- [ ] Confirm no open P0/P1 issue and no unresolved rollback/data-loss incident.

## Publish

- [ ] Merge the release candidate through green required checks.
- [ ] Create and push the annotated `v1.0.0` tag from the reviewed commit.
- [ ] Approve the `pypi` environment only after the release workflow's build,
      metadata validation, installed-wheel smoke test, and GitHub release pass.
- [ ] Verify the PyPI page, wheel, source distribution, provenance attestation,
      GitHub assets, and `SHA256SUMS`.
- [ ] Install from PyPI with `pipx install mcp-dashboard` on a clean machine and
      run `mcp-dashboard --doctor` followed by `mcp-dashboard open`.

## Post-release

- [ ] Confirm README badges and installation links resolve.
- [ ] Monitor installation, mutation, migration, and privacy reports closely for
      the first week.
- [ ] Publish a patch immediately for any security, state-loss, or rollback
      regression; otherwise record the beta-exit evidence in the roadmap.
