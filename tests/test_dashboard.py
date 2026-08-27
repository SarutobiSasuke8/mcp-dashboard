"""Tests for the MCP Dashboard.

Standard library only: `python -m unittest discover -s tests` from the
project root, or `python tests/test_dashboard.py`.

The suite covers the parts that would do damage if wrong — config edits,
process matching, usage counting — plus the regressions found while
building: the Codex TOML remover truncating at a bracket inside an args
array, shells being counted as MCP servers, and one SKILL.md being listed
twice under two roots.
"""

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from mcpdash import analysis, config, probe, usage  # noqa: E402
from mcpdash.common import load_toml  # noqa: E402

MB = 1024 * 1024


class TempHomeCase(unittest.TestCase):
    """Runs each test against a throwaway HOME and side-file directory.

    Isolation is belt and braces, because these tests exercise code that
    edits real agent config files:

    - ``Path.home`` is patched directly. Setting the HOME env var is not
      enough — on Windows ``Path.home()`` resolves via USERPROFILE, so an
      env-only sandbox silently leaks every mutation onto the real machine.
    - HOME, USERPROFILE, CODEX_HOME, and GEMINI_HOME all point inside the
      sandbox for any code that reads them.
    - ``config.run_cli`` is stubbed to always fail, so no test can shell
      out to a real `claude`/`codex` CLI and mutate live config that way.
    """

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.home = self.root / "home"
        (self.home / ".claude").mkdir(parents=True)
        (self.home / ".codex").mkdir(parents=True)
        (self.home / ".gemini").mkdir(parents=True)
        self._env = {}
        for var, value in (("HOME", str(self.home)),
                           ("USERPROFILE", str(self.home)),
                           ("CODEX_HOME", str(self.home / ".codex")),
                           ("GEMINI_HOME", str(self.home / ".gemini"))):
            self._env[var] = os.environ.get(var)
            os.environ[var] = value
        home = self.home
        self._patchers = [
            mock.patch.object(Path, "home", classmethod(lambda cls: home)),
            mock.patch.object(config, "run_cli",
                              lambda *a, **k: (False, "CLI disabled in tests")),
        ]
        for p in self._patchers:
            p.start()
        # Side files live next to the script; point them into the sandbox.
        self._patched = {}
        for mod, names in ((config, ("DISABLED_PATH", "PROVENANCE_PATH",
                                     "PROFILES_PATH")),):
            for name in names:
                self._patched[(mod, name)] = getattr(mod, name)
                setattr(mod, name, self.root / f"{name.lower()}.json")

    def tearDown(self):
        for (mod, name), value in self._patched.items():
            setattr(mod, name, value)
        for p in self._patchers:
            p.stop()
        for var, old in self._env.items():
            if old is None:
                os.environ.pop(var, None)
            else:
                os.environ[var] = old
        self.tmp.cleanup()

    def write_claude(self, data):
        (self.home / ".claude.json").write_text(json.dumps(data), encoding="utf-8")

    def write_codex(self, text):
        (self.home / ".codex" / "config.toml").write_text(text, encoding="utf-8")


class TestDiscovery(TempHomeCase):
    def test_finds_servers_across_agents_and_scopes(self):
        self.write_claude({
            "mcpServers": {"fs": {"command": "npx", "args": ["-y", "@modelcontextprotocol/server-filesystem"]}},
            "projects": {"/proj": {"mcpServers": {"local1": {"command": "node", "args": ["/proj/s.js"]}}}}})
        self.write_codex('[mcp_servers.mem]\ncommand = "npx"\nargs = ["-y", "x"]\n')
        (self.home / ".gemini" / "settings.json").write_text(
            json.dumps({"mcpServers": {"fetch": {"command": "uvx", "args": ["mcp-server-fetch"]}}}),
            encoding="utf-8")

        found = {(s["agent"], s["name"], s["scope"]) for s in config.discover_servers()}
        self.assertIn(("claude", "fs", "user"), found)
        self.assertIn(("claude", "local1", "local"), found)
        self.assertIn(("codex", "mem", "user"), found)
        self.assertIn(("gemini", "fetch", "user"), found)

    def test_transport_and_command_shapes(self):
        self.write_claude({"mcpServers": {
            "remote": {"type": "http", "url": "https://example.test/mcp"},
            "implied": {"url": "https://example.test/sse"},
            "std": {"command": "node", "args": ["a.js"]}}})
        by_name = {s["name"]: s for s in config.discover_servers()}
        self.assertEqual(by_name["remote"]["transport"], "http")
        self.assertEqual(by_name["implied"]["transport"], "http")
        self.assertEqual(by_name["std"]["transport"], "stdio")
        self.assertEqual(by_name["std"]["command"], "node a.js")


