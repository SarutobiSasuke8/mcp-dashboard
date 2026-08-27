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


def atomic_write(path, text):
    """Write via a temporary file in the same directory, then replace.

    Config files edited here belong to other programs; a crash or full disk
    mid-write must never leave one truncated."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    with open(tmp, "w", encoding="utf-8") as fh:
        fh.write(text)
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(tmp, path)


def save_json(path, data):
    atomic_write(path, json.dumps(data, indent=2))


def parse_ts(value):
    """Parse an ISO timestamp to naive local time.

    Transcripts stamp UTC with a trailing Z; comparing that to a local
    `now()` would skew every age by the UTC offset, so convert first."""
    if not isinstance(value, str) or not value:
        return None
    text = value.strip()
    try:
        if text.endswith("Z"):
            dt = datetime.datetime.fromisoformat(text[:-1]).replace(
                tzinfo=datetime.timezone.utc)
        else:
            dt = datetime.datetime.fromisoformat(text)
    except ValueError:
        return None
    if dt.tzinfo is not None:
        dt = dt.astimezone().replace(tzinfo=None)
    return dt


def load_toml(path):
    """Parse TOML via tomllib when available (3.11+), else a minimal
    fallback that understands [section.sub] headers and string/number/
    bool/array values, in both basic ("…") and literal ('…') strings."""
    try:
        text = Path(path).read_text(encoding="utf-8")
    except OSError:
        return None
    try:
        import tomllib
        return tomllib.loads(text)
    except Exception:
        pass
    return parse_toml_fallback(text)


def parse_toml_fallback(text):
    """The no-tomllib parser, separated so tests exercise it on every
    Python version — tomllib would otherwise mask its bugs on 3.11+."""
    data, cur = {}, None
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        m = re.match(r"^\[([^\]]+)\]$", line)
        if m:
            cur = data
            parts = re.findall(r'(?:^|\.)\s*(?:"((?:[^"\\]|\\.)*)"|([\w-]+))',
                               m.group(1))
            for basic, bare in parts:
                part = (basic.replace('\\"', '"').replace("\\\\", "\\")
                        if basic else bare)
                cur = cur.setdefault(part, {})
            continue
        m = re.match(r'^(?:"((?:[^"\\]|\\.)*)"|([\w.-]+))\s*=\s*(.+)$',
                     line)
        if m and cur is not None:
            key = (m.group(1).replace('\\"', '"').replace("\\\\", "\\")
                   if m.group(1) is not None else m.group(2))
            val = m.group(3).strip()
            if val.startswith("["):
                # Basic ("…", backslash-escaped) and literal ('…', verbatim)
                # strings, in the order they appear.
                cur[key] = [seg[0].replace('\\"', '"').replace("\\\\", "\\")
                            if seg[0] else seg[1]
                            for seg in re.findall(
                                r'"((?:[^"\\]|\\.)*)"|\'([^\']*)\'', val)]
            elif val.startswith('"'):
                cur[key] = val.strip('"').replace('\\"', '"') \
                              .replace("\\\\", "\\")
            elif val.startswith("'"):
                cur[key] = val.strip("'")
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


BACKUP_KEEP = 10
_BACKUP_STAMP_RE = re.compile(r"\.bak-\d{8}-\d{6}$")


def backup_file(path, keep=BACKUP_KEEP):
    """Timestamped copy next to the file, pruning our oldest backups beyond
    `keep`. Only backups matching this function's own stamp format are ever
    pruned — a user's hand-made .bak files are left alone."""
    path = Path(path)
    if not path.exists():
        return
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    path.with_name(path.name + f".bak-{stamp}").write_text(
        path.read_text(encoding="utf-8"), encoding="utf-8")
    ours = sorted(p for p in path.parent.glob(path.name + ".bak-*")
                  if _BACKUP_STAMP_RE.search(p.name))
    for old in ours[:-keep]:
        try:
            old.unlink()
        except OSError:
            pass


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
    then = parse_ts(iso)
    return None if then is None else (datetime.datetime.now() - then).days


def project_label(path):
    """Human label for a Claude Code project directory."""
    return Path(str(path)).name or str(path)
