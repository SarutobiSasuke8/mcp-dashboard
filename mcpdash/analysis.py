"""History, recommendations, and the cost/benefit verdict per server."""

import json

from .common import (HISTORY_LIMIT, HISTORY_PATH, days_ago, fmt_mb,
                     fmt_tokens, load_json)

MB = 1024 * 1024


# ---------------------------------------------------------------------------
# History
# ---------------------------------------------------------------------------

def append_history(servers, now_iso):
    snap = {
        "ts": now_iso,
        "total_mb": round(sum(s.get("ram_bytes", 0) for s in servers) / MB, 1),
        "total_tokens": sum(s.get("ctx_tokens", 0) for s in servers
                            if s.get("enabled", True)),
        "servers": {s["key"]: round(s.get("ram_bytes", 0) / MB, 1)
                    for s in servers if s.get("ram_bytes")},
    }
    with open(HISTORY_PATH, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(snap) + "\n")


def load_history():
    if not HISTORY_PATH.exists():
        return []
    rows = []
    for line in HISTORY_PATH.read_text(encoding="utf-8").splitlines():
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return rows[-HISTORY_LIMIT:]


# ---------------------------------------------------------------------------
# Verdicts
# ---------------------------------------------------------------------------

def verdict(s, registry_entry=None):
    """One-word cost/benefit judgement for a server."""
    if not s.get("enabled", True):
        return "disabled"
    if s.get("status") == "failed" or s.get("probe_error"):
        return "broken"
    calls30 = s.get("calls_30d", 0)
    calls = s.get("calls", 0)
    ram = s.get("ram_bytes", 0)
    tokens = s.get("ctx_tokens", 0)
    age = days_ago((registry_entry or {}).get("first_seen"))
    settling = age is not None and age < 7
    if calls == 0 and not settling and (ram > 50 * MB or tokens > 1500):
        return "unused"
    if calls30 == 0 and calls > 0:
        return "dormant"
    if calls30 <= 2 and (ram > 250 * MB or tokens > 6000):
        return "expensive"
    if calls30 > 0:
        return "earning"
    return "quiet"


VERDICT_ORDER = {"broken": 0, "unused": 1, "expensive": 2, "dormant": 3,
                 "quiet": 4, "earning": 5, "disabled": 6}


