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
import os
import platform
import secrets
import sys
import webbrowser
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from mcpdash import analysis, config, doctor, probe, render, skills, usage, vaultout  # noqa: E402
from mcpdash import __version__  # noqa: E402
from mcpdash.common import (DEFAULT_HTML, DEFAULT_NOTE, DISABLED_PATH,  # noqa: E402
                            PROBE_CACHE_PATH, PROVENANCE_PATH, atomic_write,
                            fmt_mb, has_psutil, load_json,
                            migrate_legacy_state, save_json)
from mcpdash.demo import demo_data  # noqa: E402


def ensure_side_files():
    migrated = migrate_legacy_state()
    if migrated:
        print("Migrated existing dashboard state to user storage:")
        for path in migrated:
            print(f"  {path}")
    if not PROVENANCE_PATH.exists():
        save_json(PROVENANCE_PATH, {
            "_help": ("Label server provenance here; keys are server names. "
                      "Values: self-built | official | vendor | community, or "
                      "{\"provenance\": \"self-built\", \"note\": \"...\"}. "
                      "Manual labels beat auto-detection."),
            "_example-my-server": "self-built"})
    config.load_profiles()  # writes defaults on first run


def scan(use_cli=True, do_probe=False, probe_timeout=25, include_usage=True):
    """Full scan: config, processes, usage, probe cache, verdicts.

    Returns (servers, skill_usage) — transcripts are parsed once per run and
    the skill half handed back, so nothing re-reads them downstream."""
    servers = config.discover_servers()
    status = {} if not use_cli else claude_status()
    probe.measure_usage(servers, probe.list_processes())
    if do_probe:
        probe.probe_all(servers, timeout=probe_timeout)
    probe.attach_probe(servers)
    if include_usage:
        server_usage, skill_usage = usage.collect_usage()
    else:
        server_usage, skill_usage = {}, {}
    usage.attach_usage(servers, server_usage)

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
    return servers, skill_usage


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


def build_page(servers, skill_list, skill_usage, history, meta, live=False,
               token=""):
    found = config.secret_findings(servers)
    registry = load_json(vaultout.REGISTRY_PATH) or {}
    recs = analysis.recommendations(servers, found, registry)
    shadowed = analysis.skill_findings(skill_list, skill_usage)
    html = render.render_html(servers, skill_list, history, recs, found,
                              shadowed, meta, profiles=config.load_profiles(),
                              live=live, token=token)
    return html, recs, found


def export_json(servers, skill_list, recs, totals_d, path):
    """Machine-readable snapshot for other tools, with configs redacted."""
    def clean(s):
        raw = config.redact_sensitive_config(s.get("raw") or {})
        return {k: v for k, v in
                {**s, "raw": raw, "command": config.server_command(raw)}.items()
                if k != "token"}

    payload = {
        "generated": datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        "totals": totals_d,
        "servers": [clean(s) for s in servers],
        "skills": skill_list,
        "recommendations": recs,
    }
    save_json(path, payload)
    return path


# ---------------------------------------------------------------------------
# Serve
# ---------------------------------------------------------------------------

