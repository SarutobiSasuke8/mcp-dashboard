"""Focused unit tests for mcpdash/config.py, driven by small fixture configs.

Every test runs inside the sandboxed HOME from ``test_dashboard.TempHomeCase``
(``Path.home`` patched, HOME/USERPROFILE/CODEX_HOME/GEMINI_HOME redirected,
``run_cli`` stubbed). Fixtures live in ``tests/fixtures`` and contain only
made-up values. No real user config is read and nothing touches the network.
"""

import json
import os
import shutil
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from test_dashboard import TempHomeCase  # noqa: E402

from mcpdash import config  # noqa: E402

FIXTURES = Path(__file__).resolve().parent / "fixtures"
PLAINTEXT_VALUES = ("fixture-plaintext-value-0001", "fixture-query-value",
                    "fixture-header-value-0002", "fixture-arg-value-0003")


class FixtureHomeCase(TempHomeCase):
    """Copies the fixture configs into the sandbox HOME."""

    def setUp(self):
        super().setUp()
        shutil.copy(FIXTURES / "claude.json", self.home / ".claude.json")
        shutil.copy(FIXTURES / "codex_config.toml", self.home / ".codex" / "config.toml")
        shutil.copy(FIXTURES / "gemini_settings.json",
                    self.home / ".gemini" / "settings.json")
        (self.home / ".cursor").mkdir()
        shutil.copy(FIXTURES / "cursor_mcp.json", self.home / ".cursor" / "mcp.json")
        # discover_servers() also reads .mcp.json from the working directory.
        self.work = self.root / "cwd"
        self.work.mkdir()
        self._old_cwd = os.getcwd()
        os.chdir(self.work)

    def tearDown(self):
        os.chdir(self._old_cwd)
        super().tearDown()

    def install(self, fixture, dest, replace=None):
        text = (FIXTURES / fixture).read_text(encoding="utf-8")
        for old, new in (replace or {}).items():
            text = text.replace(old, json.dumps(new)[1:-1])
        Path(dest).write_text(text, encoding="utf-8")

    def by_name(self, servers):
        return {(s["agent"], s["scope"], s["name"]): s for s in servers}


class TestFixtureDiscovery(FixtureHomeCase):
    def test_discovers_every_agent_and_scope_from_fixtures(self):
        found = self.by_name(config.discover_servers())
        self.assertEqual(set(found), {
            ("claude", "user", "filesystem"), ("claude", "user", "my-tools"),
            ("claude", "user", "docs-remote"), ("claude", "local", "filesystem"),
            ("codex", "user", "memory"), ("gemini", "user", "fetch"),
            ("cursor", "user", "playwright"),
        })
        self.assertTrue(all(s["enabled"] for s in found.values()))
        self.assertEqual(found[("claude", "user", "docs-remote")]["transport"], "http")
        self.assertEqual(found[("claude", "local", "filesystem")]["origin"], "/work/alpha")

    def test_keys_are_unique_and_scope_aware(self):
        servers = config.discover_servers()
        keys = [s["key"] for s in servers]
        self.assertEqual(len(keys), len(set(keys)))
        self.assertIn("claude::user::filesystem", keys)
        self.assertIn("claude::local::/work/alpha::filesystem", keys)

    def test_disabled_stash_is_listed_off_without_duplicating_live_servers(self):
        self.install("disabled.json", config.DISABLED_PATH,
                     {"FIXTURE_CURSOR_PATH": str(config.cursor_mcp_path())})
        servers = config.discover_servers()
        found = self.by_name(servers)
        self.assertFalse(found[("claude", "user", "old-search")]["enabled"])
        # The stashed playwright entry matches the live cursor entry exactly,
        # so the live (enabled) copy wins and it is not listed twice.
        playwright = [s for s in servers if s["name"] == "playwright"]
        self.assertEqual(len(playwright), 1)
        self.assertTrue(playwright[0]["enabled"])

    def test_provenance_overrides_and_notes_come_from_the_fixture(self):
        shutil.copy(FIXTURES / "provenance.json", config.PROVENANCE_PATH)
        found = self.by_name(config.discover_servers())
        fs = found[("claude", "user", "filesystem")]
        self.assertEqual((fs["provenance"], fs["prov_source"]), ("vendor", "manual"))
        self.assertEqual(fs["note"], "pinned by fixture")
        fetch = found[("gemini", "user", "fetch")]
        self.assertEqual((fetch["provenance"], fetch["prov_source"]), ("self-built", "manual"))
        self.assertEqual(fetch["note"], "")
        tools = found[("claude", "user", "my-tools")]
        self.assertEqual((tools["provenance"], tools["prov_source"]), ("self-built", "auto"))
        self.assertEqual(found[("cursor", "user", "playwright")]["provenance"], "vendor")
        self.assertEqual(found[("codex", "user", "memory")]["provenance"], "community")
        self.assertEqual(found[("claude", "user", "docs-remote")]["provenance"], "remote")

    def test_display_command_never_carries_plaintext_credentials(self):
        servers = config.discover_servers()
        rendered = json.dumps([s["command"] for s in servers])
        for value in PLAINTEXT_VALUES:
            self.assertNotIn(value, rendered)
        remote = self.by_name(servers)[("claude", "user", "docs-remote")]
        # Host and port survive redaction so the user can still see where it points.
        self.assertIn("mcp.example.test:8443", remote["command"])
        self.assertIn("region=eu", remote["command"])

    def test_secret_findings_cover_env_headers_urls_and_args_but_not_env_refs(self):
        findings = config.secret_findings(config.discover_servers())
        labels = {(f["server"], f["var"]) for f in findings}
        self.assertIn(("my-tools", "MY_TOOLS_TOKEN"), labels)
        self.assertIn(("docs-remote", "headers.Authorization"), labels)
        self.assertIn(("docs-remote", "url"), labels)
        self.assertIn(("memory", "args.3"), labels)
        self.assertFalse(any(f["server"] == "fetch" for f in findings),
                         "an $env: reference is not a plaintext secret")
        self.assertNotIn(("my-tools", "LOG_LEVEL"), labels)
        previews = json.dumps([f["preview"] for f in findings])
        for value in PLAINTEXT_VALUES:
            self.assertNotIn(value, previews)


