"""MCP server configuration discovery and mutation.

Supports Claude Code (user/local/project scopes), OpenAI Codex
(~/.codex/config.toml), Gemini CLI (~/.gemini/settings.json), and Cursor
(~/.cursor/mcp.json). Disabling a server stashes its config so it can be
restored later; every direct file edit takes a timestamped backup first.
"""

import os
import re
from pathlib import Path

from .common import (DISABLED_PATH, GENERIC_COMMANDS, PROFILES_PATH,
                     PROVENANCE_PATH, backup_file, load_json, load_toml,
                     run_cli, save_json)

OFFICIAL_PREFIXES = ("@modelcontextprotocol/",)
VENDOR_PREFIXES = (
    "@playwright/", "@notionhq/", "@supabase/", "@cloudflare/", "@stripe/",
    "@sentry/", "@elastic/", "@aws/", "@azure/", "@google/", "@slack/",
    "@base-org/", "@browserbasehq/", "@upstash/", "@vercel/", "@figma/",
)
SCRIPT_EXTS = (".py", ".js", ".mjs", ".cjs", ".ts")
# \b keeps _PAT (personal access token) from matching inside _PATH.
SECRET_KEY_RE = re.compile(r"(KEY|TOKEN|SECRET|PASSWORD|PASSWD|CREDENTIAL|"
                           r"_PAT\b|APIKEY|ACCESS)", re.I)


# ---------------------------------------------------------------------------
# Shape helpers
# ---------------------------------------------------------------------------

def server_transport(cfg):
    t = (cfg.get("type") or "").lower()
    if t in ("http", "sse"):
        return t
    if cfg.get("url") or cfg.get("httpUrl"):
        return "http"
    return "stdio"


def server_command(cfg):
    if server_transport(cfg) != "stdio":
        return cfg.get("url") or cfg.get("httpUrl") or ""
    parts = [cfg.get("command", "")] + list(cfg.get("args", []))
    return " ".join(str(p) for p in parts if p)


def match_token(cfg):
    """Most distinctive substring of a stdio command line, used to find its
    processes. Prefers a package/script argument over generic launchers."""
    if server_transport(cfg) != "stdio":
        return None
    args = [str(a) for a in cfg.get("args", [])]
    candidates = [a for a in args if not a.startswith("-") and (
        "@" in a or "/" in a or "\\" in a or a.endswith(SCRIPT_EXTS))]
    if candidates:
        return max(candidates, key=len)
    cmd = os.path.basename(str(cfg.get("command", ""))).lower()
    if cmd and cmd not in GENERIC_COMMANDS:
        return cfg.get("command", "")
    for a in args:
        if not a.startswith("-"):
            return a
    return cfg.get("command") or None


def detect_provenance(entry, overrides):
    """Return (label, source). Labels: self-built, official, vendor,
    community, remote, unknown. Manual overrides always win."""
    ov = overrides.get(entry["name"])
    if isinstance(ov, dict):
        ov = ov.get("provenance") or ov.get("label")
    if isinstance(ov, str) and ov.strip():
        return ov.strip(), "manual"

    cfg = entry.get("raw") or {}
    if server_transport(cfg) != "stdio":
        return "remote", "auto"
    args = [str(a) for a in cfg.get("args", [])]
    cmd = os.path.basename(str(cfg.get("command", ""))).lower()

    # A local script run by a generic interpreter => probably yours.
    if cmd in GENERIC_COMMANDS and cmd not in (
            "npx", "npx.cmd", "npx.exe", "uvx", "uvx.exe", "docker", "docker.exe"):
        for a in args:
            if a.startswith("-"):
                continue
            if a.endswith(SCRIPT_EXTS) and "node_modules" not in a:
                return "self-built", "auto"
            break
    if str(cfg.get("command", "")).endswith(SCRIPT_EXTS):
        return "self-built", "auto"

    packages = [a for a in args if not a.startswith("-") and
                (a.startswith("@") or "/" in a
                 or re.match(r"^[\w-]+(@[\w.^~-]+)?$", a))]
    for pkg in packages:
        if pkg.startswith(OFFICIAL_PREFIXES):
            return "official", "auto"
        if pkg.startswith(VENDOR_PREFIXES):
            return "vendor", "auto"
    # A scoped or owner/name package published by someone else.
    if any("@" in pkg or "/" in pkg for pkg in packages):
        return "community", "auto"
    return "unknown", "auto"


