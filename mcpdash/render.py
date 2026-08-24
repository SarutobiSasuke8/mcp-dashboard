"""HTML rendering for the MCP Dashboard (Servers / Advisor / Skills)."""

from .common import esc, fmt_mb, fmt_tokens

CSS = """
:root {
  --bg:#F4F6F8; --surface:#FFFFFF; --ink:#1B2229; --muted:#5C6873;
  --line:#DDE3E8; --accent:#2F6B8F; --accent-soft:#D8E5ED;
  --cpu:#6B5D95; --cpu-soft:#E4DFF0;
  --ok:#2E7D4F; --ok-soft:#DEEEE4; --bad:#B3413A; --bad-soft:#F3E0DE;
  --warn:#A8752C; --warn-soft:#F1E7D6; --info:#3D5A80; --info-soft:#DEE5EF;
  --off:#5C6873; --off-soft:#E4E8EC;
}
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) {
    --bg:#14181D; --surface:#1C222A; --ink:#E8ECEF; --muted:#93A0AC;
    --line:#2B333D; --accent:#6FA3C4; --accent-soft:#24384A;
    --cpu:#A395CC; --cpu-soft:#2E2941;
    --ok:#63B888; --ok-soft:#1E3529; --bad:#D98A84; --bad-soft:#3D2523;
    --warn:#CDA05F; --warn-soft:#3A2F1D; --info:#8FA9C9; --info-soft:#252F3E;
    --off:#93A0AC; --off-soft:#262D36;
  }
}
:root[data-theme="dark"] {
  --bg:#14181D; --surface:#1C222A; --ink:#E8ECEF; --muted:#93A0AC;
  --line:#2B333D; --accent:#6FA3C4; --accent-soft:#24384A;
  --cpu:#A395CC; --cpu-soft:#2E2941;
  --ok:#63B888; --ok-soft:#1E3529; --bad:#D98A84; --bad-soft:#3D2523;
  --warn:#CDA05F; --warn-soft:#3A2F1D; --info:#8FA9C9; --info-soft:#252F3E;
  --off:#93A0AC; --off-soft:#262D36;
}
* { box-sizing:border-box; margin:0; }
html { background:var(--bg); }
body { background:var(--bg); color:var(--ink);
  font:15px/1.5 "IBM Plex Sans","Segoe UI",system-ui,sans-serif;
  padding:32px 20px 64px; }
main { max-width:1040px; margin:0 auto; display:flex; flex-direction:column; gap:24px; }
header { display:flex; align-items:flex-end; justify-content:space-between;
  gap:16px; flex-wrap:wrap; }
header h1 { font-size:22px; font-weight:600; letter-spacing:-0.01em; }
header .sub { color:var(--muted); font-size:13px; margin-top:4px;
  font-family:"IBM Plex Mono",ui-monospace,Consolas,monospace; }
.tabs { display:flex; gap:4px; background:var(--surface);
  border:1px solid var(--line); border-radius:6px; padding:3px; }
.tabs button { font:inherit; font-size:13.5px; font-weight:500; border:0;
  background:transparent; color:var(--muted); padding:6px 16px;
  border-radius:4px; cursor:pointer; }
.tabs button[aria-selected="true"] { background:var(--accent-soft); color:var(--accent); }
.tabs button:focus-visible, .switch:focus-visible, .btn:focus-visible {
  outline:2px solid var(--accent); outline-offset:1px; }
.tiles { display:grid; grid-template-columns:repeat(auto-fit,minmax(140px,1fr)); gap:12px; }
.tile { background:var(--surface); border:1px solid var(--line);
  border-radius:6px; padding:14px 16px; }
.tile .label { font-size:11px; text-transform:uppercase; letter-spacing:0.08em; color:var(--muted); }
.tile .value { font-size:25px; font-weight:600; margin-top:2px; font-variant-numeric:tabular-nums; }
.tile .value small { font-size:13px; font-weight:500; color:var(--muted); }
.tile.hot .value { color:var(--accent); }
.tile.alert .value { color:var(--bad); }
section { margin-top:24px; }
section:first-child { margin-top:0; }
section h2 { font-size:13px; text-transform:uppercase; letter-spacing:0.08em;
  color:var(--muted); font-weight:600; margin-bottom:10px; }
section h2 .hint { text-transform:none; letter-spacing:0; font-weight:400; }
.card { background:var(--surface); border:1px solid var(--line);
  border-radius:6px; padding:16px; }
.tablewrap { background:var(--surface); border:1px solid var(--line);
  border-radius:6px; overflow-x:auto; }
table { border-collapse:collapse; width:100%; min-width:760px; }
th { text-align:left; font-size:11px; text-transform:uppercase; letter-spacing:0.07em;
  color:var(--muted); font-weight:600; padding:10px 14px; border-bottom:1px solid var(--line); }
td { padding:12px 14px; border-bottom:1px solid var(--line); vertical-align:middle; font-size:14px; }
tr:last-child td { border-bottom:none; }
tr.disabledrow td { opacity:0.55; }
td.name { font-weight:500; }
td.desc { color:var(--muted); font-size:13px; max-width:460px; }
.chiprow { margin-top:4px; display:flex; gap:4px; flex-wrap:wrap; align-items:center; }
.cmd { font-family:"IBM Plex Mono",ui-monospace,Consolas,monospace;
  font-size:11.5px; color:var(--muted); margin-top:3px; max-width:320px;
  overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
.chip { display:inline-block; font-size:11px; padding:1px 7px; border-radius:4px;
  border:1px solid var(--line); color:var(--muted); background:var(--bg); }
.prov, .prov-self { display:inline-block; font-size:11px; font-weight:500;
  padding:1px 8px; border-radius:99px; margin-left:4px; vertical-align:2px; }
.prov { border:1px solid var(--line); color:var(--muted); }
.prov-self { background:var(--accent); color:var(--surface); }
.prov-dim { border-style:dashed; }
.pill { display:inline-flex; align-items:center; gap:6px; font-size:12px;
  font-weight:500; padding:3px 10px; border-radius:99px; white-space:nowrap; }
.pill i { width:7px; height:7px; border-radius:50%; background:currentColor; }
.pill.ok { color:var(--ok); background:var(--ok-soft); }
.pill.bad { color:var(--bad); background:var(--bad-soft); }
.pill.warn { color:var(--warn); background:var(--warn-soft); }
.pill.info { color:var(--info); background:var(--info-soft); }
.pill.off { color:var(--off); background:var(--off-soft); }
.verdict { display:inline-block; font-size:11px; font-weight:500; padding:2px 8px;
  border-radius:4px; margin-top:5px; }
.v-earning { color:var(--ok); background:var(--ok-soft); }
.v-broken, .v-unused { color:var(--bad); background:var(--bad-soft); }
.v-dormant, .v-expensive { color:var(--warn); background:var(--warn-soft); }
.v-quiet, .v-disabled { color:var(--muted); background:var(--off-soft); }
.num { font-family:"IBM Plex Mono",ui-monospace,Consolas,monospace;
  font-variant-numeric:tabular-nums; font-size:13px; }
.sub2 { color:var(--muted); font-size:11.5px; margin-top:2px; white-space:nowrap; }
.ramcell { min-width:120px; }
.usecell { min-width:110px; }
.bar { height:6px; border-radius:4px; background:var(--accent-soft);
  overflow:hidden; margin-bottom:5px; }
.bar.cpu { background:var(--cpu-soft); }
.bar.cpu span { background:var(--cpu); }
.bar.empty { background:transparent; }
.bar span { display:block; height:100%; border-radius:4px; background:var(--accent); }
.spark { width:80px; height:20px; vertical-align:middle; margin-left:6px; }
.spark polyline { fill:none; stroke:var(--accent); stroke-width:1.5; }
.spark circle { fill:var(--accent); }
.switch { width:38px; height:21px; border-radius:99px; border:1px solid var(--line);
  background:var(--off-soft); position:relative; cursor:pointer; padding:0;
  display:inline-block; }
.switch i { position:absolute; top:2px; left:2px; width:15px; height:15px;
  border-radius:50%; background:var(--surface); border:1px solid var(--line);
  transition:left 0.15s; }
.switch.on { background:var(--ok-soft); border-color:var(--ok); }
.switch.on i { left:19px; background:var(--ok); border-color:var(--ok); }
.switch.static { cursor:help; opacity:0.6; }
.btn { font:inherit; font-size:12.5px; font-weight:500; padding:5px 12px;
  border-radius:4px; border:1px solid var(--line); background:var(--surface);
  color:var(--ink); cursor:pointer; }
.btn:hover { border-color:var(--accent); color:var(--accent); }
.btn.primary { background:var(--accent-soft); border-color:var(--accent); color:var(--accent); }
.btn.static { cursor:help; opacity:0.6; }
.rec { display:flex; gap:14px; align-items:flex-start; padding:14px 16px;
  border-bottom:1px solid var(--line); }
.rec:last-child { border-bottom:none; }
.rec .sev { width:4px; align-self:stretch; border-radius:2px; background:var(--muted); flex:none; }
.rec.high .sev { background:var(--bad); }
.rec.medium .sev { background:var(--warn); }
.rec.low .sev { background:var(--info); }
.rec.info .sev { background:var(--line); }
.rec .body { flex:1; min-width:0; }
.rec .title { font-weight:500; font-size:14px; }
.rec .detail { color:var(--muted); font-size:13px; margin-top:3px; }
.rec .act { flex:none; display:flex; align-items:center; gap:8px; }
.saving { font-family:"IBM Plex Mono",ui-monospace,monospace; font-size:12px;
  color:var(--accent); white-space:nowrap; }
.profiles { display:flex; gap:8px; flex-wrap:wrap; align-items:center; }
.hbar { display:grid; grid-template-columns:150px 1fr 64px; gap:10px;
  align-items:center; padding:5px 0; }
.hbar .track { height:10px; border-radius:3px; background:var(--accent-soft); overflow:hidden; }
.hbar .track span { display:block; height:100%; background:var(--accent); border-radius:3px; }
.hbar .lbl { font-size:13px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
svg[role="img"] { width:100%; height:auto; display:block; }
.grid { stroke:var(--line); stroke-width:1; }
.axis { fill:var(--muted); font:11px "IBM Plex Mono",ui-monospace,monospace; }
.endlabel { fill:var(--accent); font:12px "IBM Plex Mono",ui-monospace,monospace; font-weight:500; }
.chart-area { fill:var(--accent); opacity:0.12; }
.chart-line { fill:none; stroke:var(--accent); stroke-width:2;
  stroke-linejoin:round; stroke-linecap:round; }
.dot { fill:var(--accent); }
.dot.end { stroke:var(--surface); stroke-width:1.5; }
.chart-empty, .emptymsg { color:var(--muted); font-size:13.5px; }
.chart-empty code, .emptymsg code { font-family:"IBM Plex Mono",ui-monospace,monospace; font-size:12px; }
footer { color:var(--muted); font-size:12.5px; line-height:1.6; }
footer code { font-family:"IBM Plex Mono",ui-monospace,Consolas,monospace; font-size:11.5px; }
[hidden] { display:none !important; }
@media (prefers-reduced-motion: reduce) { .switch i { transition:none; } }
"""

