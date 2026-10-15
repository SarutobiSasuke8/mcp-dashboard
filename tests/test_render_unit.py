"""Focused unit tests for mcpdash/render.py.

Pure string rendering: inputs are small in-memory rows plus the history
fixture in ``tests/fixtures``. No real config, no network.
"""

import json
import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from mcpdash import render  # noqa: E402

FIXTURES = Path(__file__).resolve().parent / "fixtures"
MB = 1024 * 1024


def fixture_history():
    rows = []
    for line in (FIXTURES / "history.jsonl").read_text(encoding="utf-8").splitlines():
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return rows


def server(**kw):
    base = {"name": "srv", "key": "claude::user::srv", "agent": "claude",
            "scope": "user", "transport": "stdio", "enabled": True,
            "status": "idle", "command": "node srv.js", "provenance": "unknown",
            "ram_bytes": 0, "ctx_tokens": 0, "calls_30d": 0, "instances": 0,
            "cpu_pct": None, "verdict": "quiet"}
    base.update(kw)
    return base


META = {"when": "2026-10-15 00:00", "host": "fixture-host"}


class TestHistoryChart(unittest.TestCase):
    def test_fewer_than_two_points_shows_guidance(self):
        for history in ([], fixture_history()[:1]):
            html = render.svg_history_chart(history)
            self.assertIn("chart-empty", html)
            self.assertNotIn("<svg", html)

    def test_multi_day_history_uses_date_labels_and_latest_value(self):
        svg = render.svg_history_chart(fixture_history())
        self.assertTrue(svg.startswith("<svg"))
        self.assertIn("latest 140 megabytes", svg)
        for label in ("10-01", "10-02", "10-03"):
            self.assertIn(f">{label}</text>", svg)
        self.assertEqual(svg.count("<circle"), 3)
        self.assertEqual(svg.count('class="dot end"'), 1)
        # The y axis is rounded up to the next hundred above the peak.
        self.assertIn(">200</text>", svg)

    def test_same_day_history_uses_time_labels_and_escapes_timestamps(self):
        history = [{"ts": "2026-10-15T08:30:00<b>", "total_mb": 5},
                   {"ts": "2026-10-15T09:45:00", "total_mb": 7}]
        svg = render.svg_history_chart(history)
        self.assertIn(">08:30</text>", svg)
        self.assertIn(">09:45</text>", svg)
        self.assertNotIn("<b>", svg)
        self.assertIn("&lt;b&gt;", svg)


class TestSparklineAndBars(unittest.TestCase):
    def test_sparkline_needs_two_real_values(self):
        self.assertEqual(render.svg_sparkline([]), "")
        self.assertEqual(render.svg_sparkline([None, 3, None]), "")
        svg = render.svg_sparkline([1, None, 4, 2])
        points = re.search(r'points="([^"]+)"', svg).group(1).split()
        self.assertEqual(len(points), 3)
        self.assertTrue(points[0].startswith("0.0,"))
        self.assertTrue(points[-1].startswith("80.0,"))

    def test_hbar_list_scales_to_the_largest_value_and_escapes_labels(self):
        self.assertIn("No recorded activity yet", render.hbar_list([]))
        html = render.hbar_list([("<big>", 200, ""), ("small", 1, ""), ("mid", 50, "")],
                                unit=" MB")
        widths = re.findall(r"width:(\d+)%", html)
        self.assertEqual(widths, ["100", "1", "25"])
        self.assertIn("&lt;big&gt;", html)
        self.assertNotIn("<big>", html)
        self.assertIn(">200 MB<", html)


class TestPageSections(unittest.TestCase):
    def test_secret_previews_are_shown_and_escaped(self):
        secrets = [{"server": "my-tools", "agent": "claude", "origin": "~/.claude.json",
                    "var": "MY_<TOKEN>", "preview": "fix…01"}]
        html = render.render_html([], [], [], [], secrets, [], META)
        self.assertIn("Credentials in config", html)
        self.assertIn("MY_&lt;TOKEN&gt;", html)
        self.assertIn("fix…01", html)
        no_secrets = render.render_html([], [], [], [], [], [], META)
        self.assertNotIn("Credentials in config", no_secrets)

    def test_profiles_are_static_offline_and_buttons_when_live(self):
        profiles = {"writing": ["filesystem", "fetch"], "empty": []}
        static = render.render_html([], [], [], [], [], [], META, profiles=profiles)
        self.assertIn("writing (2)", static)
        self.assertIn("empty (0)", static)
        self.assertNotIn('data-profile="writing"', static)
        live = render.render_html([], [], [], [], [], [], META, profiles=profiles,
                                  live=True, token="fixture-nonce")
        self.assertIn('data-profile="writing"', live)
        self.assertIn("data-restore-last", live)
        self.assertNotIn("data-restore-last", static)

    def test_servers_get_status_verdict_and_provenance_labels(self):
        servers = [
            server(name="mine", key="k1", provenance="self-built", status="running",
                   verdict="earning", calls_30d=12, ram_bytes=40 * MB, instances=1),
            server(name="off", key="k2", enabled=False, verdict="disabled"),
            server(name="cloud", key="k3", transport="http", status="remote",
                   command="https://mcp.example.test/mcp", provenance="remote"),
        ]
        html = render.render_html(servers, [], fixture_history(), [], [], [], META)
        self.assertIn("earning its keep", html)
        self.assertIn(">yours<", html)
        self.assertIn("Disabled", html)
        self.assertIn("mcp.example.test", html)
        self.assertIn("fixture-host", html)
        self.assertNotIn("DEMO DATA", html)
        self.assertIn('data-key="k1"', render.render_html(
            servers, [], [], [], [], [], META, live=True, token="n"))
        self.assertNotIn('data-key="k1"', html)


if __name__ == "__main__":
    unittest.main()