class TestProvenance(TempHomeCase):
    def label(self, cfg, overrides=None):
        entry = {"name": cfg.get("_name", "srv"), "raw": cfg}
        return config.detect_provenance(entry, overrides or {})[0]

    def test_official_vendor_community(self):
        self.assertEqual(self.label({"command": "npx", "args": ["-y", "@modelcontextprotocol/server-memory"]}), "official")
        self.assertEqual(self.label({"command": "npx", "args": ["-y", "@playwright/mcp@latest"]}), "vendor")
        self.assertEqual(self.label({"command": "uvx", "args": ["mcp-obsidian-community/thing"]}), "community")

    def test_local_script_is_self_built(self):
        self.assertEqual(self.label({"command": "python", "args": ["/home/me/mcp/server.py"]}), "self-built")
        self.assertEqual(self.label({"command": "node", "args": ["/home/me/tools/s.js"]}), "self-built")

    def test_node_modules_script_is_not_self_built(self):
        self.assertNotEqual(
            self.label({"command": "node", "args": ["/x/node_modules/pkg/dist/index.js"]}),
            "self-built")

    def test_remote_and_manual_override(self):
        self.assertEqual(self.label({"url": "https://x.test/mcp"}), "remote")
        self.assertEqual(
            self.label({"command": "npx", "args": ["-y", "@modelcontextprotocol/x"]},
                       {"srv": "self-built"}), "self-built")


class TestSecrets(TempHomeCase):
    def test_flags_plaintext_and_skips_env_references(self):
        servers = [
            {"name": "a", "agent": "claude", "origin": "~/.claude.json",
             "raw": {"env": {"VAULT_API_KEY": "sk-live-abcdef123456"}}},
            {"name": "b", "agent": "claude", "origin": "~/.claude.json",
             "raw": {"env": {"API_TOKEN": "${MY_TOKEN}"}}},
            {"name": "c", "agent": "claude", "origin": "~/.claude.json",
             "raw": {"env": {"LOG_LEVEL": "debug"}}},
            {"name": "d", "agent": "codex", "origin": "~/.codex/config.toml",
             "raw": {"env": {"NODE_REPL_NODE_PATH": r"C:\Tools\node.exe",
                             "GH_PAT": "ghp_abcdef1234567890"}}},
        ]
        found = config.secret_findings(servers)
        self.assertEqual([f["server"] for f in found], ["a", "d"])
        self.assertEqual([f["var"] for f in found if f["server"] == "d"],
                         ["GH_PAT"])  # _PATH vars are paths, not secrets
        self.assertNotIn("abcdef123456", json.dumps(found))  # never echoed whole