STATUS_META = {
    "connected": ("ok", "Connected"), "failed": ("bad", "Failed"),
    "running": ("ok", "Running"), "idle": ("warn", "Configured, idle"),
    "remote": ("info", "Remote"), "disabled": ("off", "Disabled"),
    "unknown": ("warn", "Unknown"),
}
PROV_META = {
    "self-built": ("prov-self", "yours"), "official": ("prov", "official"),
    "vendor": ("prov", "vendor"), "community": ("prov", "community"),
    "remote": ("prov", "remote"), "unknown": ("prov prov-dim", "unlabeled"),
}
VERDICT_TEXT = {
    "earning": "earning its keep", "unused": "unused", "dormant": "dormant",
    "expensive": "costly vs use", "broken": "broken", "quiet": "quiet",
    "disabled": "disabled",
}


# ---------------------------------------------------------------------------
# Charts
# ---------------------------------------------------------------------------

def svg_history_chart(history, width=940, height=190):
    if len(history) < 2:
        return ('<div class="chart-empty">The RAM trend needs at least two '
                'scans. Run the script again later, or schedule it with '
                '<code>Register-MCPDashboardScan.ps1</code>, and the line '
                'appears here.</div>')
    pts = [h.get("total_mb", 0) for h in history]
    labels = [h.get("ts", "")[11:16] for h in history]
    if len({h.get("ts", "")[:10] for h in history}) > 1:
        labels = [h.get("ts", "")[5:10] for h in history]
    top = max(pts) or 1
    top = (int(top / 100) + 1) * 100 if top > 100 else (int(top / 10) + 1) * 10
    pad_l, pad_r, pad_t, pad_b = 46, 70, 12, 24
    iw, ih = width - pad_l - pad_r, height - pad_t - pad_b

    def x(i):
        return pad_l + iw * i / (len(pts) - 1)

    def y(v):
        return pad_t + ih * (1 - v / top)

    line = " ".join(f"{x(i):.1f},{y(v):.1f}" for i, v in enumerate(pts))
    area = f"{pad_l:.1f},{pad_t + ih:.1f} {line} {x(len(pts) - 1):.1f},{pad_t + ih:.1f}"
    grid = ""
    for g in range(5):
        gy = pad_t + ih * g / 4
        grid += (f'<line class="grid" x1="{pad_l}" y1="{gy:.1f}" x2="{width - pad_r}" '
                 f'y2="{gy:.1f}"/><text class="axis" x="{pad_l - 8}" y="{gy + 4:.1f}" '
                 f'text-anchor="end">{top * (4 - g) / 4:g}</text>')
    dots = ""
    for i, v in enumerate(pts):
        cls = "dot end" if i == len(pts) - 1 else "dot"
        dots += (f'<circle class="{cls}" cx="{x(i):.1f}" cy="{y(v):.1f}" '
                 f'r="{4 if i == len(pts) - 1 else 2.5}"><title>'
                 f'{esc(history[i].get("ts", ""))}: {v:g} MB</title></circle>')
    step = max(1, len(labels) // 10)
    ticks = "".join(f'<text class="axis" x="{x(i):.1f}" y="{height - 6}" '
                    f'text-anchor="middle">{esc(labels[i])}</text>'
                    for i in range(0, len(labels), step))
    return (f'<svg viewBox="0 0 {width} {height}" role="img" aria-label="Total '
            f'local MCP RAM over time, latest {pts[-1]:g} megabytes">{grid}'
            f'<polygon class="chart-area" points="{area}"/>'
            f'<polyline class="chart-line" points="{line}"/>{dots}{ticks}'
            f'<text class="endlabel" x="{x(len(pts) - 1) + 10:.1f}" '
            f'y="{y(pts[-1]) + 4:.1f}">{pts[-1]:g} MB</text></svg>')


def svg_sparkline(series, width=80, height=20):
    vals = [v for v in series if v is not None]
    if len(vals) < 2:
        return ""
    top = max(vals) or 1
    step = width / (len(vals) - 1)
    pts = " ".join(f"{i * step:.1f},{(height - 2) * (1 - v / top) + 1:.1f}"
                   for i, v in enumerate(vals))
    lx, ly = (len(vals) - 1) * step, (height - 2) * (1 - vals[-1] / top) + 1
    return (f'<svg class="spark" viewBox="0 0 {width} {height}" aria-hidden="true">'
            f'<polyline points="{pts}"/><circle cx="{lx:.1f}" cy="{ly:.1f}" r="2"/></svg>')


def hbar_list(rows, unit=""):
    """rows: [(label, value, note)] — single-hue magnitude bars."""
    if not rows:
        return '<div class="emptymsg">No recorded activity yet.</div>'
    top = max(v for _, v, _ in rows) or 1
    out = []
    for label, value, note in rows:
        w = max(1, round(value / top * 100))
        out.append(f'<div class="hbar"><div class="lbl">{esc(label)}</div>'
                   f'<div class="track"><span style="width:{w}%"></span></div>'
                   f'<div class="num">{value:g}{unit}</div></div>')
    return "".join(out)


# ---------------------------------------------------------------------------
# Page
# ---------------------------------------------------------------------------

def render_html(servers, skills, history, recs, secrets, shadowed, meta,
                profiles=None, live=False, token=""):
    stdio = sorted([s for s in servers if s["transport"] == "stdio"],
                   key=lambda s: (-s.get("ram_bytes", 0), s["name"]))
    remote = sorted([s for s in servers if s["transport"] != "stdio"],
                    key=lambda s: (-s.get("calls_30d", 0), s["name"]))
    enabled = [s for s in servers if s.get("enabled", True)]
    total_ram = sum(s.get("ram_bytes", 0) for s in stdio)
    total_tokens = sum(s.get("ctx_tokens", 0) for s in enabled)
    total_calls = sum(s.get("calls_30d", 0) for s in servers)
    running = sum(1 for s in stdio if s.get("instances", 0) > 0)
    disabled_n = sum(1 for s in servers if not s.get("enabled", True))
    mine = sum(1 for s in servers if s.get("provenance") == "self-built")
    reclaimable = sum(r["saving_bytes"] for r in recs if r["action"] == "disable")
    high = sum(1 for r in recs if r["severity"] == "high")
    max_ram = max([s.get("ram_bytes", 0) for s in stdio], default=0) or 1
    max_cpu = max([s.get("cpu_pct") or 0 for s in stdio], default=0) or 1

    hist_by_key = {}
    for h in history:
        for k, v in (h.get("servers") or {}).items():
            hist_by_key.setdefault(k, []).append(v)

    def toggle(s):
        state = "on" if s.get("enabled", True) else "off"
        if live:
            return (f'<button class="switch {state}" data-key="{esc(s["key"])}" '
                    f'role="switch" aria-checked="{"true" if state == "on" else "false"}" '
                    f'aria-label="Toggle {esc(s["name"])}"><i></i></button>')
        return (f'<span class="switch {state} static" title="Toggles work in live '
                f'mode: python mcp_dashboard.py --serve"><i></i></span>')

    def prov_chip(s):
        cls, label = PROV_META.get(s.get("provenance", "unknown"),
                                   ("prov", s.get("provenance", "")))
        return f'<span class="{cls}">{esc(label)}</span>'

    def name_cell(s):
        return (f'<td class="name">{esc(s["name"])} {prov_chip(s)}'
                f'<div class="chiprow"><span class="chip">{esc(s["agent"])}</span>'
                f'<span class="chip">{esc(s["scope"])}</span>'
                f'<span class="chip">{esc(s["transport"])}</span></div>'
                f'<div class="cmd">{esc(s["command"])}</div></td>')

    def status_cell(s):
        st = "disabled" if not s.get("enabled", True) else s.get("status", "unknown")
        cls, label = STATUS_META.get(st, STATUS_META["unknown"])
        v = s.get("verdict") or "quiet"
        return (f'<td><span class="pill {cls}"><i></i>{label}</span>'
                f'<div><span class="verdict v-{v}">{VERDICT_TEXT.get(v, v)}</span></div></td>')

    def use_cell(s):
        c30, last = s.get("calls_30d", 0), s.get("last_used")
        sub = (f'<div class="sub2">last {last[:10]}</div>' if last
               else '<div class="sub2">never</div>')
        return f'<td class="usecell"><span class="num">{c30}</span>{sub}</td>'

    def ctx_cell(s):
        tok, tools = s.get("ctx_tokens", 0), s.get("tools_count", 0)
        if not tok:
            return ('<td><span class="num">—</span>'
                    '<div class="sub2">not probed</div></td>')
        return (f'<td><span class="num">{fmt_tokens(tok)}</span>'
                f'<div class="sub2">{tools} tools</div></td>')

    def stdio_row(s):
        ram = s.get("ram_bytes", 0)
        cpu = s.get("cpu_pct")
        bar = (f'<div class="bar"><span style="width:{max(2, round(ram / max_ram * 100))}%">'
               f'</span></div>' if ram else '<div class="bar empty"></div>')
        cpucell = (f'<div class="bar cpu"><span style="width:'
                   f'{max(2, round((cpu or 0) / max_cpu * 100))}%"></span></div>'
                   f'<span class="num">{cpu:g}%</span>' if cpu
                   else '<span class="num">—</span>')
        inst = s.get("instances", 0)
        dis = "" if s.get("enabled", True) else ' class="disabledrow"'
        return (f"<tr{dis}>{name_cell(s)}{status_cell(s)}{use_cell(s)}{ctx_cell(s)}"
                f'<td class="num">{f"{inst}&times;" if inst else "&mdash;"}</td>'
                f'<td class="ramcell">{cpucell}</td>'
                f'<td class="ramcell">{bar}<span class="num">'
                f'{fmt_mb(ram) if ram else "&mdash;"}</span>'
                f'{svg_sparkline(hist_by_key.get(s["key"], []))}</td>'
                f"<td>{toggle(s)}</td></tr>")

    def remote_row(s):
        dis = "" if s.get("enabled", True) else ' class="disabledrow"'
        return (f"<tr{dis}>{name_cell(s)}{status_cell(s)}{use_cell(s)}{ctx_cell(s)}"
                f"<td>{toggle(s)}</td></tr>")

    stdio_rows = "".join(stdio_row(s) for s in stdio) or \
        '<tr><td colspan="8" class="emptymsg">No local stdio MCP servers configured.</td></tr>'
    remote_rows = "".join(remote_row(s) for s in remote) or \
        ('<tr><td colspan="5" class="emptymsg">No HTTP/SSE servers in local config. '
         'claude.ai connectors live server-side and never appear here — and never '
         'cost local RAM (their usage still shows once you call them).</td></tr>')

    # --- Advisor ---------------------------------------------------------
    def rec_card(r):
        act = ""
        if r["action"] == "disable" and r["key"]:
            act = ((f'<button class="btn primary" data-key="{esc(r["key"])}" '
                    f'data-act="off">Switch off</button>') if live else
                   '<span class="btn static" title="Run with --serve to act '
                   'from here">Switch off</span>')
        saving = (f'<span class="saving">−{fmt_mb(r["saving_bytes"])}</span>'
                  if r["saving_bytes"] else "")
        return (f'<div class="rec {r["severity"]}"><div class="sev"></div>'
                f'<div class="body"><div class="title">{esc(r["title"])}</div>'
                f'<div class="detail">{esc(r["detail"])}</div></div>'
                f'<div class="act">{saving}{act}</div></div>')

    rec_html = "".join(rec_card(r) for r in recs) or \
        ('<div class="rec info"><div class="sev"></div><div class="body">'
         '<div class="title">Nothing to act on</div><div class="detail">'
         'Every configured server is either in use or cheap enough to keep. '
         'Run with <code>--probe</code> to add context-cost findings.</div>'
         '</div></div>')

    prof_html = ""
    if profiles:
        btns = []
        for name, members in sorted(profiles.items()):
            label = f"{esc(name)} ({len(members)})"
            btns.append((f'<button class="btn" data-profile="{esc(name)}">{label}</button>')
                        if live else
                        f'<span class="btn static" title="Run with --serve to apply">{label}</span>')
        prof_html = (f'<section><h2>Profiles <span class="hint">— apply a set, '
                     f'disable everything else</span></h2><div class="card">'
                     f'<div class="profiles">{"".join(btns)}</div></div></section>')

    usage_rows = [(f"{s['name']}", s.get("calls_30d", 0), "")
                  for s in sorted(servers, key=lambda s: -s.get("calls_30d", 0))[:10]
                  if s.get("calls_30d", 0) > 0]
    cost_rows = [(f"{s['name']}", round(s.get("ram_bytes", 0) / 1048576), "")
                 for s in stdio[:10] if s.get("ram_bytes", 0) > 0]

    secret_html = ""
    if secrets:
        items = "".join(
            f'<div class="rec high"><div class="sev"></div><div class="body">'
            f'<div class="title">{esc(f["var"])} in {esc(f["server"])} '
            f'({esc(f["agent"])})</div><div class="detail">Value {esc(f["preview"])} '
            f'stored in plaintext in {esc(f["origin"])}.</div></div></div>'
            for f in secrets)
        secret_html = (f'<section><h2>Credentials in config</h2>'
                       f'<div class="tablewrap">{items}</div></section>')

    # --- Skills ----------------------------------------------------------
    def skill_row(sk):
        chips = f'<span class="chip">{esc(sk["source"])}</span>'
        if sk.get("locked"):
            chips += '<span class="chip">locked</span>'
        if sk.get("shadowed_by"):
            chips += f'<span class="chip">shadowed by {esc(sk["shadowed_by"])}</span>'
        last = sk.get("last_used")
        desc = sk.get("description", "")
        return (f'<tr><td class="name">{esc(sk["name"])}'
                f'<div class="chiprow">{chips}</div></td>'
                f'<td><span class="num">{sk.get("calls_30d", 0)}</span>'
                f'<div class="sub2">{("last " + last[:10]) if last else "never"}</div></td>'
                f'<td class="desc">{esc(desc[:200] + ("…" if len(desc) > 200 else "")) or "—"}</td></tr>')

    skills_sorted = sorted(skills, key=lambda s: (-s.get("calls_30d", 0),
                                                  s["source"], s["name"]))
    skill_rows = "".join(skill_row(s) for s in skills_sorted) or \
        '<tr><td colspan="3" class="emptymsg">No skills found.</td></tr>'
    shadow_html = ""
    if shadowed:
        items = "".join(
            f'<div class="rec low"><div class="sev"></div><div class="body">'
            f'<div class="title">{esc(s["name"])} is defined more than once</div>'
            f'<div class="detail">Loaded from <strong>{esc(s["winner"])}</strong>; '
            f'also present in {esc(", ".join(s["others"]))}.</div></div></div>'
            for s in shadowed)
        shadow_html = (f'<section><h2>Name collisions</h2>'
                       f'<div class="tablewrap">{items}</div></section>')
    skill_used = sum(1 for s in skills if s.get("calls_30d", 0) > 0)

    live_js = """
<script>
var MCP_TOKEN = '__TOKEN__';
function post(url, body, ok) {
  fetch(url, {method:'POST', headers:{'Content-Type':'application/json',
      'X-MCP-Token': MCP_TOKEN},
    body: JSON.stringify(body)}).then(r => r.json()).then(j => {
      if (!j.ok) { alert('Failed: ' + j.message); ok(false); }
      else { location.reload(); }
    }).catch(e => { alert('Failed: ' + e); ok(false); });
}
document.querySelectorAll('button.switch').forEach(function (btn) {
  btn.addEventListener('click', function () {
    btn.disabled = true;
    post('/api/toggle', {key: btn.dataset.key}, function () { btn.disabled = false; });
  });
});
document.querySelectorAll('button[data-act="off"]').forEach(function (btn) {
  btn.addEventListener('click', function () {
    btn.disabled = true;
    post('/api/set', {key: btn.dataset.key, enabled: false},
         function () { btn.disabled = false; });
  });
});
document.querySelectorAll('button[data-profile]').forEach(function (btn) {
  btn.addEventListener('click', function () {
    if (!confirm('Apply profile "' + btn.dataset.profile + '"? Servers not in it '
                 + 'will be switched off.')) return;
    btn.disabled = true;
    post('/api/profile', {name: btn.dataset.profile},
         function () { btn.disabled = false; });
  });
});
</script>""".replace("__TOKEN__", token)

    cpu_note = ("a live sample" if meta.get("psutil")
                else "the process-lifetime average (install psutil for live sampling)")
    probe_note = (f"probed {meta.get('probe_at', '')[:16].replace('T', ' ')}"
                  if meta.get("probe_at") else
                  "run with <code>--probe</code> to measure context cost and startup time")

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>MCP Server Dashboard</title>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap">
<style>{CSS}</style>
</head>
<body>
<main>
  <header>
    <div>
      <h1>MCP Server Dashboard</h1>
      <div class="sub">scanned {esc(meta['when'])} &middot; host {esc(meta['host'])}{' &middot; LIVE' if live else ''}{' &middot; DEMO DATA' if meta.get('demo') else ''}</div>
    </div>
    <nav class="tabs" role="tablist">
      <button role="tab" aria-selected="true" data-tab="mcp">Servers</button>
      <button role="tab" aria-selected="false" data-tab="advisor">Advisor{f' ({high})' if high else ''}</button>
      <button role="tab" aria-selected="false" data-tab="skills">Skills</button>
    </nav>
  </header>

  <div id="view-mcp">
  <div class="tiles">
    <div class="tile"><div class="label">Configured</div>
      <div class="value">{len(servers)}<small> / {disabled_n} off</small></div></div>
    <div class="tile"><div class="label">Running locally</div>
      <div class="value">{running}<small> / {len(stdio)} stdio</small></div></div>
    <div class="tile hot"><div class="label">Local RAM</div>
      <div class="value">{fmt_mb(total_ram)}</div></div>
    <div class="tile"><div class="label">Context cost</div>
      <div class="value">{fmt_tokens(total_tokens)}<small> tok</small></div></div>
    <div class="tile"><div class="label">Calls (30d)</div>
      <div class="value">{total_calls}</div></div>
    <div class="tile"><div class="label">Built by you</div>
      <div class="value">{mine}</div></div>
  </div>

  <section>
    <h2>Local MCP RAM over time</h2>
    <div class="card">{svg_history_chart(history)}</div>
  </section>

  <section>
    <h2>Local stdio servers <span class="hint">&mdash; RAM cost is per open session</span></h2>
    <div class="tablewrap">
    <table>
      <thead><tr><th>Server</th><th>Status</th><th>Calls 30d</th><th>Context</th>
        <th>Procs</th><th>CPU</th><th>RAM</th><th>On</th></tr></thead>
      <tbody>{stdio_rows}</tbody>
    </table>
    </div>
  </section>

  <section>
    <h2>Remote servers <span class="hint">&mdash; no local RAM, but still context cost</span></h2>
    <div class="tablewrap">
    <table>
      <thead><tr><th>Server</th><th>Status</th><th>Calls 30d</th><th>Context</th><th>On</th></tr></thead>
      <tbody>{remote_rows}</tbody>
    </table>
    </div>
  </section>
  </div>

  <div id="view-advisor" hidden>
  <div class="tiles">
    <div class="tile{' alert' if high else ''}"><div class="label">Needs attention</div>
      <div class="value">{high}</div></div>
    <div class="tile hot"><div class="label">Reclaimable RAM</div>
      <div class="value">{fmt_mb(reclaimable)}</div></div>
    <div class="tile"><div class="label">Context tokens</div>
      <div class="value">{fmt_tokens(total_tokens)}</div></div>
    <div class="tile"><div class="label">Credentials exposed</div>
      <div class="value">{len(secrets)}</div></div>
  </div>

  <section>
    <h2>Recommendations <span class="hint">&mdash; cost weighed against recorded use</span></h2>
    <div class="tablewrap">{rec_html}</div>
  </section>

  {prof_html}

  <section>
    <h2>Most used servers (30 days)</h2>
    <div class="card">{hbar_list(usage_rows)}</div>
  </section>

  <section>
    <h2>Heaviest servers (RAM)</h2>
    <div class="card">{hbar_list(cost_rows, unit=" MB")}</div>
  </section>

  {secret_html}
  </div>

  <div id="view-skills" hidden>
  <div class="tiles">
    <div class="tile hot"><div class="label">Skills installed</div>
      <div class="value">{len(skills)}</div></div>
    <div class="tile"><div class="label">Used (30d)</div>
      <div class="value">{skill_used}</div></div>
    <div class="tile"><div class="label">Sources</div>
      <div class="value">{len({s['source'] for s in skills})}</div></div>
    <div class="tile"><div class="label">Collisions</div>
      <div class="value">{len(shadowed)}</div></div>
  </div>
  <section>
    <h2>Skill directory <span class="hint">&mdash; vault, project, user, synced, plugins</span></h2>
    <div class="tablewrap">
    <table>
      <thead><tr><th>Skill</th><th>Calls 30d</th><th>Description</th></tr></thead>
      <tbody>{skill_rows}</tbody>
    </table>
    </div>
  </section>
  {shadow_html}
  </div>

  <footer>
    Each <strong>stdio</strong> server is a real OS process spawned per agent
    session &mdash; three open sessions run every stdio server three times.
    Context cost is the tool schemas a server injects into every request;
    {probe_note}. CPU is {cpu_note}. Usage comes from your Claude Code and
    Codex transcripts. Provenance:
    <span class="prov-self" style="vertical-align:0">yours</span> = servers you
    built (label them in <code>mcp-provenance.json</code>). Switching a server
    off stashes its config for later; running sessions keep their processes
    until restarted.
    Regenerate: <code>python mcp_dashboard.py --open</code> &middot;
    live control: <code>python mcp_dashboard.py --serve</code>
  </footer>
</main>
<script>
document.querySelectorAll('.tabs button').forEach(function (btn) {{
  btn.addEventListener('click', function () {{
    document.querySelectorAll('.tabs button').forEach(function (b) {{
      b.setAttribute('aria-selected', b === btn ? 'true' : 'false');
    }});
    ['mcp', 'advisor', 'skills'].forEach(function (t) {{
      document.getElementById('view-' + t).hidden = btn.dataset.tab !== t;
    }});
  }});
}});
</script>
{live_js if live else ''}
</body>
</html>
"""