def _make_http_server(args, token=None, nonce=None, cookie_name=None):
    """Build the authenticated loopback control surface.

    This endpoint edits real agent config, so it binds to loopback, rejects
    non-loopback Host headers, requires a per-run token, and applies strict
    browser response headers. Cross-origin pages cannot attach the custom
    mutation header without a CORS preflight, which this server never grants.
    """
    from http.server import HTTPServer, BaseHTTPRequestHandler

    token = token or secrets.token_urlsafe(16)
    nonce = nonce or secrets.token_urlsafe(16)
    # Cookies are host-scoped, not port-scoped. A per-run name prevents two
    # dashboard instances on different ports from invalidating each other.
    cookie_name = cookie_name or "mcp_dashboard_" + secrets.token_hex(6)
    state = {"servers": []}

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, fmt, *a):
            pass

        def _send(self, code, body, ctype="text/html; charset=utf-8",
                  establish_session=False):
            data = body.encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("X-Frame-Options", "DENY")
            self.send_header("Cross-Origin-Resource-Policy", "same-origin")
            if establish_session:
                self.send_header(
                    "Set-Cookie",
                    f"{cookie_name}={token}; HttpOnly; SameSite=Strict; Path=/")
            if ctype.startswith("text/html"):
                self.send_header(
                    "Content-Security-Policy",
                    "default-src 'none'; base-uri 'none'; form-action 'none'; "
                    "frame-ancestors 'none'; img-src 'self' data:; "
                    "font-src 'self'; style-src 'unsafe-inline'; "
                    f"script-src 'nonce-{nonce}'; connect-src 'self'")
            self.end_headers()
            self.wfile.write(data)

        def _json_body(self):
            length = min(int(self.headers.get("Content-Length", 0) or 0), 64_000)
            return json.loads(self.rfile.read(length) or b"{}")

        def _local(self):
            host = (self.headers.get("Host") or "").split(":")[0].strip("[]")
            if host not in ("127.0.0.1", "localhost", "::1", ""):
                return False
            return self.client_address[0] in ("127.0.0.1", "::1")

        def _authorised(self, mutation=False):
            if not self._local():
                return False
            if mutation:
                origin = self.headers.get("Origin", "")
                expected_origin = "http://" + (self.headers.get("Host") or "")
                if origin != expected_origin:
                    return False
                from http.cookies import SimpleCookie
                cookies = SimpleCookie()
                try:
                    cookies.load(self.headers.get("Cookie", ""))
                except Exception:
                    return False
                given = cookies.get(cookie_name)
                return bool(given) and secrets.compare_digest(given.value, token)
            from urllib.parse import parse_qs, urlparse
            given = parse_qs(urlparse(self.path).query).get("t", [""])[0]
            return secrets.compare_digest(given, token)

        def do_GET(self):
            if self.path.split("?")[0] not in ("/", "/index.html"):
                self._send(404, "not found", "text/plain")
                return
            if not self._authorised(mutation=False):
                self._send(403, "Forbidden — open the URL printed by the "
                                "command, which carries this run's token.",
                           "text/plain")
                return
            now = datetime.datetime.now()
            now_iso = now.strftime("%Y-%m-%dT%H:%M:%S")
            do_probe = args.probe and not state.get("probed")
            servers, skill_usage = scan(use_cli=not args.no_cli,
                                        do_probe=do_probe,
                                        probe_timeout=args.probe_timeout,
                                        include_usage=not getattr(args, "no_usage", False))
            state["servers"] = servers
            state["probed"] = True
            analysis.append_history(servers, now_iso)
            registry = vaultout.update_registry(servers, now_iso)
            vaultout.write_directory_note(args.note, registry, servers, now_iso)
            cache = load_json(PROBE_CACHE_PATH) or {}
            meta = {"when": now.strftime("%Y-%m-%d %H:%M"),
                    "host": platform.node() or platform.system(),
                    "version": __version__,
                    "psutil": has_psutil(),
                    "usage_disabled": getattr(args, "no_usage", False),
                    "probe_at": max((v.get("at", "") for v in cache.values()),
                                    default="")}
            html, _, _ = build_page(servers, skills.discover_skills(),
                                    skill_usage, analysis.load_history(), meta,
                                    live=True, token=nonce)
            args.html.parent.mkdir(parents=True, exist_ok=True)
            atomic_write(args.html, html)
            self._send(200, html, establish_session=True)

        def do_POST(self):
            path = self.path.split("?")[0]
            if not self._authorised(mutation=True):
                self._send(403, json.dumps({"ok": False, "message": "forbidden"}),
                           "application/json")
                return
            try:
                body = self._json_body()
                if not isinstance(body, dict):
                    raise ValueError("JSON body must be an object")
                if path == "/api/toggle":
                    key = body.get("key")
                    if not isinstance(key, str) or not key:
                        raise ValueError("key must be a non-empty string")
                    ok, msg = config.toggle_server(key, state["servers"])
                elif path == "/api/set":
                    if not isinstance(body.get("enabled"), bool):
                        raise ValueError("enabled must be a boolean")
                    entry = next((s for s in state["servers"]
                                  if s["key"] == body.get("key")), None)
                    if entry is None:
                        ok, msg = False, "unknown server"
                    else:
                        ok, msg = config.set_enabled(entry, body["enabled"])
                elif path == "/api/profile":
                    name = body.get("name")
                    if not isinstance(name, str) or not name:
                        raise ValueError("name must be a non-empty string")
                    ok, msg = config.apply_profile(name,
                                                   state["servers"])
                elif path == "/api/restore":
                    ok, msg = config.restore_last_change()
                else:
                    self._send(404, "{}", "application/json")
                    return
            except (ValueError, json.JSONDecodeError) as exc:
                self._send(400, json.dumps({"ok": False,
                                            "message": f"invalid request: {exc}"}),
                           "application/json")
                return
            except Exception as exc:  # pragma: no cover - defensive
                self._send(500, json.dumps({"ok": False, "message": str(exc)}),
                           "application/json")
                return
            self._send(200 if ok else 400,
                       json.dumps({"ok": ok, "message": msg}),
                       "application/json")

    return HTTPServer(("127.0.0.1", args.port), Handler), token


