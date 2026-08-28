"""Release-grade local environment diagnostics."""

import os
import shutil
import socket
import sys
from pathlib import Path

from . import __version__
from .common import CACHE_DIR, CONFIG_DIR, STATE_DIR, has_psutil


def _writable_directory(path):
    """Return (ok, detail) after a reversible write test in ``path``."""
    path = Path(path)
    probe = path / f".mcp-dashboard-doctor-{os.getpid()}"
    try:
        path.mkdir(parents=True, exist_ok=True)
        probe.write_text("ok", encoding="utf-8")
        probe.unlink()
        return True, str(path)
    except OSError as exc:
        try:
            probe.unlink(missing_ok=True)
        except OSError:
            pass
        return False, f"{path}: {exc}"


def _port_available(port):
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.bind(("127.0.0.1", port))
        return True, f"127.0.0.1:{port} is available"
    except OSError as exc:
        return False, f"127.0.0.1:{port}: {exc}"


def checks(port=7817, html_path=None, note_path=None):
    results = []

    def add(name, ok, detail, required=False):
        results.append({"name": name, "ok": bool(ok), "detail": str(detail),
                        "required": required})

    version = sys.version_info
    add("Python", version >= (3, 10),
        f"{version.major}.{version.minor}.{version.micro}", required=True)
    add("MCP Dashboard", True, __version__, required=True)
    for name, path in (("Config directory", CONFIG_DIR),
                       ("State directory", STATE_DIR),
                       ("Cache directory", CACHE_DIR)):
        ok, detail = _writable_directory(path)
        add(name, ok, detail, required=True)
    ok, detail = _port_available(port)
    add("Live port", ok, detail, required=True)
    add("Optional CPU sampling", has_psutil(),
        "psutil installed" if has_psutil() else
        "psutil not installed; install mcp-dashboard[cpu] for live CPU data")

    cli_names = (("Claude Code CLI", "claude"), ("Codex CLI", "codex"),
                 ("Gemini CLI", "gemini"), ("Cursor CLI", "cursor"))
    for label, command in cli_names:
        found = shutil.which(command) or shutil.which(command + ".cmd")
        add(label, bool(found), found or "not found (config discovery still works)")

    for label, path in (("HTML output", html_path), ("Directory note", note_path)):
        if path is not None:
            add(label, True, str(Path(path)))
    return results


def run(port=7817, html_path=None, note_path=None):
    results = checks(port=port, html_path=html_path, note_path=note_path)
    print(f"MCP Dashboard {__version__} diagnostics\n")
    for item in results:
        marker = "OK" if item["ok"] else ("FAIL" if item["required"] else "INFO")
        print(f"[{marker:4}] {item['name']}: {item['detail']}")
    failed = [item for item in results if item["required"] and not item["ok"]]
    print("\nReady." if not failed else
          f"\nNot ready: {len(failed)} required check(s) failed.")
    return not failed
