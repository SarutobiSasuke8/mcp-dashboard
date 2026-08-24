"""Usage history from agent transcripts.

Claude Code writes one JSONL transcript per session under
~/.claude/projects/<encoded-cwd>/<session-id>.jsonl, where every tool call
appears as a `tool_use` content block. MCP tools are named
`mcp__<server>__<tool>`, so counting them gives real usage per server —
the other half of the cost/benefit picture the process table can't supply.
Codex rollout files under ~/.codex/sessions are scanned best-effort.

Transcripts accumulate, and re-reading every line on every scan gets slow
once there are hundreds of sessions. Each file is therefore parsed once
into day-bucketed counts and cached against its size and mtime; only new
or changed files are read again. Buckets are per-day so that the 30/90-day
windows can still be recomputed fresh on every run.
"""

import datetime
import json
import re
from pathlib import Path

from .common import SCRIPT_DIR, load_json, parse_ts, save_json

MCP_NAME_RE = re.compile(r"^mcp__([^_].*?)__(.+)$")
CODEX_NAME_RE = re.compile(r'"name"\s*:\s*"(?:mcp__)?([\w.-]+?)__([\w.-]+)"')
CACHE_PATH = SCRIPT_DIR / "mcp-usage-cache.json"
CACHE_VERSION = 2
CODEX_SKIP = {"function", "type", "shell", "local", "apply", "container"}


# ---------------------------------------------------------------------------
# Per-file parsing (cached)
# ---------------------------------------------------------------------------

def _blocks(rec):
    msg = rec.get("message")
    if isinstance(msg, dict) and isinstance(msg.get("content"), list):
        return msg["content"]
    if isinstance(rec.get("content"), list):
        return rec["content"]
    return []


def _bucket(store, key, day, tool=None):
    e = store.setdefault(key, {"days": {}, "tools": {}})
    e["days"][day] = e["days"].get(day, 0) + 1
    if tool:
        e["tools"][tool] = e["tools"].get(tool, 0) + 1


def parse_claude_file(path):
    """{servers: {...}, skills: {...}} of day-bucketed counts for one file."""
    servers, skills = {}, {}
    try:
        fh = path.open("r", encoding="utf-8", errors="replace")
    except OSError:
        return {"servers": servers, "skills": skills}
    with fh:
        for line in fh:
            if '"tool_use"' not in line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            when = parse_ts(rec.get("timestamp") or rec.get("ts") or "")
            day = when.strftime("%Y-%m-%d") if when else "unknown"
            for blk in _blocks(rec):
                if not isinstance(blk, dict) or blk.get("type") != "tool_use":
                    continue
                name = blk.get("name") or ""
                m = MCP_NAME_RE.match(name)
                if m:
                    _bucket(servers, m.group(1).lower(), day, m.group(2))
                elif name == "Skill":
                    sk = (blk.get("input") or {}).get("skill")
                    if isinstance(sk, str) and sk:
                        _bucket(skills, sk.split(":")[-1].lower(), day)
    return {"servers": servers, "skills": skills}


def parse_codex_file(path):
    servers = {}
    try:
        fh = path.open("r", encoding="utf-8", errors="replace")
    except OSError:
        return {"servers": servers, "skills": {}}
    with fh:
        for line in fh:
            if "__" not in line:
                continue
            when = None
            try:
                when = parse_ts((json.loads(line) or {}).get("timestamp", ""))
            except (json.JSONDecodeError, AttributeError):
                pass
            day = when.strftime("%Y-%m-%d") if when else "unknown"
            for m in CODEX_NAME_RE.finditer(line):
                server, tool = m.group(1), m.group(2)
                if server.lower() in CODEX_SKIP:
                    continue
                _bucket(servers, server.lower(), day, tool)
    return {"servers": servers, "skills": {}}


def _scan_root(root, parser, cache, project_of):
    """Parse every JSONL under root, reusing cache entries for files whose
    size and mtime are unchanged. Returns [(project, parsed)]."""
    out = []
    if not root.is_dir():
        return out
    for path in sorted(root.rglob("*.jsonl")):
        try:
            st = path.stat()
        except OSError:
            continue
        key = str(path)
        hit = cache.get(key)
        if hit and hit.get("size") == st.st_size and hit.get("mtime") == int(st.st_mtime):
            parsed = hit["data"]
        else:
            parsed = parser(path)
            cache[key] = {"size": st.st_size, "mtime": int(st.st_mtime),
                          "data": parsed}
        out.append((project_of(path), parsed))
    return out


# ---------------------------------------------------------------------------
# Aggregation
# ---------------------------------------------------------------------------

def _empty():
    return {"calls": 0, "calls_30d": 0, "calls_90d": 0, "last_used": None,
            "projects": {}, "tools": {}}


def _aggregate(chunks, kind):
    """Fold day-buckets into windowed totals against today."""
    today = datetime.date.today()
    out = {}
    for project, parsed in chunks:
        for name, entry in (parsed.get(kind) or {}).items():
            e = out.setdefault(name, _empty())
            total = 0
            for day, count in entry["days"].items():
                total += count
                if day == "unknown":
                    continue
                try:
                    d = datetime.date.fromisoformat(day)
                except ValueError:
                    continue
                age = (today - d).days
                if age <= 30:
                    e["calls_30d"] += count
                if age <= 90:
                    e["calls_90d"] += count
                if not e["last_used"] or day > e["last_used"][:10]:
                    e["last_used"] = day + "T00:00:00"
            e["calls"] += total
            if project:
                e["projects"][project] = e["projects"].get(project, 0) + total
            for tool, n in entry.get("tools", {}).items():
                e["tools"][tool] = e["tools"].get(tool, 0) + n
    return out


def collect_usage(claude_root=None, codex_root=None, use_cache=True):
    """Return (server_usage, skill_usage) keyed by lowercase name."""
    cached = load_json(CACHE_PATH) if use_cache else None
    cache = (cached or {}).get("files", {}) if (cached or {}).get(
        "version") == CACHE_VERSION else {}

    claude_root = Path(claude_root or (Path.home() / ".claude" / "projects"))
    codex_root = Path(codex_root or (Path.home() / ".codex" / "sessions"))

    chunks = _scan_root(claude_root, parse_claude_file, cache,
                        lambda p: p.parent.name.split("-")[-1] or p.parent.name)
    chunks += _scan_root(codex_root, parse_codex_file, cache, lambda p: "codex")

    if use_cache:
        live = {str(p) for p in list(claude_root.rglob("*.jsonl"))
                + list(codex_root.rglob("*.jsonl"))} if (
            claude_root.is_dir() or codex_root.is_dir()) else set()
        cache = {k: v for k, v in cache.items() if k in live}
        save_json(CACHE_PATH, {"version": CACHE_VERSION, "files": cache})

    return _aggregate(chunks, "servers"), _aggregate(chunks, "skills")


def attach_usage(servers, usage):
    for s in servers:
        u = usage.get(s["name"].lower()) or _empty()
        s["calls"] = u["calls"]
        s["calls_30d"] = u["calls_30d"]
        s["calls_90d"] = u["calls_90d"]
        s["last_used"] = u["last_used"]
        s["projects_used"] = dict(sorted(u["projects"].items(),
                                         key=lambda kv: -kv[1]))
        s["top_tools"] = dict(sorted(u["tools"].items(),
                                     key=lambda kv: -kv[1])[:5])
    return servers
