"""Sample data so the dashboard's visual can be reviewed without a scan."""

MB = 1024 * 1024


def demo_data():
    servers = [
        dict(name="playwright", agent="claude", scope="user",
             origin="~/.claude.json", transport="stdio",
             command="npx -y @playwright/mcp@latest", provenance="vendor",
             status="connected", instances=3, ram_bytes=812 * MB, cpu_pct=4.2,
             enabled=True, calls=6, calls_30d=0, calls_90d=6,
             last_used="2026-06-11T09:12:00", tools_count=24, ctx_tokens=9800,
             probe_ms=2100, probe_error="", projects_used={"obsidian-vault": 6}),
        dict(name="filesystem", agent="claude", scope="user",
             origin="~/.claude.json", transport="stdio",
             command="npx -y @modelcontextprotocol/server-filesystem D:/Vault",
             provenance="official", status="connected", instances=3,
             ram_bytes=486 * MB, cpu_pct=0.6, enabled=True, calls=812,
             calls_30d=214, calls_90d=602, last_used="2026-08-24T18:40:00",
             tools_count=11, ctx_tokens=3200, probe_ms=740, probe_error="",
             projects_used={"obsidian-vault": 190, "astraeus": 24}),
        dict(name="memory", agent="codex", scope="user",
             origin="~/.codex/config.toml", transport="stdio",
             command="npx -y @modelcontextprotocol/server-memory",
             provenance="official", status="running", instances=2,
             ram_bytes=231 * MB, cpu_pct=0.3, enabled=True, calls=48,
             calls_30d=12, calls_90d=40, last_used="2026-08-22T11:05:00",
             tools_count=9, ctx_tokens=2400, probe_ms=610, probe_error="",
             projects_used={"codex": 48}),
        dict(name="vault-bridge", agent="claude", scope="user",
             origin="~/.claude.json", transport="stdio",
             command="python C:/Users/sarut/mcp/vault_bridge_server.py",
             provenance="self-built", status="connected", instances=2,
             ram_bytes=214 * MB, cpu_pct=1.8, enabled=True, calls=356,
             calls_30d=97, calls_90d=280, last_used="2026-08-24T20:02:00",
             tools_count=7, ctx_tokens=1900, probe_ms=880, probe_error="",
             projects_used={"obsidian-vault": 97},
             env_secret=True),
        dict(name="obsidian-vault", agent="claude", scope="project",
             origin=".mcp.json", transport="stdio", command="uvx mcp-obsidian",
             provenance="community", status="failed", instances=1,
             ram_bytes=74 * MB, cpu_pct=0.1, enabled=True, calls=3, calls_30d=0,
             calls_90d=1, last_used="2026-07-30T08:00:00", tools_count=0,
             ctx_tokens=0, probe_ms=None,
             probe_error="exited with code 1 — stderr: OBSIDIAN_API_KEY not set",
             projects_used={"obsidian-vault": 3}),
        dict(name="base-mcp", agent="claude", scope="user",
             origin="~/.claude.json", transport="stdio",
             command="npx -y @base-org/mcp", provenance="vendor",
             status="disabled", instances=0, ram_bytes=0, cpu_pct=None,
             enabled=False, calls=11, calls_30d=0, calls_90d=2,
             last_used="2026-07-02T14:20:00", tools_count=18, ctx_tokens=5200,
             probe_ms=1500, probe_error="", projects_used={"obsidian-vault": 11}),
        dict(name="github", agent="claude", scope="user",
             origin="~/.claude.json", transport="http",
             command="https://api.githubcopilot.com/mcp/", provenance="remote",
             status="connected", instances=0, ram_bytes=0, cpu_pct=None,
             enabled=True, calls=402, calls_30d=88, calls_90d=310,
             last_used="2026-08-24T19:55:00", tools_count=61, ctx_tokens=18400,
             probe_ms=None, probe_error="", projects_used={"obsidian-vault": 88}),
        dict(name="context7", agent="codex", scope="user",
             origin="~/.codex/config.toml", transport="http",
             command="https://mcp.context7.com/mcp", provenance="remote",
             status="remote", instances=0, ram_bytes=0, cpu_pct=None,
             enabled=True, calls=0, calls_30d=0, calls_90d=0, last_used=None,
             tools_count=2, ctx_tokens=900, probe_ms=None, probe_error="",
             projects_used={}),
    ]
    for s in servers:
        s["key"] = f"{s['agent']}::{s['scope']}::{s['name']}"
        s.setdefault("top_tools", {})
        s.setdefault("raw", {})
        s["verdict"] = _demo_verdict(s)
    servers[3]["raw"] = {"command": "python", "env": {"VAULT_API_KEY": "sk-live-9f2b7c41aa"}}

    totals = [980, 1105, 1420, 1230, 1610, 1385, 1755, 1690, 1902, 1740, 1830, 1817]
    history = []
    for i, t in enumerate(totals):
        history.append({"ts": f"2026-08-24T{9 + i:02d}:00:00", "total_mb": t,
                        "servers": {
                            "claude::user::playwright": round(t * 0.44),
                            "claude::user::filesystem": round(t * 0.27),
                            "codex::user::memory": round(t * 0.13),
                            "claude::user::vault-bridge": round(t * 0.12),
                            "claude::project::obsidian-vault": round(t * 0.04)}})

    skill_list = [
        dict(name="asv", source="vault", locked=False, calls=41, calls_30d=12,
             last_used="2026-08-23T10:00:00",
             description="Promote context from the current session into the Agentic Satellite Vault so Nezu and the agent fleet can retrieve it."),
        dict(name="career-ops", source="vault", locked=False, calls=18, calls_30d=5,
             last_used="2026-08-19T16:30:00",
             description="Run the Obsidian-centred Career Advancement Agent Team: prioritisation, role assessment, application planning, interview prep."),
        dict(name="jf", source="vault", locked=False, calls=9, calls_30d=3,
             last_used="2026-08-21T09:15:00",
             description="Pull a Fireflies Teneo Jour Fixe transcript and file it as a JF meeting note matching the vault's established template."),
        dict(name="hallmark", source="vault", locked=True, calls=6, calls_30d=1,
             last_used="2026-08-12T13:00:00",
             description="Anti-AI-slop design skill for greenfield pages, audits, redesigns, and design extraction from URLs or screenshots."),
        dict(name="morning", source="user", locked=False, calls=2, calls_30d=0,
             last_used="2026-07-14T07:05:00",
             description="Render the morning brief as a styled HTML artifact, or set it up as a recurring weekday task."),
        dict(name="skill-creator", source="user", locked=False, calls=0,
             calls_30d=0, last_used=None,
             description="Create new skills, modify and improve existing skills, and measure skill performance with evals."),
        dict(name="asv", source="plugin:vault-tools", locked=False, calls=0,
             calls_30d=0, last_used=None,
             description="Older copy of the ASV promotion skill shipped with a plugin."),
    ]
    return servers, skill_list, history, {"demo": True,
                                          "probe_at": "2026-08-24T21:00:00"}


def _demo_verdict(s):
    if not s["enabled"]:
        return "disabled"
    if s["status"] == "failed" or s.get("probe_error"):
        return "broken"
    if s["calls"] == 0 and (s["ram_bytes"] > 50 * MB or s["ctx_tokens"] > 1500):
        return "unused"
    if s["calls_30d"] == 0 and s["calls"] > 0:
        return "dormant"
    if s["calls_30d"] <= 2 and (s["ram_bytes"] > 250 * MB or s["ctx_tokens"] > 6000):
        return "expensive"
    return "earning" if s["calls_30d"] > 0 else "quiet"