class TestCodexToml(TempHomeCase):
    SAMPLE = ('model = "gpt-5"\n\n[mcp_servers.memory]\ncommand = "npx"\n'
              'args = ["-y", "@modelcontextprotocol/server-memory"]\n\n'
              '[mcp_servers.memory.env]\nTOKEN = "abc123456789"\n\n'
              '[mcp_servers.keep]\ncommand = "uvx"\nargs = ["k", "[odd]"]\n')

    def test_remove_does_not_truncate_at_bracket_in_args(self):
        self.write_codex(self.SAMPLE)
        ok, msg = config.codex_disable({"name": "memory"})
        self.assertTrue(ok, msg)
        text = (self.home / ".codex" / "config.toml").read_text(encoding="utf-8")
        self.assertNotIn("memory", text)
        self.assertNotIn("server-memory", text)      # the args line went too
        self.assertIn('model = "gpt-5"', text)
        self.assertIn("[mcp_servers.keep]", text)
        self.assertIn('args = ["k", "[odd]"]', text)

    def test_disable_then_enable_round_trips(self):
        self.write_codex(self.SAMPLE)
        original = load_toml(self.home / ".codex" / "config.toml")["mcp_servers"]["memory"]
        config.codex_disable({"name": "memory"})
        config.codex_enable({"name": "memory", "raw": original})
        restored = load_toml(self.home / ".codex" / "config.toml")["mcp_servers"]["memory"]
        self.assertEqual(restored["command"], original["command"])
        self.assertEqual(list(restored["args"]), list(original["args"]))
        self.assertEqual(restored["env"]["TOKEN"], "abc123456789")

    def test_enable_fallback_writes_valid_toml_for_windows_paths(self):
        # Backslashes are escapes inside TOML basic strings, so appending a
        # Windows-path command as "C:\Users\..." corrupts config.toml.
        self.write_codex('model = "gpt-5"\n')
        cfg = {"command": "C:\\Tools\\srv.exe",
               "args": ["--dir", "C:\\Users\\me\\data"],
               "env": {"KEY": 'va"lue'}}
        ok, msg = config.codex_enable({"name": "winsrv", "raw": cfg})
        self.assertTrue(ok, msg)
        data = load_toml(self.home / ".codex" / "config.toml")
        srv = data["mcp_servers"]["winsrv"]
        self.assertEqual(srv["command"], "C:\\Tools\\srv.exe")
        self.assertEqual(list(srv["args"]), ["--dir", "C:\\Users\\me\\data"])
        self.assertEqual(srv["env"]["KEY"], 'va"lue')

    def test_fallback_toml_parser_matches_shape(self):
        self.write_codex(self.SAMPLE)
        data = load_toml(self.home / ".codex" / "config.toml")
        self.assertEqual(data["mcp_servers"]["keep"]["args"], ["k", "[odd]"])

    def test_fallback_parser_handles_literal_and_basic_strings(self):
        # Run the no-tomllib parser directly — on 3.11+ tomllib would
        # otherwise mask its bugs (which is exactly what happened with
        # literal strings on Python 3.10).
        from mcpdash.common import parse_toml_fallback
        text = ("[mcp_servers.win]\n"
                "command = 'C:\\Tools\\srv.exe'\n"
                "args = ['--dir', 'C:\\Users\\me\\data', \"esc\\\"aped\"]\n"
                "url = \"https://x.test/mcp\"\n")
        data = parse_toml_fallback(text)
        srv = data["mcp_servers"]["win"]
        self.assertEqual(srv["command"], "C:\\Tools\\srv.exe")
        self.assertEqual(srv["args"],
                         ["--dir", "C:\\Users\\me\\data", 'esc"aped'])
        self.assertEqual(srv["url"], "https://x.test/mcp")
        try:
            import tomllib
            self.assertEqual(data, tomllib.loads(text))
        except ImportError:
            pass


class TestToggleAndProfiles(TempHomeCase):
    def setUp(self):
        super().setUp()
        self.write_claude({"mcpServers": {
            "a": {"command": "node", "args": ["/a.js"]},
            "b": {"command": "node", "args": ["/b.js"]}}})

    def test_disable_stashes_and_enable_restores(self):
        servers = config.discover_servers()
        a = next(s for s in servers if s["name"] == "a")
        ok, msg = config.set_enabled(a, False)
        self.assertTrue(ok, msg)
        cfg = json.loads((self.home / ".claude.json").read_text(encoding="utf-8"))
        self.assertNotIn("a", cfg["mcpServers"])
        self.assertIn("b", cfg["mcpServers"])

        again = config.discover_servers()
        stashed = next(s for s in again if s["name"] == "a")
        self.assertFalse(stashed["enabled"])
        ok, msg = config.set_enabled(stashed, True)
        self.assertTrue(ok, msg)
        cfg = json.loads((self.home / ".claude.json").read_text(encoding="utf-8"))
        self.assertEqual(cfg["mcpServers"]["a"]["args"], ["/a.js"])

    def test_direct_config_edit_backs_up_first(self):
        # The CLI path manages its own config; this covers the fallback that
        # edits the file ourselves, which must never write without a backup.
        ok, msg = config._json_file_remove(self.home / ".claude.json", "a")
        self.assertTrue(ok, msg)
        backups = list(self.home.glob(".claude.json.bak-*"))
        self.assertTrue(backups, "no backup written before editing config")
        restored = json.loads(backups[0].read_text(encoding="utf-8"))
        self.assertIn("a", restored["mcpServers"])

    def test_profile_enables_members_and_disables_others(self):
        config.PROFILES_PATH.write_text(json.dumps({"only-b": ["b"]}), encoding="utf-8")
        ok, msg = config.apply_profile("only-b", config.discover_servers())
        self.assertTrue(ok, msg)
        cfg = json.loads((self.home / ".claude.json").read_text(encoding="utf-8"))
        self.assertEqual(list(cfg["mcpServers"]), ["b"])

    def test_unknown_profile_is_rejected(self):
        ok, msg = config.apply_profile("nope", config.discover_servers())
        self.assertFalse(ok)
        self.assertIn("unknown profile", msg)


