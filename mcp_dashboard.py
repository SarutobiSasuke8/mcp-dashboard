#!/usr/bin/env python3
"""MCP Server Dashboard — cost and benefit of your MCP toolbox.

Scans MCP server configuration for Claude Code, OpenAI Codex, Gemini CLI,
and Cursor; measures RAM and CPU of running stdio servers; reads real tool
usage from agent transcripts; optionally probes each server for its tool
count, context-token cost, and startup time; weighs cost against use into
recommendations; and lists every installed skill in a separate view.

    python mcp_dashboard.py                 scan and write the dashboard
    python mcp_dashboard.py --open          ...and open it
    python mcp_dashboard.py --probe         also measure context cost/startup
    python mcp_dashboard.py --serve         live dashboard with working toggles
    python mcp_dashboard.py --report        append a snapshot to the vault report
    python mcp_dashboard.py --tasks         file high-severity findings as tasks
    python mcp_dashboard.py --profile NAME  apply a profile from mcp-profiles.json
    python mcp_dashboard.py --demo          render sample data

Outputs land in Obsidian Vault Management/Systems/; machine-local state
(registry, history, probe cache, disabled stash) sits next to this script.
"""

import argparse
import datetime
import json
import platform
import sys
import webbrowser
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from mcpdash import analysis, config, probe, render, skills, usage, vaultout  # noqa: E402
from mcpdash.common import (DEFAULT_HTML, DEFAULT_NOTE, DISABLED_PATH,  # noqa: E402
                            PROBE_CACHE_PATH, PROFILES_PATH, PROVENANCE_PATH,
                            fmt_mb, fmt_tokens, has_psutil, load_json, save_json)
from mcpdash.demo import demo_data  # noqa: E402


def ensure_side_files():
    if not PROVENANCE_PATH.exists():
        save_json(PROVENANCE_PATH, {
            "_help": ("Label server provenance here; keys are server names. "
                      "Values: self-built | official | vendor | community, or "
                      "{\"provenance\": \"self-built\", \"note\": \"...\"}. "
                      "Manual labels beat auto-detection."),
            "_example-my-server": "self-built"})
    config.load_profiles()  # writes defaults on first run


def scan(use_cli=True, do_probe=False, probe_timeout=25):
    """Full scan: config, processes, usage, probe cache, verdicts."""
    servers = config.discover_servers()
    status = {} if not use_cli else claude_status()
    probe.measure_usage(servers, probe.list_processes())
    if do_probe:
        probe.probe_all(servers, timeout=probe_timeout)
    probe.attach_probe(servers)
    usage.attach_usage(servers, usage.collect_usage()[0])

    for s in servers:
        if not s.get("enabled", True):
            s["status"] = "disabled"
        elif s["name"] in status and s["agent"] == "claude":
            s["status"] = status[s["name"]]
        elif s.get("probe_error"):
            s["status"] = "failed"
        elif s["transport"] != "stdio":
            s["status"] = "remote"
        elif s.get("instances", 0) > 0:
            s["status"] = "running"
        else:
            s["status"] = "idle"
    registry = load_json(vaultout.REGISTRY_PATH) or {}
    for s in servers:
        s["verdict"] = analysis.verdict(s, (registry.get("servers") or {}).get(s["key"]))
    return servers


def claude_status():
    import re
    from mcpdash.common import run_cli
    ok, out = run_cli(["claude", "mcp", "list"], timeout=60)
    status = {}
    for line in (out or "").splitlines():
        m = re.match(r"^\s*([\w./@-]+):\s+.*-\s*(.+)$", line)
        if not m:
            continue
        tail = m.group(2).lower()
        if "failed" in tail or "✗" in m.group(2):
            status[m.group(1)] = "failed"
        elif "connect" in tail or "✓" in m.group(2):
            status[m.group(1)] = "connected"
    return status