def recommendations(servers, secrets, registry):
    """Actionable findings, most valuable first. Each: {severity, title,
    detail, key, action, saving_bytes}."""
    out = []
    entries = (registry or {}).get("servers", {})

    for s in servers:
        if not s.get("enabled", True):
            continue
        reg = entries.get(s["key"], {})
        v = verdict(s, reg)
        ram, tokens = s.get("ram_bytes", 0), s.get("ctx_tokens", 0)
        calls30, calls = s.get("calls_30d", 0), s.get("calls", 0)
        last = s.get("last_used")
        age = days_ago(reg.get("first_seen"))

        if v == "broken":
            err = (s.get("probe_error") or "server reports as failed").strip()
            out.append({
                "severity": "high", "key": s["key"], "action": "disable",
                "title": f"{s['name']} is failing",
                "detail": (f"{err[:220]} — a broken server still costs startup "
                           f"time on every session. Fix it or switch it off."),
                "saving_bytes": ram})
        elif v == "unused":
            never = "never used" if calls == 0 else "unused"
            since = f", installed {age}d ago" if age is not None else ""
            out.append({
                "severity": "high" if ram > 200 * MB else "medium",
                "key": s["key"], "action": "disable",
                "title": f"{s['name']}: {never}{since}",
                "detail": (f"No recorded tool calls, but it costs "
                           f"{fmt_mb(ram)} of RAM"
                           + (f" and ~{fmt_tokens(tokens)} tokens of context "
                              f"({s.get('tools_count', 0)} tools) in every request"
                              if tokens else "") + "."),
                "saving_bytes": ram})
        elif v == "dormant":
            out.append({
                "severity": "medium", "key": s["key"], "action": "disable",
                "title": f"{s['name']}: no calls in 30 days",
                "detail": (f"Last used {last[:10] if last else 'unknown'} "
                           f"({calls} calls all-time). Currently {fmt_mb(ram)}"
                           + (f" and ~{fmt_tokens(tokens)} context tokens" if tokens else "")
                           + ". Switch on again when you need it."),
                "saving_bytes": ram})
        elif v == "expensive":
            out.append({
                "severity": "medium", "key": s["key"], "action": "review",
                "title": f"{s['name']}: high cost, low use",
                "detail": (f"{calls30} calls in 30 days for {fmt_mb(ram)}"
                           + (f" and ~{fmt_tokens(tokens)} context tokens "
                              f"({s.get('tools_count', 0)} tools)" if tokens else "")
                           + ". Consider project scope so it only loads where used."),
                "saving_bytes": 0})

        # Scope advice: used in exactly one project but configured globally.
        projects = s.get("projects_used") or {}
        if (s.get("scope") == "user" and len(projects) == 1 and calls30 >= 3
                and s.get("transport") == "stdio"):
            proj = next(iter(projects))
            out.append({
                "severity": "low", "key": s["key"], "action": "review",
                "title": f"{s['name']}: only used in {proj}",
                "detail": (f"Configured globally but every recorded call came "
                           f"from one project. Moving it to that project's "
                           f".mcp.json keeps it out of every other session."),
                "saving_bytes": ram})

        if s.get("probe_ms") and s["probe_ms"] > 3000:
            out.append({
                "severity": "low", "key": s["key"], "action": "review",
                "title": f"{s['name']} is slow to start",
                "detail": (f"{s['probe_ms'] / 1000:.1f}s handshake — that delay "
                           f"lands on every new session that loads it."),
                "saving_bytes": 0})

    for f in secrets:
        out.append({
            "severity": "high", "key": None, "action": "secret",
            "title": f"Plaintext credential in {f['server']} config",
            "detail": (f"{f['var']} = {f['preview']} sits in {f['origin']}. "
                       f"Config files get synced and backed up — reference an "
                       f"environment variable instead."),
            "saving_bytes": 0})

    # Same server name configured for more than one agent/scope.
    by_name = {}
    for s in servers:
        by_name.setdefault(s["name"].lower(), []).append(s)
    for name, group in by_name.items():
        if len(group) > 1 and len({g["agent"] for g in group}) > 1:
            agents = ", ".join(sorted({g["agent"] for g in group}))
            out.append({
                "severity": "info", "key": None, "action": "note",
                "title": f"{group[0]['name']} is configured for {agents}",
                "detail": ("Each agent runs its own copy — expected if you use "
                           "both, wasteful if you don't."),
                "saving_bytes": 0})

    rank = {"high": 0, "medium": 1, "low": 2, "info": 3}
    out.sort(key=lambda r: (rank[r["severity"]], -r["saving_bytes"]))
    return out


def totals(servers, recs):
    enabled = [s for s in servers if s.get("enabled", True)]
    return {
        "ram": sum(s.get("ram_bytes", 0) for s in enabled),
        "tokens": sum(s.get("ctx_tokens", 0) for s in enabled),
        "tools": sum(s.get("tools_count", 0) for s in enabled),
        "calls30": sum(s.get("calls_30d", 0) for s in enabled),
        "reclaimable": sum(r["saving_bytes"] for r in recs
                           if r["action"] == "disable"),
        "high": sum(1 for r in recs if r["severity"] == "high"),
    }


def skill_findings(skills, skill_usage):
    """Attach usage to skills and flag name shadowing across sources."""
    by_name = {}
    for sk in skills:
        u = skill_usage.get(sk["name"].lower()) or {}
        sk["calls"] = u.get("calls", 0)
        sk["calls_30d"] = u.get("calls_30d", 0)
        sk["last_used"] = u.get("last_used")
        by_name.setdefault(sk["name"].lower(), []).append(sk)
    shadowed = []
    for name, group in by_name.items():
        if len(group) < 2:
            continue
        winner = group[0]  # discovery order encodes precedence
        for other in group[1:]:
            other["shadowed_by"] = winner["source"]
        shadowed.append({"name": group[0]["name"],
                         "winner": winner["source"],
                         "others": [g["source"] for g in group[1:]]})
    return shadowed
