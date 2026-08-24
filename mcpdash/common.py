"""Shared paths and helpers for the MCP Dashboard."""

import datetime
import json
import os
import platform
import re
import subprocess
from pathlib import Path

PKG_DIR = Path(__file__).resolve().parent
SCRIPT_DIR = PKG_DIR.parent


def _find_vault_root():
    """The vault this script lives in, when it lives in one.

    Set MCP_DASHBOARD_VAULT to point elsewhere. Run from a standalone clone
    (outside any vault) and outputs fall back to an `output/` folder next to
    the script, so the tool works anywhere without configuration.
    """
    override = os.environ.get("MCP_DASHBOARD_VAULT")
    if override:
        return Path(override).expanduser()
    for parent in SCRIPT_DIR.parents:
        if (parent / "Obsidian Vault Management").is_dir():
            return parent
    return None


VAULT_ROOT = _find_vault_root()
IN_VAULT = VAULT_ROOT is not None
if IN_VAULT:
    SYSTEMS_DIR = VAULT_ROOT / "Obsidian Vault Management" / "Systems"
    TASKS_INBOX = VAULT_ROOT / "Tasks" / "Inbox.md"
else:
    VAULT_ROOT = SCRIPT_DIR
    SYSTEMS_DIR = SCRIPT_DIR / "output"
    TASKS_INBOX = SCRIPT_DIR / "output" / "Inbox.md"

DEFAULT_HTML = SYSTEMS_DIR / "MCP Server Dashboard.html"
DEFAULT_NOTE = SYSTEMS_DIR / "MCP Directory.md"
WEEKLY_NOTE = SYSTEMS_DIR / "MCP Usage Report.md"

REGISTRY_PATH = SCRIPT_DIR / "mcp-registry.json"
HISTORY_PATH = SCRIPT_DIR / "mcp-history.jsonl"
DISABLED_PATH = SCRIPT_DIR / "mcp-disabled.json"
PROVENANCE_PATH = SCRIPT_DIR / "mcp-provenance.json"
PROFILES_PATH = SCRIPT_DIR / "mcp-profiles.json"
PROBE_CACHE_PATH = SCRIPT_DIR / "mcp-probe-cache.json"

HISTORY_LIMIT = 60

GENERIC_COMMANDS = {
    "node", "node.exe", "npx", "npx.cmd", "npx.exe", "python", "python3",
    "python.exe", "uv", "uvx", "uvx.exe", "uv.exe", "docker", "docker.exe",
    "cmd", "cmd.exe", "sh", "bash", "deno", "bun", "bun.exe",
}


def load_json(path):
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, json.JSONDecodeError):
        return None


def save_json(path, data):
    Path(path).write_text(json.dumps(data, indent=2), encoding="utf-8")


def load_toml(path):
    """Parse TOML via tomllib when available, else a minimal fallback that
    understands [section.sub] headers and string/number/bool/array values."""
    try:
        text = Path(path).read_text(encoding="utf-8")
    except OSError:
        return None
    try:
        import tomllib
        return tomllib.loads(text)
    except Exception:
        pass
    data, cur = {}, None
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        m = re.match(r"^\[([^\]]+)\]$", line)
        if m:
            cur = data
            for part in m.group(1).split("."):
                cur = cur.setdefault(part.strip().strip('"'), {})
            continue
        m = re.match(r"^([\w.-]+)\s*=\s*(.+)$", line)
        if m and cur is not None:
            key, val = m.group(1), m.group(2).strip()
            if val.startswith("["):
                cur[key] = [i.replace('\\"', '"')
                            for i in re.findall(r'"((?:[^"\\]|\\.)*)"', val)]
            elif val.startswith('"'):
                cur[key] = val.strip('"')
            elif val in ("true", "false"):
                cur[key] = val == "true"
            else:
                try:
                    cur[key] = float(val) if "." in val else int(val)
                except ValueError:
                    cur[key] = val
    return data


def run_cli(cmd, cwd=None, timeout=60):
    """Run a CLI command; returns (ok, combined output). Tries the .cmd
    variant first on Windows so npm-installed shims resolve."""
    variants = [cmd]
    if platform.system() == "Windows":
        variants.insert(0, [cmd[0] + ".cmd"] + cmd[1:])
    for v in variants:
        try:
            proc = subprocess.run(v, capture_output=True, text=True,
                                  timeout=timeout, cwd=cwd)
            return proc.returncode == 0, (proc.stdout + "\n" + proc.stderr)
        except (OSError, subprocess.TimeoutExpired):
            continue
    return False, "command not found"


def backup_file(path):
    path = Path(path)
    if path.exists():
        stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
        path.with_name(path.name + f".bak-{stamp}").write_text(
            path.read_text(encoding="utf-8"), encoding="utf-8")


def esc(s):
    return (str(s).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


def fmt_mb(b):
    mb = b / (1024 * 1024)
    return f"{mb / 1024:.1f} GB" if mb >= 1024 else f"{mb:.0f} MB"


def fmt_tokens(n):
    if not n:
        return "—"
    return f"{n / 1000:.1f}k" if n >= 1000 else str(int(n))


def has_psutil():
    try:
        import psutil  # noqa: F401
        return True
    except ImportError:
        return False


def days_ago(iso):
    if not iso:
        return None
    try:
        then = datetime.datetime.fromisoformat(iso[:19])
    except ValueError:
        return None
    return (datetime.datetime.now() - then).days


def project_label(path):
    """Human label for a Claude Code project directory."""
    return Path(str(path)).name or str(path)