class TestProcessMatching(unittest.TestCase):
    def server(self, **kw):
        base = {"name": "playwright", "transport": "stdio", "enabled": True,
                "token": "@playwright/mcp", "key": "k",
                "raw": {"command": "npx", "args": ["-y", "@playwright/mcp"]}}
        base.update(kw)
        return base

    def test_counts_real_server_process_tree(self):
        procs = [
            {"pid": 10, "ppid": 1, "rss": 100 * MB, "cpu": 1.0,
             "cmdline": "node /x/node_modules/@playwright/mcp/index.js"},
            {"pid": 11, "ppid": 10, "rss": 50 * MB, "cpu": 0.5,
             "cmdline": "chromium --headless"},
        ]
        s = self.server()
        probe.measure_usage([s], procs)
        self.assertEqual(s["instances"], 1)
        self.assertEqual(s["ram_bytes"], 150 * MB)

    def test_shell_mentioning_a_server_is_not_counted(self):
        procs = [{"pid": 20, "ppid": 1, "rss": 30 * MB, "cpu": 0.0,
                  "cmdline": "bash -c 'echo @playwright/mcp >> notes.txt'"}]
        s = self.server()
        probe.measure_usage([s], procs)
        self.assertEqual(s["instances"], 0)
        self.assertEqual(s["ram_bytes"], 0)

    def test_editor_and_grep_are_not_counted(self):
        for cmd in ("vim /etc/@playwright/mcp.conf",
                    "grep -r @playwright/mcp .",
                    "code /home/me/@playwright/mcp"):
            s = self.server()
            probe.measure_usage([s], [{"pid": 30, "ppid": 1, "rss": 9 * MB,
                                       "cpu": 0.0, "cmdline": cmd}])
            self.assertEqual(s["ram_bytes"], 0, cmd)

    def test_disabled_and_remote_servers_are_skipped(self):
        procs = [{"pid": 40, "ppid": 1, "rss": 10 * MB, "cpu": 0.0,
                  "cmdline": "node @playwright/mcp"}]
        off = self.server(enabled=False)
        probe.measure_usage([off], procs)
        self.assertEqual(off["ram_bytes"], 0)
        remote = self.server(transport="http")
        probe.measure_usage([remote], procs)
        self.assertEqual(remote["ram_bytes"], 0)

    def test_multiple_sessions_count_as_multiple_instances(self):
        procs = [{"pid": p, "ppid": 1, "rss": 10 * MB, "cpu": 0.0,
                  "cmdline": "node @playwright/mcp"} for p in (50, 51, 52)]
        s = self.server()
        probe.measure_usage([s], procs)
        self.assertEqual(s["instances"], 3)
        self.assertEqual(s["ram_bytes"], 30 * MB)


class TestProbeHandshake(unittest.TestCase):
    SERVER = (
        "import json,sys\n"
        "for line in sys.stdin:\n"
        "    line=line.strip()\n"
        "    if not line: continue\n"
        "    m=json.loads(line)\n"
        "    if m.get('method')=='initialize':\n"
        "        print(json.dumps({'jsonrpc':'2.0','id':m['id'],'result':{}}),flush=True)\n"
        "    elif m.get('method')=='tools/list':\n"
        "        tools=[{'name':'t%d'%i,'description':'d'*40,"
        "'inputSchema':{'type':'object'}} for i in range(5)]\n"
        "        print(json.dumps({'jsonrpc':'2.0','id':m['id'],"
        "'result':{'tools':tools}}),flush=True)\n")

    def test_lists_tools_and_estimates_context(self):
        with tempfile.TemporaryDirectory() as td:
            script = Path(td) / "srv.py"
            script.write_text(self.SERVER, encoding="utf-8")
            res = probe.probe_server({"command": sys.executable,
                                      "args": [str(script)]}, timeout=20)
        self.assertTrue(res["ok"], res["error"])
        self.assertEqual(res["tools"], 5)
        self.assertGreater(res["tokens"], 0)
        self.assertIsNotNone(res["ms"])

    def test_failure_reports_exit_code_and_stderr(self):
        res = probe.probe_server(
            {"command": sys.executable,
             "args": ["-c", "import sys; sys.stderr.write('KEY missing\\n');"
                            " sys.exit(3)"]}, timeout=15)
        self.assertFalse(res["ok"])
        self.assertIn("3", res["error"])
        self.assertIn("KEY missing", res["error"])

    def test_missing_binary_does_not_raise(self):
        res = probe.probe_server({"command": "definitely-not-a-real-binary-xyz"},
                                 timeout=5)
        self.assertFalse(res["ok"])
        self.assertIn("failed to start", res["error"])


