# Security policy

## Supported versions

MCP Dashboard is currently a v1 release candidate. Security fixes are applied
to the latest commit on `main`; after publication, v1 receives security fixes
until a newer supported major version is announced.

## Reporting a vulnerability

Please use GitHub's private vulnerability reporting for this repository when
available. If it is unavailable, contact the maintainer privately rather than
opening a public issue containing exploit details, credentials, local paths,
or agent configuration.

Include the affected commit, operating system, Python version, reproduction
steps, expected impact, and whether the issue can modify agent configuration
or expose local data. You should receive an acknowledgement within seven days.

## Security model

- The control server binds to loopback and rejects non-loopback hosts.
- Each run uses a fresh authentication token and short-lived, host-only
  `HttpOnly`, `SameSite=Strict` session cookie.
- Mutations require an exact same-origin request.
- Live responses use a nonce-based Content Security Policy and disable
  framing, caching, and referrers.
- Config edits require browser confirmation, are backed up before mutation,
  and create a single-use local recovery point; profiles roll back on failure.
- Machine-readable exports recursively redact credential-like values.
- The test suite patches the home directory and stubs agent CLIs so it cannot
  modify real agent configuration.

## User responsibilities

MCP Dashboard starts configured stdio commands when `--probe` is used and can
edit real agent configuration in `--serve` mode. Review unfamiliar commands,
open only the URL printed by the current process, keep the service bound to
loopback, and review generated reports before sharing them. Reports may contain
server names, project names, and local filesystem paths even when credentials
have been redacted. Recovery points contain original local configuration and
must be protected like the source config. See [docs/PRIVACY.md](docs/PRIVACY.md)
for data sources, retention, opt-out, and removal details.