class TestShapeHelpers(unittest.TestCase):
    def test_match_token_prefers_the_most_distinctive_argument(self):
        self.assertEqual(config.match_token(
            {"command": "npx", "args": ["-y", "@scope/pkg", "/a/longer/path"]}),
            "/a/longer/path")
        self.assertEqual(config.match_token(
            {"command": "python", "args": ["-m", "server.py"]}), "server.py")
        self.assertEqual(config.match_token(
            {"command": "/opt/bin/custom-server", "args": ["--port", "1"]}),
            "/opt/bin/custom-server")
        self.assertEqual(config.match_token({"command": "uvx", "args": ["mcp-server-fetch"]}),
                         "mcp-server-fetch")
        self.assertIsNone(config.match_token({"url": "https://x.test/mcp"}))

    def test_server_transport_and_command(self):
        self.assertEqual(config.server_transport({"type": "SSE", "url": "u"}), "sse")
        self.assertEqual(config.server_transport({"httpUrl": "https://x.test"}), "http")
        self.assertEqual(config.server_transport({"command": "node"}), "stdio")
        self.assertEqual(config.server_command({"command": "node", "args": ["a.js", 3]}),
                         "node a.js 3")
        self.assertEqual(config.server_command({"httpUrl": "https://x.test"}), "https://x.test")

    def test_env_references_are_not_treated_as_secrets(self):
        for ref in ("$TOKEN", "${GITHUB_TOKEN}", "$env:API_KEY", "%API_KEY%"):
            self.assertTrue(config._is_env_reference(ref), ref)
            self.assertFalse(config._looks_secret("API_KEY", ref), ref)
        self.assertTrue(config._looks_secret("API_KEY", "abcdefgh12"))
        self.assertTrue(config._looks_secret("", "sk-abcdefghijkl"))
        self.assertFalse(config._looks_secret("API_KEY", "short"))
        self.assertFalse(config._looks_secret("PROJECT_PATH", "/a/long/path/here"))

    def test_redact_args_handles_split_and_joined_options(self):
        out, findings = config._redact_args(
            ["--api-key", "value-one-123", "--token=value-two-456", "plain", "--port", "8"])
        self.assertEqual(out, ["--api-key", "<redacted>", "--token=<redacted>",
                               "plain", "--port", "8"])
        self.assertEqual([i for i, _ in findings], [1, 2])


class TestProfilesFromFixture(TempHomeCase):
    def test_load_profiles_keeps_only_named_lists(self):
        shutil.copy(FIXTURES / "profiles.json", config.PROFILES_PATH)
        self.assertEqual(config.load_profiles(),
                         {"writing": ["filesystem", "fetch"], "empty": []})

    def test_missing_profiles_file_is_seeded_with_defaults(self):
        self.assertFalse(Path(config.PROFILES_PATH).exists())
        profiles = config.load_profiles()
        self.assertIn("coding", profiles)
        self.assertNotIn("_help", profiles)
        saved = json.loads(Path(config.PROFILES_PATH).read_text(encoding="utf-8"))
        self.assertEqual(saved, config.DEFAULT_PROFILES)


if __name__ == "__main__":
    unittest.main()
