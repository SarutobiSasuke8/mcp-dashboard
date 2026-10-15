"""Focused unit tests for mcpdash/analysis.py.

History tests point ``analysis.HISTORY_PATH`` at a temporary file seeded from
``tests/fixtures/history.jsonl``; the real state directory is never read or
written. No network, no probes.
"""

import datetime
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from mcpdash import analysis  # noqa: E402

FIXTURES = Path(__file__).resolve().parent / "fixtures"
MB = 1024 * 1024


def server(**kw):
    base = {"name": "srv", "key": "claude::user::srv", "agent": "claude",
            "scope": "user", "transport": "stdio", "enabled": True,
            "status": "running", "ram_bytes": 0, "ctx_tokens": 0,
            "calls": 0, "calls_30d": 0, "last_used": None,
            "projects_used": {}, "raw": {}}
    base.update(kw)
    return base


class HistoryCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "history.jsonl"
        patcher = mock.patch.object(analysis, "HISTORY_PATH", self.path)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.addCleanup(self.tmp.cleanup)


class TestHistory(HistoryCase):
    def test_load_history_skips_blank_and_malformed_lines(self):
        shutil.copy(FIXTURES / "history.jsonl", self.path)
        rows = analysis.load_history()
        self.assertEqual([r["ts"][:10] for r in rows],
                         ["2026-10-01", "2026-10-02", "2026-10-03"])
        self.assertEqual(rows[1]["total_mb"], 150.5)

    def test_missing_history_file_is_empty(self):
        self.assertEqual(analysis.load_history(), [])

    def test_append_history_snapshot_shape(self):
        servers = [
            server(key="a", ram_bytes=int(10.04 * MB), ctx_tokens=1000),
            server(key="b", ram_bytes=5 * MB, ctx_tokens=500, enabled=False),
            server(key="c", ram_bytes=0, ctx_tokens=250),
        ]
        analysis.append_history(servers, "2026-10-15T00:00:00")
        snap = analysis.load_history()[-1]
        self.assertEqual(snap["ts"], "2026-10-15T00:00:00")
        self.assertEqual(snap["total_mb"], 15.0)
        # Disabled servers do not count towards context tokens.
        self.assertEqual(snap["total_tokens"], 1250)
        # Servers with no RAM sample are left out of the per-server map.
        self.assertEqual(snap["servers"], {"a": 10.0, "b": 5.0})

    def test_load_history_returns_only_the_latest_window(self):
        with open(self.path, "w", encoding="utf-8") as fh:
            for i in range(analysis.HISTORY_LIMIT + 15):
                fh.write(json.dumps({"ts": f"t{i}", "total_mb": i}) + "\n")
        rows = analysis.load_history()
        self.assertEqual(len(rows), analysis.HISTORY_LIMIT)
        self.assertEqual(rows[-1]["ts"], f"t{analysis.HISTORY_LIMIT + 14}")

    def test_trim_keeps_the_tail_once_the_file_grows_too_long(self):
        keep = 5
        lines = [json.dumps({"ts": f"t{i}"}) for i in range(keep * 2 + 1)]
        self.path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        analysis._trim_history(keep=keep)
        kept = self.path.read_text(encoding="utf-8").splitlines()
        self.assertEqual(kept, lines[-keep:])

    def test_trim_leaves_a_short_file_alone(self):
        lines = [json.dumps({"ts": f"t{i}"}) for i in range(10)]
        self.path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        analysis._trim_history(keep=5)
        self.assertEqual(self.path.read_text(encoding="utf-8").splitlines(), lines)


