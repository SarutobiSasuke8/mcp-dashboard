"""Usage history from agent transcripts.

Claude Code writes one JSONL transcript per session under
~/.claude/projects/<encoded-cwd>/<session-id>.jsonl, where every tool call
appears as a `tool_use` content block. MCP tools are named
`mcp__<server>__<tool>`, so counting them gives real usage per server —
the other half of the cost/benefit picture the process table can't supply.
Codex rollout files under ~/.codex/sessions are scanned best-effort.
"""

import datetime
import json
import re
from pathlib import Path

MCP_NAME_RE = re.compile(r"^mcp__([^_].*?)__(.+)$")
CODEX_NAME_RE = re.compile(r'"name"\s*:\s*"(?:mcp__)?([\w.-]+?)__([\w.-]+)"')


def _parse_ts(rec):
    ts = rec.get("timestamp") or rec.get("ts") or ""
    if not isinstance(ts, str):
        return None
    try:
        return datetime.datetime.fromisoformat(ts.replace("Z", "+00:00")).replace(tzinfo=None)
    except ValueError:
        return None


def _blocks(rec):
    msg = rec.get("message")
    if isinstance(msg, dict) and isinstance(msg.get("content"), list):
        return msg["content"]
    if isinstance(rec.get("content"), list):
        return rec["content"]
    return []


def _empty():
    return {"calls": 0, "calls_30d": 0, "calls_90d": 0, "last_used": None,
            "projects": {}, "tools": {}}


def _record(store, key, when, project, tool, now):
    e = store.setdefault(key, _empty())
    e["calls"] += 1
    if when:
        age = (now - when).days
        if age <= 30:
            e["calls_30d"] += 1
        if age <= 90:
            e["calls_90d"] += 1
        iso = when.strftime("%Y-%m-%dT%H:%M:%S")
        if not e["last_used"] or iso > e["last_used"]:
            e["last_used"] = iso
    if project:
        e["projects"][project] = e["projects"].get(project, 0) + 1
    if tool:
        e["tools"][tool] = e["tools"].get(tool, 0) + 1


def scan_claude_transcripts(root=None, max_files=4000):
    """Return (server_usage, skill_usage) keyed by lowercase name."""
    root = Path(root or (Path.home() / ".claude" / "projects"))
    servers, skills = {}, {}
    if not root.is_dir():
        return servers, skills
    now = datetime.datetime.now()
    for i, path in enumerate(sorted(root.glob("*/*.jsonl"))):
        if i >= max_files:
            break
        project = path.parent.name.split("-")[-1] or path.parent.name
        try:
            fh = path.open("r", encoding="utf-8", errors="replace")
        except OSError:
            continue
        with fh:
            for line in fh:
                if '"tool_use"' not in line:
                    continue
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    continue
                when = _parse_ts(rec)
                for blk in _blocks(rec):
                    if not isinstance(blk, dict) or blk.get("type") != "tool_use":
                        continue
                    name = blk.get("name") or ""
                    m = MCP_NAME_RE.match(name)
                    if m:
                        _record(servers, m.group(1).lower(), when, project,
                                m.group(2), now)
                    elif name == "Skill":
                        sk = (blk.get("input") or {}).get("skill")
                        if isinstance(sk, str) and sk:
                            _record(skills, sk.split(":")[-1].lower(), when,
                                    project, None, now)
    return servers, skills


def scan_codex_sessions(root=None, max_files=2000):
    """Best-effort usage counts from Codex rollout logs."""
    root = Path(root or (Path.home() / ".codex" / "sessions"))
    servers = {}
    if not root.is_dir():
        return servers
    now = datetime.datetime.now()
    files = sorted(root.rglob("*.jsonl"))[:max_files]
    for path in files:
        try:
            fh = path.open("r", encoding="utf-8", errors="replace")
        except OSError:
            continue
        with fh:
            for line in fh:
                if "__" not in line:
                    continue
                when = None
                try:
                    when = _parse_ts(json.loads(line))
                except json.JSONDecodeError:
                    pass
                for m in CODEX_NAME_RE.finditer(line):
                    server, tool = m.group(1), m.group(2)
                    if server in ("function", "type", "shell"):
                        continue
                    _record(servers, server.lower(), when, "codex", tool, now)
    return servers


def merge_usage(*maps):
    out = {}
    for m in maps:
        for k, v in m.items():
            e = out.setdefault(k, _empty())
            e["calls"] += v["calls"]
            e["calls_30d"] += v["calls_30d"]
            e["calls_90d"] += v["calls_90d"]
            if v["last_used"] and (not e["last_used"] or v["last_used"] > e["last_used"]):
                e["last_used"] = v["last_used"]
            for p, n in v["projects"].items():
                e["projects"][p] = e["projects"].get(p, 0) + n
            for t, n in v["tools"].items():
                e["tools"][t] = e["tools"].get(t, 0) + n
    return out


def collect_usage():
    servers, skills = scan_claude_transcripts()
    return merge_usage(servers, scan_codex_sessions()), skills


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