class TestUsage(unittest.TestCase):
    def write_transcript(self, root, project, records):
        d = root / project
        d.mkdir(parents=True, exist_ok=True)
        (d / "s.jsonl").write_text("\n".join(json.dumps(r) for r in records),
                                   encoding="utf-8")

    def call(self, name, when, extra=None):
        block = {"type": "tool_use", "name": name, "input": extra or {}}
        return {"timestamp": when, "message": {"role": "assistant",
                                               "content": [block]}}

    def test_counts_windows_projects_and_skills(self):
        import datetime
        now = datetime.datetime.now()
        recent = (now - datetime.timedelta(days=2)).isoformat()
        old = (now - datetime.timedelta(days=200)).isoformat()
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "projects"
            self.write_transcript(root, "-home-me-vault", [
                self.call("mcp__filesystem__read_file", recent),
                self.call("mcp__filesystem__read_file", recent),
                self.call("mcp__playwright__navigate", old),
                self.call("Skill", recent, {"skill": "asv"}),
                self.call("Bash", recent),
            ])
            servers, skills = usage.collect_usage(
                claude_root=root, codex_root=Path(td) / "none", use_cache=False)
        self.assertEqual(servers["filesystem"]["calls_30d"], 2)
        self.assertEqual(servers["playwright"]["calls_30d"], 0)
        self.assertEqual(servers["playwright"]["calls"], 1)
        self.assertEqual(servers["filesystem"]["projects"], {"vault": 2})
        self.assertEqual(servers["filesystem"]["tools"], {"read_file": 2})
        self.assertEqual(skills["asv"]["calls_30d"], 1)
        self.assertNotIn("bash", servers)

    def test_utc_timestamps_are_converted_not_truncated(self):
        import datetime
        stamp = (datetime.datetime.now(datetime.timezone.utc)
                 - datetime.timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "projects"
            self.write_transcript(root, "-p", [self.call("mcp__x__y", stamp)])
            servers, _ = usage.collect_usage(claude_root=root,
                                             codex_root=Path(td) / "none",
                                             use_cache=False)
        self.assertEqual(servers["x"]["calls_30d"], 1)

    def test_cache_reuses_unchanged_files(self):
        import datetime
        now = datetime.datetime.now().isoformat()
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "projects"
            self.write_transcript(root, "-p", [self.call("mcp__a__b", now)])
            cache_path = Path(td) / "cache.json"
            original = usage.CACHE_PATH
            usage.CACHE_PATH = cache_path
            try:
                first, _ = usage.collect_usage(claude_root=root,
                                               codex_root=Path(td) / "none")
                calls = {"n": 0}
                real = usage.parse_claude_file

                def counting(path):
                    calls["n"] += 1
                    return real(path)

                usage.parse_claude_file = counting
                second, _ = usage.collect_usage(claude_root=root,
                                                codex_root=Path(td) / "none")
                usage.parse_claude_file = real
            finally:
                usage.CACHE_PATH = original
        self.assertEqual(first["a"]["calls"], second["a"]["calls"])
        self.assertEqual(calls["n"], 0, "unchanged transcript was re-parsed")


class TestVerdictsAndRecommendations(unittest.TestCase):
    def server(self, **kw):
        base = {"name": "srv", "key": "claude::user::srv", "agent": "claude",
                "scope": "user", "transport": "stdio", "enabled": True,
                "status": "running", "ram_bytes": 0, "ctx_tokens": 0,
                "calls": 0, "calls_30d": 0, "last_used": None,
                "projects_used": {}, "raw": {}}
        base.update(kw)
        return base

    def test_verdicts(self):
        self.assertEqual(analysis.verdict(self.server(enabled=False)), "disabled")
        self.assertEqual(analysis.verdict(self.server(status="failed")), "broken")
        self.assertEqual(analysis.verdict(self.server(ram_bytes=300 * MB)), "unused")
        self.assertEqual(analysis.verdict(self.server(calls=9, calls_30d=0)), "dormant")
        self.assertEqual(analysis.verdict(self.server(calls=9, calls_30d=1,
                                                      ram_bytes=400 * MB)), "expensive")
        self.assertEqual(analysis.verdict(self.server(calls=9, calls_30d=9)), "earning")
        self.assertEqual(analysis.verdict(self.server()), "quiet")

    def test_new_servers_get_a_grace_period(self):
        import datetime
        fresh = (datetime.datetime.now() - datetime.timedelta(days=2)).isoformat()
        aged = (datetime.datetime.now() - datetime.timedelta(days=40)).isoformat()
        s = self.server(ram_bytes=300 * MB)
        self.assertEqual(analysis.verdict(s, {"first_seen": fresh}), "quiet")
        self.assertEqual(analysis.verdict(s, {"first_seen": aged}), "unused")

    def test_recommendations_rank_and_estimate_savings(self):
        servers = [
            self.server(name="dead", key="k1", status="failed",
                        probe_error="exited with code 1", ram_bytes=70 * MB),
            self.server(name="idle", key="k2", ram_bytes=400 * MB),
            self.server(name="busy", key="k3", calls=90, calls_30d=40,
                        ram_bytes=100 * MB),
        ]
        recs = analysis.recommendations(servers, [], {"servers": {}})
        titles = [r["title"] for r in recs]
        self.assertTrue(recs[0]["severity"] == "high")
        self.assertTrue(any("dead" in t for t in titles))
        self.assertTrue(any("idle" in t for t in titles))
        self.assertFalse(any("busy" in t for t in titles))
        t = analysis.totals(servers, recs)
        self.assertEqual(t["reclaimable"], 470 * MB)

    def test_single_project_server_gets_scope_advice(self):
        s = self.server(calls=20, calls_30d=20, projects_used={"vault": 20})
        recs = analysis.recommendations([s], [], {"servers": {}})
        self.assertTrue(any("only used in vault" in r["title"] for r in recs))

    def test_disabled_servers_produce_no_recommendations(self):
        s = self.server(enabled=False, ram_bytes=900 * MB)
        self.assertEqual(analysis.recommendations([s], [], {"servers": {}}), [])


class TestSkillFindings(unittest.TestCase):
    def test_shadowing_is_reported_with_the_winner_first(self):
        skills = [{"name": "asv", "source": "vault"},
                  {"name": "asv", "source": "plugin:old"},
                  {"name": "solo", "source": "user"}]
        shadowed = analysis.skill_findings(skills, {"asv": {"calls": 3, "calls_30d": 1}})
        self.assertEqual(len(shadowed), 1)
        self.assertEqual(shadowed[0]["winner"], "vault")
        self.assertEqual(shadowed[0]["others"], ["plugin:old"])
        self.assertEqual(skills[0]["calls_30d"], 1)
        self.assertEqual(skills[1].get("shadowed_by"), "vault")


class TestRendering(unittest.TestCase):
    def test_demo_page_renders_all_views(self):
        from mcpdash import render
        from mcpdash.demo import demo_data
        servers, skills, history, extra = demo_data()
        recs = analysis.recommendations(servers, [], {"servers": {}})
        html = render.render_html(servers, skills, history, recs, [], [],
                                  {"when": "now", "host": "test", **extra})
        for marker in ("view-mcp", "view-advisor", "view-skills",
                       "MCP Server Dashboard", "prefers-color-scheme"):
            self.assertIn(marker, html)
        self.assertNotIn("__TOKEN__", html)

    def test_html_is_escaped(self):
        from mcpdash import render
        evil = {"name": "<script>x</script>", "key": "k", "agent": "claude",
                "scope": "user", "transport": "stdio", "enabled": True,
                "status": "idle", "command": "node <img onerror=1>",
                "provenance": "unknown", "ram_bytes": 0, "ctx_tokens": 0,
                "calls_30d": 0, "instances": 0, "cpu_pct": None,
                "verdict": "quiet"}
        html = render.render_html([evil], [], [], [], [], [],
                                  {"when": "now", "host": "t"})
        self.assertNotIn("<script>x</script>", html)
        self.assertIn("&lt;script&gt;", html)


class TestVaultOutputs(unittest.TestCase):
    def test_note_block_is_replaced_not_duplicated(self):
        from mcpdash import vaultout
        with tempfile.TemporaryDirectory() as td:
            note = Path(td) / "MCP Directory.md"
            reg = {"last_scan": "2026-08-24T10:00:00", "servers": {
                "claude::user::a": {"name": "a", "agent": "claude", "scope": "user",
                                    "last_seen": "2026-08-24T10:00:00",
                                    "last_ram_mb": 10, "peak_ram_mb": 12,
                                    "first_seen": "2026-08-01T10:00:00"}}}
            vaultout.write_directory_note(note, reg, [], "2026-08-24T10:00:00")
            first = note.read_text(encoding="utf-8")
            note.write_text(first + "\n## My own notes\n\nKeep me.\n", encoding="utf-8")
            reg["last_scan"] = "2026-08-25T10:00:00"
            vaultout.write_directory_note(note, reg, [], "2026-08-25T10:00:00")
            second = note.read_text(encoding="utf-8")
        self.assertEqual(second.count(vaultout.NOTE_BEGIN), 1)
        self.assertIn("Keep me.", second)
        self.assertIn("2026-08-25", second)

    def test_tasks_are_appended_once(self):
        from mcpdash import vaultout
        recs = [{"severity": "high", "action": "disable", "key": "k",
                 "title": "srv: never used", "detail": "costs 400 MB.",
                 "saving_bytes": 0},
                {"severity": "low", "action": "review", "key": "k2",
                 "title": "ignore me", "detail": "x", "saving_bytes": 0}]
        with tempfile.TemporaryDirectory() as td:
            inbox = Path(td) / "Inbox.md"
            inbox.write_text("# Inbox\n\n- [ ] existing task #task\n", encoding="utf-8")
            first = vaultout.append_tasks(recs, "2026-08-24T10:00:00", path=inbox)
            second = vaultout.append_tasks(recs, "2026-08-24T11:00:00", path=inbox)
            text = inbox.read_text(encoding="utf-8")
        self.assertEqual(len(first), 1)
        self.assertEqual(second, [])
        self.assertIn("existing task", text)
        self.assertIn("#task #inbox", text)
        self.assertNotIn("ignore me", text)

    def test_missing_inbox_is_left_alone(self):
        from mcpdash import vaultout
        with tempfile.TemporaryDirectory() as td:
            missing = Path(td) / "nope.md"
            self.assertEqual(vaultout.append_tasks([], "2026-08-24T10:00:00",
                                                   path=missing), [])
            self.assertFalse(missing.exists())


class TestBackupPruning(unittest.TestCase):
    def test_keeps_newest_n_and_spares_manual_backups(self):
        from mcpdash.common import backup_file
        with tempfile.TemporaryDirectory() as td:
            target = Path(td) / "config.json"
            target.write_text("{}", encoding="utf-8")
            # Twelve old tool-made backups plus two hand-made ones.
            for i in range(12):
                (Path(td) / f"config.json.bak-202601{i + 10:02d}-120000")\
                    .write_text("old", encoding="utf-8")
            manual = [Path(td) / "config.json.bak-2026-08-23",
                      Path(td) / "config.json.bak-pre-restore"]
            for m in manual:
                m.write_text("mine", encoding="utf-8")
            backup_file(target, keep=10)
            ours = sorted(p.name for p in Path(td).glob("config.json.bak-*")
                          if p not in manual)
            self.assertEqual(len(ours), 10)
            self.assertNotIn("config.json.bak-20260110-120000", ours)
            self.assertNotIn("config.json.bak-20260111-120000", ours)
            for m in manual:
                self.assertTrue(m.exists(), f"{m.name} was pruned")


class TestAtomicWrite(unittest.TestCase):
    def test_write_replaces_without_leaving_temp_files(self):
        from mcpdash.common import atomic_write
        with tempfile.TemporaryDirectory() as td:
            target = Path(td) / "sub" / "f.json"
            atomic_write(target, '{"a": 1}')
            atomic_write(target, '{"a": 2}')
            self.assertEqual(json.loads(target.read_text(encoding="utf-8")), {"a": 2})
            self.assertEqual([p.name for p in target.parent.iterdir()], ["f.json"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