# ---------------------------------------------------------------------------
# Discovery
# ---------------------------------------------------------------------------

def codex_toml_path():
    return Path(os.environ.get("CODEX_HOME", Path.home() / ".codex")) / "config.toml"


def gemini_settings_path():
    return Path(os.environ.get("GEMINI_HOME", Path.home() / ".gemini")) / "settings.json"


def cursor_mcp_path():
    return Path.home() / ".cursor" / "mcp.json"


def discover_servers():
    """Collect MCP servers across every supported agent and scope."""
    servers, seen = [], set()

    def add(name, cfg, agent, scope, origin):
        key = (agent, name, scope, origin)
        if key in seen or not isinstance(cfg, dict):
            return
        seen.add(key)
        servers.append({
            "name": name, "agent": agent, "scope": scope, "origin": origin,
            "transport": server_transport(cfg), "command": server_command(cfg),
            "token": match_token(cfg), "raw": cfg, "enabled": True,
        })

    # Claude Code -------------------------------------------------------
    claude_json = load_json(Path.home() / ".claude.json") or {}
    for name, cfg in (claude_json.get("mcpServers") or {}).items():
        add(name, cfg, "claude", "user", "~/.claude.json")
    project_paths = set((claude_json.get("projects") or {}).keys())
    project_paths.add(os.getcwd())
    for proj in sorted(project_paths):
        pcfg = (claude_json.get("projects") or {}).get(proj) or {}
        for name, cfg in (pcfg.get("mcpServers") or {}).items():
            add(name, cfg, "claude", "local", proj)
        for name, cfg in ((load_json(Path(proj) / ".mcp.json") or {})
                          .get("mcpServers") or {}).items():
            add(name, cfg, "claude", "project", str(Path(proj) / ".mcp.json"))

    # Codex -------------------------------------------------------------
    codex_cfg = load_toml(codex_toml_path()) or {}
    for name, cfg in (codex_cfg.get("mcp_servers") or {}).items():
        add(name, cfg, "codex", "user", str(codex_toml_path()))

    # Gemini CLI --------------------------------------------------------
    gem = load_json(gemini_settings_path()) or {}
    for name, cfg in (gem.get("mcpServers") or {}).items():
        add(name, cfg, "gemini", "user", str(gemini_settings_path()))

    # Cursor ------------------------------------------------------------
    cur = load_json(cursor_mcp_path()) or {}
    for name, cfg in (cur.get("mcpServers") or {}).items():
        add(name, cfg, "cursor", "user", str(cursor_mcp_path()))

    # Stash of servers this dashboard switched off ----------------------
    for key, e in (load_json(DISABLED_PATH) or {}).items():
        cfg = e.get("raw") or {}
        k = (e["agent"], e["name"], e["scope"], e.get("origin", ""))
        if k in seen:
            continue
        seen.add(k)
        servers.append({
            "name": e["name"], "agent": e["agent"], "scope": e["scope"],
            "origin": e.get("origin", ""), "transport": server_transport(cfg),
            "command": server_command(cfg), "token": match_token(cfg),
            "raw": cfg, "enabled": False,
        })

    overrides = {k: v for k, v in (load_json(PROVENANCE_PATH) or {}).items()
                 if not k.startswith("_")}
    for s in servers:
        s["provenance"], s["prov_source"] = detect_provenance(s, overrides)
        s["key"] = f"{s['agent']}::{s['scope']}::{s['name']}"
        s["note"] = (overrides.get(s["name"], {}) or {}).get("note", "") \
            if isinstance(overrides.get(s["name"]), dict) else ""
    return servers


def secret_findings(servers):
    """Flag plaintext-looking credentials in server env blocks. Values are
    never returned in full — only a short redacted preview."""
    out = []
    for s in servers:
        for k, v in ((s.get("raw") or {}).get("env") or {}).items():
            if not isinstance(v, str) or len(v) < 8:
                continue
            looks_secret = bool(SECRET_KEY_RE.search(k)) or re.match(
                r"^(sk-|ghp_|github_pat_|xoxb-|AIza|glpat-)", v)
            if not looks_secret:
                continue
            if re.match(r"^\$\{?[\w]+\}?$", v.strip()) or v.startswith("%"):
                continue  # already an env-var reference
            out.append({"server": s["name"], "agent": s["agent"],
                        "origin": s["origin"], "var": k,
                        "preview": v[:3] + "…" + v[-2:] if len(v) > 8 else "…"})
    return out