def serve(args):
    """Run the local control surface until interrupted."""
    httpd, token = _make_http_server(args)
    url = f"http://127.0.0.1:{httpd.server_port}/?t={token}"
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
    # Windows consoles often default to a legacy codepage that mangles the
    # "·" separators in status lines; ask for UTF-8 where the stream allows.
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except (AttributeError, OSError, ValueError):
            pass

    ap = argparse.ArgumentParser(
        description="MCP Server Dashboard — cost and benefit of your MCP toolbox")
    ap.add_argument("--version", action="version",
                    version=f"MCP Dashboard {__version__}")
    ap.add_argument("--doctor", action="store_true",
                    help="check Python, storage, port, optional features, and agent CLIs")
    ap.add_argument("--html", type=Path, default=DEFAULT_HTML)
    ap.add_argument("--note", type=Path, default=DEFAULT_NOTE)
    ap.add_argument("--demo", action="store_true", help="render sample data")
    ap.add_argument("--no-cli", action="store_true",
                    help="skip the `claude mcp list` health check (faster)")
    ap.add_argument("--no-usage", action="store_true",
                    default=os.environ.get("MCP_DASHBOARD_NO_USAGE", "").lower()
                    in {"1", "true", "yes", "on"},
                    help="do not read Claude Code or Codex transcripts")
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
    ap.add_argument("--restore-last", action="store_true",
                    help="restore files from the most recent dashboard config change")
    ap.add_argument("--json", type=Path, metavar="PATH", dest="json_path",
                    help="also write a machine-readable snapshot (nested "
                         "credential values redacted) for other tools")
    ap.add_argument("--open", action="store_true", help="open in a browser")
    argv = sys.argv[1:]
    if argv[:1] == ["open"]:
        argv = ["--serve", "--open", *argv[1:]]
    elif argv[:1] == ["scan"]:
        argv = argv[1:]
    args = ap.parse_args(argv)

    if args.doctor:
        if not doctor.run(args.port, args.html, args.note):
            raise SystemExit(1)
        return

    ensure_side_files()

    if args.restore_last:
        ok, msg = config.restore_last_change()
        print(msg)
        if not ok:
            raise SystemExit(1)
        return

    if args.list_profiles:
        for name, members in sorted(config.load_profiles().items()):
            print(f"{name}: {', '.join(members) or '(none — disables everything)'}")
        return

    if args.profile:
        servers, _ = scan(use_cli=False, include_usage=not args.no_usage)
        ok, msg = config.apply_profile(args.profile, servers)
        print(("Applied" if ok else "Failed to apply") +
              f" profile '{args.profile}': {msg}")
        if not ok:
            raise SystemExit(1)
        return

    if args.serve and not args.demo:
        serve(args)
        return

    now = datetime.datetime.now()
    now_iso = now.strftime("%Y-%m-%dT%H:%M:%S")
    meta = {"when": now.strftime("%Y-%m-%d %H:%M"),
            "host": platform.node() or platform.system(),
            "version": __version__,
            "demo": args.demo, "psutil": has_psutil(),
            "usage_disabled": args.no_usage}

    if args.demo:
        servers, skill_list, history, meta_extra = demo_data()
        meta.update(meta_extra)
        found = config.secret_findings(servers)
        recs = analysis.recommendations(servers, found, {"servers": {}})
        shadowed = analysis.skill_findings(skill_list, {})
        html = render.render_html(servers, skill_list, history, recs, found,
                                  shadowed, meta,
                                  profiles=config.load_profiles(), live=False)
    else:
        if args.probe:
            print("Probing servers (starting each one briefly)…")
        servers, skill_usage = scan(use_cli=not args.no_cli,
                                    do_probe=args.probe,
                                    probe_timeout=args.probe_timeout,
                                    include_usage=not args.no_usage)
        by_agent = {}
        for s in servers:
            by_agent[s["agent"]] = by_agent.get(s["agent"], 0) + 1
        print(f"Found {len(servers)} MCP server(s): " +
              (", ".join(f"{n} {a}" for a, n in sorted(by_agent.items()))
               or "none"))
        analysis.append_history(servers, now_iso)
        skill_list = skills.discover_skills()
        print(f"Found {len(skill_list)} skill(s).")
        cache = load_json(PROBE_CACHE_PATH) or {}
        meta["probe_at"] = max((v.get("at", "") for v in cache.values()), default="")
        html, recs, found = build_page(servers, skill_list, skill_usage,
                                       analysis.load_history(), meta)

    args.html.parent.mkdir(parents=True, exist_ok=True)
    atomic_write(args.html, html)
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
        if args.json_path:
            print(f"JSON snapshot -> "
                  f"{export_json(servers, skill_list, recs, t, args.json_path)}")

    if args.open:
        webbrowser.open(args.html.as_uri())


if __name__ == "__main__":
    main()
