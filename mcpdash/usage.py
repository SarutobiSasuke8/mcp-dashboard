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
CACHE_VERSION = 3
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
    servers, skills, project = {}, {}, None
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
            cwd = rec.get("cwd")
            if isinstance(cwd, str) and cwd:
                project = Path(cwd).name or cwd
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
    return {"servers": servers, "skills": skills, "project": project}


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


def _scan_root(root, parser, cache, project_of, agent):
    """Parse every JSONL under root, reusing cache entries for files whose
    size and mtime are unchanged. Returns [(agent, project, parsed)]."""
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
        if (hit and hit.get("size") == st.st_size
                and hit.get("mtime_ns") == st.st_mtime_ns):
            parsed = hit["data"]
        else:
            parsed = parser(path)
            cache[key] = {"size": st.st_size, "mtime_ns": st.st_mtime_ns,
                          "data": parsed}
        out.append((agent, parsed.get("project") or project_of(path), parsed))
    return out


# ---------------------------------------------------------------------------
# Aggregation
# ---------------------------------------------------------------------------

def _empty():
    return {"calls": 0, "calls_30d": 0, "calls_90d": 0, "last_used": None,
            "projects": {}, "tools": {}}


def _add_days(target, days, tools):
    """Add one transcript bucket to an aggregate and its time windows."""
    today = datetime.date.today()
    total = 0
    for day, count in days.items():
        total += count
        if day == "unknown":
            continue
        try:
            parsed_day = datetime.date.fromisoformat(day)
        except ValueError:
            continue
        age = (today - parsed_day).days
        if 0 <= age <= 30:
            target["calls_30d"] += count
        if 0 <= age <= 90:
            target["calls_90d"] += count
        if not target["last_used"] or day > target["last_used"][:10]:
            target["last_used"] = day + "T00:00:00"
    target["calls"] += total
    for tool, count in tools.items():
        target["tools"][tool] = target["tools"].get(tool, 0) + count


def _aggregate(chunks, kind):
    """Fold day-buckets into windowed totals against today."""
    out = {}
    for agent, project, parsed in chunks:
        for name, entry in (parsed.get(kind) or {}).items():
            key = name if kind == "skills" else f"{agent}::{name}"
            e = out.setdefault(key, _empty())
            _add_days(e, entry["days"], entry.get("tools", {}))
            if project:
                project_entry = e.setdefault("project_usage", {}).setdefault(
                    project, _empty())
                _add_days(project_entry, entry["days"], entry.get("tools", {}))
                project_entry["projects"][project] = project_entry["calls"]
                e["projects"][project] = project_entry["calls"]
    return out


def collect_usage(claude_root=None, codex_root=None, use_cache=True):
    """Return usage keyed by ``agent::server`` and skills by lowercase name."""
    cached = load_json(CACHE_PATH) if use_cache else None
    cache = (cached or {}).get("files", {}) if (cached or {}).get(
        "version") == CACHE_VERSION else {}

    claude_root = Path(claude_root or (Path.home() / ".claude" / "projects"))
    codex_root = Path(codex_root or (Path.home() / ".codex" / "sessions"))

    chunks = _scan_root(claude_root, parse_claude_file, cache,
                        lambda p: p.parent.name.split("-")[-1] or p.parent.name,
                        "claude")
    chunks += _scan_root(codex_root, parse_codex_file, cache, lambda p: "codex",
                         "codex")

    if use_cache:
        live = {str(p) for p in list(claude_root.rglob("*.jsonl"))
                + list(codex_root.rglob("*.jsonl"))} if (
            claude_root.is_dir() or codex_root.is_dir()) else set()
        cache = {k: v for k, v in cache.items() if k in live}
        save_json(CACHE_PATH, {"version": CACHE_VERSION, "files": cache})

    return _aggregate(chunks, "servers"), _aggregate(chunks, "skills")


def attach_usage(servers, usage):
    """Attach each observed call once, even with duplicate server names.

    Agent transcripts identify the agent and server name. Claude project
    transcripts also provide a project label, so duplicate project-scoped
    definitions can be separated where possible. Any genuinely ambiguous
    remainder is assigned once and explicitly marked rather than copied to
    every definition and inflated in totals.
    """
    groups = {}
    for server in servers:
        groups.setdefault((server["agent"], server["name"].lower()), []).append(server)

    for (agent, name), group in groups.items():
        aggregate = usage.get(f"{agent}::{name}") or usage.get(name) or _empty()
        if len(group) == 1:
            _set_usage(group[0], aggregate, "exact")
            continue

        remaining = dict(aggregate.get("project_usage") or {})
        allocated = set()
        for server in sorted(group, key=lambda s: 0 if s.get("scope") == "project" else 1):
            if server.get("scope") not in ("project", "local"):
                continue
            label = _server_project_label(server).casefold()
            matches = [project for project in remaining
                       if project.casefold() == label]
            if matches:
                project = matches[0]
                _set_usage(server, remaining.pop(project), "project")
                allocated.add(id(server))

        unallocated = [s for s in group if id(s) not in allocated]
        if remaining:
            residual = _merge_usage(remaining.values())
            preferred = next((s for s in unallocated if s.get("scope") == "user"),
                             unallocated[0] if unallocated else group[0])
            _set_usage(preferred, residual,
                       "aggregate" if preferred.get("scope") == "user" else "ambiguous")
            allocated.add(id(preferred))
        elif not aggregate.get("project_usage") and aggregate.get("calls"):
            preferred = next((s for s in unallocated if s.get("scope") == "user"),
                             unallocated[0] if unallocated else group[0])
            _set_usage(preferred, aggregate, "ambiguous")
            allocated.add(id(preferred))

        for server in group:
            if id(server) not in allocated:
                _set_usage(server, _empty(), "unattributed")
    return servers


def _server_project_label(server):
    origin = Path(str(server.get("origin", "")))
    return origin.parent.name if origin.name == ".mcp.json" else origin.name


def _merge_usage(entries):
    merged = _empty()
    for entry in entries:
        for field in ("calls", "calls_30d", "calls_90d"):
            merged[field] += entry.get(field, 0)
        last = entry.get("last_used")
        if last and (not merged["last_used"] or last > merged["last_used"]):
            merged["last_used"] = last
        for project, count in (entry.get("projects") or {}).items():
            merged["projects"][project] = merged["projects"].get(project, 0) + count
        for tool, count in (entry.get("tools") or {}).items():
            merged["tools"][tool] = merged["tools"].get(tool, 0) + count
    return merged


def _set_usage(s, u, attribution):
    s["calls"] = u["calls"]
    s["calls_30d"] = u["calls_30d"]
    s["calls_90d"] = u["calls_90d"]
    s["last_used"] = u["last_used"]
    s["projects_used"] = dict(sorted(u["projects"].items(),
                                     key=lambda kv: -kv[1]))
    s["top_tools"] = dict(sorted(u["tools"].items(),
                                 key=lambda kv: -kv[1])[:5])
    s["usage_attribution"] = attribution