# ---------------------------------------------------------------------------
# Enable / disable
# ---------------------------------------------------------------------------

def _json_file_remove(path, name, container="mcpServers", project=None):
    data = load_json(path)
    if data is None:
        return False, f"could not read {path}"
    backup_file(path)
    if project is not None:
        ((data.get("projects") or {}).get(project) or {}).get(container, {}).pop(name, None)
    else:
        (data.get(container) or {}).pop(name, None)
    save_json(path, data)
    return True, f"removed by editing {Path(path).name} (backup made)"


def _json_file_add(path, name, cfg, container="mcpServers", project=None):
    data = load_json(path) or {}
    backup_file(path)
    if project is not None:
        data.setdefault("projects", {}).setdefault(project, {}).setdefault(
            container, {})[name] = cfg
    else:
        data.setdefault(container, {})[name] = cfg
    save_json(path, data)
    return True, f"restored by editing {Path(path).name} (backup made)"


def claude_disable(e):
    scope, origin = e["scope"], e["origin"]
    cwd = origin if scope == "local" else (
        str(Path(origin).parent) if scope == "project" else None)
    # The CLI rewrites config with no backup of its own, so take one first —
    # same guarantee as the direct-edit fallback.
    backup_file(Path(origin) if scope == "project" else
                Path.home() / ".claude.json")
    ok, out = run_cli(["claude", "mcp", "remove", e["name"], "-s", scope], cwd=cwd)
    if ok:
        return True, "removed via claude CLI"
    if scope == "user":
        return _json_file_remove(Path.home() / ".claude.json", e["name"])
    if scope == "local":
        return _json_file_remove(Path.home() / ".claude.json", e["name"],
                                 project=origin)
    return _json_file_remove(Path(origin), e["name"])


def claude_enable(e):
    import json as _json
    scope, origin = e["scope"], e["origin"]
    cwd = origin if scope == "local" else (
        str(Path(origin).parent) if scope == "project" else None)
    ok, out = run_cli(["claude", "mcp", "add-json", e["name"],
                       _json.dumps(e["raw"]), "-s", scope], cwd=cwd)
    if ok:
        return True, "restored via claude CLI"
    if scope == "user":
        return _json_file_add(Path.home() / ".claude.json", e["name"], e["raw"])
    if scope == "local":
        return _json_file_add(Path.home() / ".claude.json", e["name"], e["raw"],
                              project=origin)
    return _json_file_add(Path(origin), e["name"], e["raw"])


def codex_disable(e):
    # The CLI rewrites config.toml with no backup of its own; take one first.
    backup_file(codex_toml_path())
    ok, out = run_cli(["codex", "mcp", "remove", e["name"]])
    if ok:
        return True, "removed via codex CLI"
    path = codex_toml_path()
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return False, out
    backup_file(path)
    # Match the server's table and any sub-tables ([mcp_servers.x.env]) up to
    # the next table header at the start of a line. Value arrays contain "["
    # too, so the stop condition must be anchored, not the next bracket.
    name = re.escape(e["name"])
    pat = re.compile(r'(?m)^\[mcp_servers\.(?:"' + name + r'"|' + name +
                     r')(?:\.[^\]]+)?\][^\n]*\n(?:(?!^\[)[^\n]*\n?)*')
    new = pat.sub("", text)
    if new == text:
        return False, "server block not found in config.toml"
    path.write_text(new, encoding="utf-8")
    return True, "removed by editing config.toml (backup made)"


def _toml_str(v):
    """Serialise one TOML string value. Backslashes are escape characters in
    basic ("") strings, so a raw Windows path written that way is invalid
    TOML; prefer a literal ('') string, escaping only when it can't hold
    the value."""
    v = str(v)
    if "'" not in v and "\n" not in v:
        return f"'{v}'"
    return '"' + v.replace("\\", "\\\\").replace('"', '\\"') \
                  .replace("\n", "\\n") + '"'