def build_page(servers, skill_list, history, meta, live=False):
    secrets = config.secret_findings(servers)
    registry = load_json(vaultout.REGISTRY_PATH) or {}
    recs = analysis.recommendations(servers, secrets, registry)
    server_usage, skill_usage = usage.collect_usage()
    shadowed = analysis.skill_findings(skill_list, skill_usage)
    html = render.render_html(servers, skill_list, history, recs, secrets,
                              shadowed, meta, profiles=config.load_profiles(),
                              live=live)
    return html, recs, secrets


# ---------------------------------------------------------------------------
# Serve
# ---------------------------------------------------------------------------

def serve(args):
    from http.server import HTTPServer, BaseHTTPRequestHandler

    state = {"servers": []}

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, fmt, *a):
            pass

        def _send(self, code, body, ctype="text/html; charset=utf-8"):
            data = body.encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def _json_body(self):
            length = int(self.headers.get("Content-Length", 0))
            return json.loads(self.rfile.read(length) or b"{}")

        def do_GET(self):
            if self.path.split("?")[0] not in ("/", "/index.html"):
                self._send(404, "not found", "text/plain")
                return
            now = datetime.datetime.now()
            now_iso = now.strftime("%Y-%m-%dT%H:%M:%S")
            do_probe = args.probe and not state.get("probed")
            servers = scan(use_cli=not args.no_cli, do_probe=do_probe,
                           probe_timeout=args.probe_timeout)
            state["servers"] = servers
            state["probed"] = True
            analysis.append_history(servers, now_iso)
            registry = vaultout.update_registry(servers, now_iso)
            vaultout.write_directory_note(args.note, registry, servers, now_iso)
            cache = load_json(PROBE_CACHE_PATH) or {}
            meta = {"when": now.strftime("%Y-%m-%d %H:%M"),
                    "host": platform.node() or platform.system(),
                    "psutil": has_psutil(),
                    "probe_at": max((v.get("at", "") for v in cache.values()),
                                    default="")}
            html, _, _ = build_page(servers, skills.discover_skills(),
                                    analysis.load_history(), meta, live=True)
            args.html.parent.mkdir(parents=True, exist_ok=True)
            args.html.write_text(html, encoding="utf-8")
            self._send(200, html)

        def do_POST(self):
            path = self.path.split("?")[0]
            try:
                body = self._json_body()
                if path == "/api/toggle":
                    ok, msg = config.toggle_server(body.get("key", ""), state["servers"])
                elif path == "/api/set":
                    entry = next((s for s in state["servers"]
                                  if s["key"] == body.get("key")), None)
                    if entry is None:
                        ok, msg = False, "unknown server"
                    else:
                        ok, msg = config.set_enabled(entry, bool(body.get("enabled")))
                elif path == "/api/profile":
                    ok, msg = config.apply_profile(body.get("name", ""),
                                                   state["servers"])
                else:
                    self._send(404, "{}", "application/json")
                    return
            except Exception as exc:  # pragma: no cover - defensive
                ok, msg = False, str(exc)
            self._send(200, json.dumps({"ok": ok, "message": msg}),
                       "application/json")

    httpd = HTTPServer(("127.0.0.1", args.port), Handler)
    url = f"http://127.0.0.1:{args.port}/"
    print(f"Live dashboard at {url}  (Ctrl+C to stop)")
    print(f"Toggles and profiles edit real config; disabled servers are stashed "
          f"in {DISABLED_PATH.name} so they can be switched back on.")
    if args.open:
        webbrowser.open(url)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(
        description="MCP Server Dashboard — cost and benefit of your MCP toolbox")
    ap.add_argument("--html", type=Path, default=DEFAULT_HTML)
    ap.add_argument("--note", type=Path, default=DEFAULT_NOTE)
    ap.add_argument("--demo", action="store_true", help="render sample data")
    ap.add_argument("--no-cli", action="store_true",
                    help="skip the `claude mcp list` health check (faster)")
    ap.add_argument("--probe", action="store_true",
                    help="start each server briefly to measure tool count, "
                         "context tokens, startup time, and real errors")
    ap.add_argument("--probe-timeout", type=int, default=25)
    ap.add_argument("--serve", action="store_true",
                    help="live dashboard with working toggles and profiles")
    ap.add_argument("--port", type=int, default=7817)
    ap.add_argument("--report", action="store_true",
                    help="append a snapshot to the vault usage report")
    ap.add_argument("--tasks", action="store_true",
                    help="file high-severity findings into Tasks/Inbox.md")
    ap.add_argument("--profile", metavar="NAME",
                    help="apply a profile from mcp-profiles.json and exit")
    ap.add_argument("--list-profiles", action="store_true")
    ap.add_argument("--open", action="store_true", help="open in a browser")
    args = ap.parse_args()

    ensure_side_files()

    if args.list_profiles:
        for name, members in sorted(config.load_profiles().items()):
            print(f"{name}: {', '.join(members) or '(none — disables everything)'}")
        return

    if args.profile:
        servers = scan(use_cli=False)
        ok, msg = config.apply_profile(args.profile, servers)
        print(("Applied" if ok else "Partly applied") + f" profile '{args.profile}': {msg}")
        return

    if args.serve and not args.demo:
        serve(args)
        return

    now = datetime.datetime.now()
    now_iso = now.strftime("%Y-%m-%dT%H:%M:%S")
    meta = {"when": now.strftime("%Y-%m-%d %H:%M"),
            "host": platform.node() or platform.system(),
            "demo": args.demo, "psutil": has_psutil()}

    if args.demo:
        servers, skill_list, history, meta_extra = demo_data()
        meta.update(meta_extra)
        secrets = config.secret_findings(servers)
        recs = analysis.recommendations(servers, secrets, {"servers": {}})
        shadowed = analysis.skill_findings(skill_list, {})
        html = render.render_html(servers, skill_list, history, recs, secrets,
                                  shadowed, meta,
                                  profiles=config.load_profiles(), live=False)
    else:
        if args.probe:
            print("Probing servers (starting each one briefly)…")
        servers = scan(use_cli=not args.no_cli, do_probe=args.probe,
                       probe_timeout=args.probe_timeout)
        by_agent = {}
        for s in servers:
            by_agent[s["agent"]] = by_agent.get(s["agent"], 0) + 1
        print(f"Found {len(servers)} MCP server(s): " +
              ", ".join(f"{n} {a}" for a, n in sorted(by_agent.items())) or "none")
        analysis.append_history(servers, now_iso)
        skill_list = skills.discover_skills()
        print(f"Found {len(skill_list)} skill(s).")
        cache = load_json(PROBE_CACHE_PATH) or {}
        meta["probe_at"] = max((v.get("at", "") for v in cache.values()), default="")
        html, recs, secrets = build_page(servers, skill_list,
                                         analysis.load_history(), meta)

    args.html.parent.mkdir(parents=True, exist_ok=True)
    args.html.write_text(html, encoding="utf-8")
    print(f"Dashboard -> {args.html}")

    if not args.demo:
        registry = vaultout.update_registry(servers, now_iso)
        vaultout.write_directory_note(args.note, registry, servers, now_iso)
        print(f"Directory note -> {args.note}")
        t = analysis.totals(servers, recs)
        print(f"Local MCP RAM: {fmt_mb(t['ram'])} · context ~{t['tokens'] or 0} "
              f"tokens · {t['calls30']} calls/30d · {t['high']} finding(s) needing "
              f"attention · {fmt_mb(t['reclaimable'])} reclaimable")
        if args.report:
            path = vaultout.append_report(servers, recs, t, now_iso)
            print(f"Usage report -> {path}")
        if args.tasks:
            written = vaultout.append_tasks(recs, now_iso)
            print(f"Tasks filed: {len(written)}")

    if args.open:
        webbrowser.open(args.html.as_uri())


if __name__ == "__main__":
    main()