class TestVerdictBoundaries(unittest.TestCase):
    def test_probe_error_counts_as_broken(self):
        self.assertEqual(analysis.verdict(server(probe_error="timeout")), "broken")

    def test_cost_thresholds(self):
        # Exactly at the thresholds is not over them.
        self.assertEqual(analysis.verdict(server(ram_bytes=50 * MB)), "quiet")
        self.assertEqual(analysis.verdict(server(ctx_tokens=1501)), "unused")
        self.assertEqual(analysis.verdict(
            server(calls=5, calls_30d=2, ctx_tokens=6001)), "expensive")
        self.assertEqual(analysis.verdict(
            server(calls=5, calls_30d=3, ram_bytes=900 * MB)), "earning")
        self.assertEqual(analysis.verdict(
            server(calls=5, calls_30d=2, ram_bytes=250 * MB)), "earning")

    def test_settling_server_with_calls_still_gets_judged(self):
        fresh = (datetime.datetime.now() - datetime.timedelta(days=1)).isoformat()
        s = server(calls=4, calls_30d=0)
        self.assertEqual(analysis.verdict(s, {"first_seen": fresh}), "dormant")

    def test_verdict_order_covers_every_verdict(self):
        self.assertEqual(set(analysis.VERDICT_ORDER), {
            "broken", "unused", "expensive", "dormant", "quiet", "earning", "disabled"})


class TestRecommendationDetails(unittest.TestCase):
    def test_secret_findings_become_high_severity_items(self):
        secrets = [{"server": "my-tools", "agent": "claude", "origin": "~/.claude.json",
                    "var": "MY_TOOLS_TOKEN", "preview": "fix…01"}]
        recs = analysis.recommendations([], secrets, {})
        self.assertEqual(len(recs), 1)
        self.assertEqual((recs[0]["severity"], recs[0]["action"]), ("high", "secret"))
        self.assertIn("MY_TOOLS_TOKEN", recs[0]["detail"])
        self.assertIn("fix…01", recs[0]["detail"])

    def test_slow_start_and_cross_agent_duplicates_are_reported(self):
        servers = [
            server(name="Fetch", key="claude::user::fetch", calls=3, calls_30d=3,
                   probe_ms=4200),
            server(name="fetch", key="codex::user::fetch", agent="codex",
                   calls=3, calls_30d=3),
        ]
        recs = analysis.recommendations(servers, [], {"servers": {}})
        titles = [r["title"] for r in recs]
        self.assertIn("Fetch is slow to start", titles)
        self.assertIn("Fetch is configured for claude, codex", titles)
        slow = next(r for r in recs if r["title"] == "Fetch is slow to start")
        self.assertIn("4.2s", slow["detail"])

    def test_scope_advice_needs_stdio_user_scope_and_three_calls(self):
        base = dict(calls=10, projects_used={"alpha": 10})
        for kw in ({"calls_30d": 2}, {"calls_30d": 5, "scope": "project"},
                   {"calls_30d": 5, "transport": "http"}):
            recs = analysis.recommendations([server(**base, **kw)], [], {"servers": {}})
            self.assertFalse(any("only used in" in r["title"] for r in recs), kw)

    def test_results_are_sorted_by_severity_then_saving(self):
        servers = [
            server(name="small", key="k1", calls=9, calls_30d=0, ram_bytes=20 * MB),
            server(name="big", key="k2", calls=9, calls_30d=0, ram_bytes=90 * MB),
            server(name="huge-unused", key="k3", ram_bytes=300 * MB),
        ]
        recs = analysis.recommendations(servers, [], {"servers": {}})
        self.assertEqual([r["key"] for r in recs], ["k3", "k2", "k1"])
        self.assertEqual([r["severity"] for r in recs], ["high", "medium", "medium"])

    def test_totals_ignore_disabled_servers_and_review_savings(self):
        servers = [
            server(ram_bytes=100 * MB, ctx_tokens=1000, tools_count=4, calls_30d=7),
            server(ram_bytes=900 * MB, ctx_tokens=9000, tools_count=40, enabled=False),
        ]
        recs = [{"severity": "high", "action": "disable", "saving_bytes": 50 * MB},
                {"severity": "low", "action": "review", "saving_bytes": 70 * MB}]
        self.assertEqual(analysis.totals(servers, recs), {
            "ram": 100 * MB, "tokens": 1000, "tools": 4, "calls30": 7,
            "reclaimable": 50 * MB, "high": 1})


if __name__ == "__main__":
    unittest.main()