def codex_enable(e):
    cfg = e["raw"] or {}
    cmd = ["codex", "mcp", "add", e["name"]]
    for k, v in (cfg.get("env") or {}).items():
        cmd += ["--env", f"{k}={v}"]
    if cfg.get("command"):
        cmd += ["--", str(cfg["command"])] + [str(a) for a in cfg.get("args", [])]
    ok, out = run_cli(cmd)
    if ok:
        return True, "restored via codex CLI"
    path = codex_toml_path()
    backup_file(path)
    lines = [f'\n[mcp_servers.{e["name"]}]']
    if cfg.get("command"):
        lines.append(f'command = {_toml_str(cfg["command"])}')
    if cfg.get("args"):
        lines.append("args = [" + ", ".join(_toml_str(a) for a in cfg["args"]) + "]")
    if cfg.get("url"):
        lines.append(f'url = {_toml_str(cfg["url"])}')
    if cfg.get("env"):
        lines.append(f'\n[mcp_servers.{e["name"]}.env]')
        for k, v in cfg["env"].items():
            lines.append(f'{k} = {_toml_str(v)}')
    with open(path, "a", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    return True, "restored by appending to config.toml (backup made)"


def gemini_disable(e):
    return _json_file_remove(gemini_settings_path(), e["name"])


def gemini_enable(e):
    return _json_file_add(gemini_settings_path(), e["name"], e["raw"])


def cursor_disable(e):
    return _json_file_remove(cursor_mcp_path(), e["name"])


def cursor_enable(e):
    return _json_file_add(cursor_mcp_path(), e["name"], e["raw"])


DISABLERS = {"claude": claude_disable, "codex": codex_disable,
             "gemini": gemini_disable, "cursor": cursor_disable}
ENABLERS = {"claude": claude_enable, "codex": codex_enable,
            "gemini": gemini_enable, "cursor": cursor_enable}


def set_enabled(entry, enabled):
    """Enable or disable one server. Returns (ok, message)."""
    stash = load_json(DISABLED_PATH) or {}
    key = entry["key"]
    keep = {k: entry[k] for k in ("name", "agent", "scope", "origin", "raw")}
    if enabled:
        stashed = stash.get(key) or keep
        stashed = {**stashed, "key": key}
        ok, msg = ENABLERS[entry["agent"]](stashed)
        if ok:
            stash.pop(key, None)
            save_json(DISABLED_PATH, stash)
        return ok, msg
    ok, msg = DISABLERS[entry["agent"]](entry)
    if ok:
        stash[key] = keep
        save_json(DISABLED_PATH, stash)
    return ok, msg


def toggle_server(key, servers):
    entry = next((s for s in servers if s["key"] == key), None)
    if entry is None:
        return False, f"unknown server key: {key}"
    return set_enabled(entry, not entry.get("enabled", True))


# ---------------------------------------------------------------------------
# Profiles
# ---------------------------------------------------------------------------

DEFAULT_PROFILES = {
    "_help": ("Named sets of MCP servers. Applying a profile enables every "
              "server listed and disables every other togglable server. "
              "Use server names as they appear in the dashboard."),
    "minimal": [],
    "coding": ["filesystem", "github", "playwright"],
    "research": ["fetch", "context7", "memory"],
}


def load_profiles():
    data = load_json(PROFILES_PATH)
    if data is None:
        save_json(PROFILES_PATH, DEFAULT_PROFILES)
        data = DEFAULT_PROFILES
    return {k: v for k, v in data.items()
            if not k.startswith("_") and isinstance(v, list)}


def apply_profile(name, servers):
    """Enable servers named in the profile, disable the rest. Returns
    (ok, message)."""
    profiles = load_profiles()
    if name not in profiles:
        return False, f"unknown profile: {name}"
    wanted = {n.lower() for n in profiles[name]}
    changed, failed = [], []
    for s in servers:
        should = s["name"].lower() in wanted
        if should == s.get("enabled", True):
            continue
        ok, msg = set_enabled(s, should)
        (changed if ok else failed).append(
            f"{s['name']} {'on' if should else 'off'}" + ("" if ok else f" ({msg})"))
    if not changed and not failed:
        return True, f"profile '{name}' already applied"
    parts = []
    if changed:
        parts.append("changed: " + ", ".join(changed))
    if failed:
        parts.append("failed: " + ", ".join(failed))
    return not failed, "; ".join(parts)
