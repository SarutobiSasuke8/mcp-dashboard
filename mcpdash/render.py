"""HTML rendering for the MCP Dashboard (Servers / Advisor / Skills)."""

from .common import esc, fmt_mb, fmt_tokens

CSS = """/* Hallmark · pre-emit critique: P5 H5 E4 S5 R5 V4 */
/* Hallmark · genre: modern-minimal · macrostructure: Workbench · designed-as-app */
:root {
  color-scheme:light;
  --font-display:"Bahnschrift","Aptos Display","Arial Narrow","Segoe UI",sans-serif;
  --font-body:"Segoe UI Variable Text","Aptos","Segoe UI",sans-serif;
  --font-mono:"Cascadia Code","SFMono-Regular","Liberation Mono",monospace;
  --bg:oklch(97.2% 0.007 240); --surface:oklch(99.1% 0.004 240);
  --surface-raised:oklch(100% 0.002 240); --ink:oklch(23% 0.018 240);
  --muted:oklch(47% 0.018 240); --line:oklch(87% 0.012 240);
  --line-strong:oklch(75% 0.018 240); --accent:oklch(53% 0.14 238);
  --accent-ink:oklch(98% 0.006 240); --accent-soft:oklch(92% 0.035 238);
  --cpu:oklch(55% 0.10 292); --cpu-soft:oklch(92% 0.025 292);
  --ok:oklch(47% 0.12 155); --ok-soft:oklch(92% 0.035 155);
  --bad:oklch(48% 0.17 28); --bad-soft:oklch(93% 0.035 28);
  --warn:oklch(49% 0.11 75); --warn-soft:oklch(93% 0.04 75);
  --info:oklch(46% 0.09 250); --info-soft:oklch(92% 0.03 250);
  --off:oklch(47% 0.018 240); --off-soft:oklch(91% 0.012 240);
  --shadow:0 1px 2px oklch(20% 0.015 240 / 0.06);
  --space-3xs:0.125rem; --space-2xs:0.25rem; --space-xs:0.5rem;
  --space-sm:0.75rem; --space-md:1rem; --space-lg:1.5rem;
  --space-xl:2.5rem; --space-2xl:4rem; --space-3xl:6rem;
  --text-xs:0.75rem; --text-sm:0.875rem; --text-base:1rem;
  --text-md:1.25rem; --text-lg:1.5625rem; --text-xl:1.953rem;
  --radius-sm:0.375rem; --radius-md:0.625rem; --radius-pill:99rem;
  --ease-out:cubic-bezier(0.16,1,0.3,1); --ease-in:cubic-bezier(0.7,0,0.84,0);
  --ease-in-out:cubic-bezier(0.65,0,0.35,1); --dur-micro:120ms; --dur-short:220ms;
}
@media (prefers-color-scheme:dark) {
  :root:not([data-theme="light"]) {
    color-scheme:dark; --bg:oklch(16% 0.012 240); --surface:oklch(20% 0.015 240);
    --surface-raised:oklch(23% 0.016 240); --ink:oklch(94% 0.008 240);
    --muted:oklch(72% 0.018 240); --line:oklch(30% 0.018 240);
    --line-strong:oklch(43% 0.022 240); --accent:oklch(72% 0.11 238);
    --accent-ink:oklch(16% 0.02 240); --accent-soft:oklch(27% 0.045 238);
    --cpu:oklch(73% 0.09 292); --cpu-soft:oklch(28% 0.035 292);
    --ok:oklch(74% 0.11 155); --ok-soft:oklch(27% 0.045 155);
    --bad:oklch(72% 0.14 28); --bad-soft:oklch(28% 0.05 28);
    --warn:oklch(76% 0.10 75); --warn-soft:oklch(29% 0.045 75);
    --info:oklch(74% 0.08 250); --info-soft:oklch(28% 0.035 250);
    --off:oklch(70% 0.018 240); --off-soft:oklch(27% 0.015 240);
    --shadow:0 1px 2px oklch(5% 0.01 240 / 0.35);
  }
}
:root[data-theme="dark"] {
  color-scheme:dark; --bg:oklch(16% 0.012 240); --surface:oklch(20% 0.015 240);
  --surface-raised:oklch(23% 0.016 240); --ink:oklch(94% 0.008 240);
  --muted:oklch(72% 0.018 240); --line:oklch(30% 0.018 240);
  --line-strong:oklch(43% 0.022 240); --accent:oklch(72% 0.11 238);
  --accent-ink:oklch(16% 0.02 240); --accent-soft:oklch(27% 0.045 238);
  --cpu:oklch(73% 0.09 292); --cpu-soft:oklch(28% 0.035 292);
  --ok:oklch(74% 0.11 155); --ok-soft:oklch(27% 0.045 155);
  --bad:oklch(72% 0.14 28); --bad-soft:oklch(28% 0.05 28);
  --warn:oklch(76% 0.10 75); --warn-soft:oklch(29% 0.045 75);
  --info:oklch(74% 0.08 250); --info-soft:oklch(28% 0.035 250);
  --off:oklch(70% 0.018 240); --off-soft:oklch(27% 0.015 240);
  --shadow:0 1px 2px oklch(5% 0.01 240 / 0.35);
}
* { box-sizing:border-box; }
html, body { margin:0; overflow-x:clip; background:var(--bg); }
body { min-width:0; color:var(--ink); font:var(--text-base)/1.55 var(--font-body);
  padding-block:var(--space-lg) max(var(--space-2xl),env(safe-area-inset-bottom));
  padding-inline:max(var(--space-md),env(safe-area-inset-left)); }
button, input { font:inherit; }
main { width:min(100%,74rem); margin-inline:auto; display:flex; flex-direction:column;
  gap:var(--space-xl); min-width:0; }
header { display:grid; gap:var(--space-md); align-items:end; }
.brandline { display:flex; gap:var(--space-sm); align-items:center; min-width:0; }
.brandmark { display:grid; place-items:center; width:2.25rem; height:2.25rem; flex:none;
  border-radius:var(--radius-sm); background:var(--ink); color:var(--bg);
  font:600 var(--text-xs)/1 var(--font-mono); letter-spacing:-0.04em; }
header h1 { margin:0; min-width:0; overflow-wrap:anywhere; font:700 var(--text-lg)/1.15 var(--font-display);
  letter-spacing:-0.035em; }
header .sub { color:var(--muted); font:var(--text-xs)/1.5 var(--font-mono); margin-top:var(--space-2xs); }
.header-actions { display:flex; gap:var(--space-xs); align-items:center; flex-wrap:wrap; min-width:0; }
.tabs { order:2; width:100%; display:flex; gap:var(--space-2xs); padding:var(--space-2xs);
  align-items:center; overflow-x:auto; background:var(--surface); border:1px solid var(--line);
  border-radius:var(--radius-md); box-shadow:var(--shadow); }
.tabs button, .theme-toggle { min-height:2.75rem; border:0; white-space:nowrap; cursor:pointer;
  border-radius:var(--radius-sm); color:var(--muted); background:transparent;
  font-size:var(--text-sm); font-weight:650; }
.tabs button { flex:1; padding-inline:var(--space-md); }
.tabs button[aria-selected="true"] { background:var(--accent-soft); color:var(--accent); }
.theme-toggle { order:1; margin-inline-start:auto; padding-inline:var(--space-sm);
  border:1px solid var(--line); background:var(--surface); box-shadow:var(--shadow); }
:focus-visible { outline:2px solid var(--accent); outline-offset:2px; }
.status-message { padding:var(--space-sm) var(--space-md); border:1px solid var(--bad);
  border-radius:var(--radius-sm); color:var(--bad); background:var(--bad-soft); }
.status-message:empty { display:none; }
.tiles { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:var(--space-sm); }
.tile { min-width:0; padding:var(--space-md); background:var(--surface);
  border:1px solid var(--line); border-radius:var(--radius-md); box-shadow:var(--shadow); }
.tile .label { color:var(--muted); font-size:var(--text-xs); font-weight:650;
  letter-spacing:0.07em; text-transform:uppercase; }
.tile .value { min-width:0; margin-top:var(--space-2xs); overflow-wrap:anywhere;
  font:700 var(--text-xl)/1.15 var(--font-display); letter-spacing:-0.035em;
  font-variant-numeric:tabular-nums; }
.tile .value small { color:var(--muted); font:600 var(--text-xs)/1.2 var(--font-body); letter-spacing:0; }
.tile.hot .value { color:var(--accent); }
.tile.alert .value { color:var(--bad); }
section { margin-top:var(--space-xl); }
section:first-child { margin-top:0; }
section h2 { min-width:0; margin:0 0 var(--space-sm); overflow-wrap:anywhere;
  color:var(--ink); font:700 var(--text-base)/1.25 var(--font-display); letter-spacing:-0.015em; }
section h2 .hint { color:var(--muted); font:400 var(--text-sm)/1.4 var(--font-body); }
.card { min-width:0; padding:var(--space-md); background:var(--surface);
  border:1px solid var(--line); border-radius:var(--radius-md); box-shadow:var(--shadow); }
.toolbar { display:flex; gap:var(--space-sm); align-items:end; justify-content:space-between;
  margin-block:var(--space-lg) var(--space-md); flex-wrap:wrap; }
.search { display:grid; gap:var(--space-2xs); width:min(100%,24rem); color:var(--muted);
  font-size:var(--text-xs); font-weight:650; }
.search input { width:100%; min-height:2.75rem; padding-inline:var(--space-sm);
  border:1px solid var(--line-strong); outline:2px solid transparent; outline-offset:1px;
  border-radius:var(--radius-sm); color:var(--ink); background:var(--surface); }
.search input:focus-visible { outline-color:var(--accent); border-color:var(--line-strong); }
.search input:disabled { cursor:not-allowed; opacity:0.55; background:var(--off-soft); }
.filter-summary { min-height:1.25rem; color:var(--muted); font-size:var(--text-sm); }
.tablewrap { min-width:0; background:transparent; }
table, thead, tbody, tr, th, td { display:block; }
table { width:100%; border-collapse:collapse; }
thead { position:absolute; width:1px; height:1px; overflow:hidden; clip-path:inset(50%); }
tbody { display:grid; gap:var(--space-sm); }
tr { padding:var(--space-xs) var(--space-sm); background:var(--surface);
  border:1px solid var(--line); border-radius:var(--radius-md); box-shadow:var(--shadow); }
tr[hidden] { display:none; }
td { display:grid; grid-template-columns:minmax(6.5rem,0.38fr) minmax(0,1fr); gap:var(--space-sm);
  align-items:start; padding:var(--space-xs) 0; border-bottom:1px solid var(--line);
  font-size:var(--text-sm); min-width:0; }
td:last-child { border-bottom:0; }
td::before { content:attr(data-label); color:var(--muted); font-size:var(--text-xs);
  font-weight:650; letter-spacing:0.06em; text-transform:uppercase; }
tr.disabledrow td { opacity:0.58; }
td.name { font-weight:650; }
td.desc { color:var(--muted); max-width:60ch; }
.chiprow { margin-top:var(--space-2xs); display:flex; gap:var(--space-2xs); flex-wrap:wrap; align-items:center; }
.cmd { max-width:100%; margin-top:var(--space-2xs); overflow:hidden; text-overflow:ellipsis;
  white-space:nowrap; color:var(--muted); font:var(--text-xs)/1.4 var(--font-mono); }
.chip, .prov, .prov-self { display:inline-block; padding:var(--space-3xs) var(--space-xs);
  border-radius:var(--radius-pill); font-size:var(--text-xs); font-weight:600; }
.chip, .prov { border:1px solid var(--line); color:var(--muted); background:var(--bg); }
.prov, .prov-self { margin-inline-start:var(--space-2xs); vertical-align:0.08rem; }
.prov-self { color:var(--accent-ink); background:var(--accent); }
.prov-dim { border-style:dashed; }
.pill { display:inline-flex; align-items:center; gap:var(--space-xs);
  padding:var(--space-3xs) var(--space-xs);
  border-radius:var(--radius-pill); white-space:nowrap; font-size:var(--text-xs); font-weight:650; }
.pill i { width:0.45rem; height:0.45rem; border-radius:50%; background:currentColor; }
.pill.ok { color:var(--ok); background:var(--ok-soft); }
.pill.bad { color:var(--bad); background:var(--bad-soft); }
.pill.warn { color:var(--warn); background:var(--warn-soft); }
.pill.info { color:var(--info); background:var(--info-soft); }
.pill.off { color:var(--off); background:var(--off-soft); }
.verdict { display:inline-block; margin-top:var(--space-2xs);
  padding:var(--space-3xs) var(--space-xs);
  border-radius:var(--radius-sm); font-size:var(--text-xs); font-weight:650; }
.v-earning { color:var(--ok); background:var(--ok-soft); }
.v-broken, .v-unused { color:var(--bad); background:var(--bad-soft); }
.v-dormant, .v-expensive { color:var(--warn); background:var(--warn-soft); }
.v-quiet, .v-disabled { color:var(--muted); background:var(--off-soft); }
.num { font:var(--text-sm)/1.4 var(--font-mono); font-variant-numeric:tabular-nums; }
.sub2 { margin-top:var(--space-3xs); color:var(--muted); font-size:var(--text-xs); white-space:nowrap; }
.bar { height:0.4rem; margin-bottom:var(--space-2xs); overflow:hidden;
  border-radius:var(--radius-pill); background:var(--accent-soft); }
.bar.cpu { background:var(--cpu-soft); }
.bar.cpu span { background:var(--cpu); }
.bar.empty { background:transparent; }
.bar span { display:block; height:100%; border-radius:inherit; background:var(--accent); }
.spark { width:5rem; height:1.25rem; vertical-align:middle; margin-inline-start:var(--space-xs); }
.spark polyline { fill:none; stroke:var(--accent); stroke-width:1.5; }
.spark circle { fill:var(--accent); }
.switch { position:relative; display:inline-grid; place-items:center; width:2.75rem; height:2.75rem;
  padding:0; border:0; border-radius:var(--radius-pill); background:transparent; cursor:pointer; }
.switch::before { content:""; position:absolute; width:2.35rem; height:1.35rem;
  border:1px solid var(--line-strong); border-radius:var(--radius-pill); background:var(--off-soft); }
.switch i { position:relative; width:0.95rem; height:0.95rem; margin-inline-end:var(--space-md);
  border:1px solid var(--line-strong); border-radius:50%; background:var(--surface-raised);
  transition:transform var(--dur-micro) var(--ease-in-out); }
.switch.on::before { border-color:var(--ok); background:var(--ok-soft); }
.switch.on i { border-color:var(--ok); background:var(--ok); transform:translateX(0.95rem); }
.switch.static { cursor:help; opacity:0.6; }
.switch:disabled, .btn:disabled { cursor:not-allowed; opacity:0.5; }
.btn { min-height:2.75rem; padding-inline:var(--space-sm); border:1px solid var(--line-strong);
  border-radius:var(--radius-sm); color:var(--ink); background:var(--surface);
  cursor:pointer; white-space:nowrap; font-size:var(--text-sm); font-weight:650;
  transition:transform var(--dur-micro) var(--ease-out); }
.btn.primary { border-color:var(--accent); color:var(--accent); background:var(--accent-soft); }
.btn.static { display:inline-flex; align-items:center; cursor:help; opacity:0.6; }
.btn:active { transform:translateY(1px); }
.rec { display:flex; gap:var(--space-sm); align-items:flex-start; margin-bottom:var(--space-sm);
  padding:var(--space-md); border:1px solid var(--line); border-radius:var(--radius-md);
  background:var(--surface); box-shadow:var(--shadow); }
.rec:last-child { margin-bottom:0; }
.rec .sev { width:0.55rem; height:0.55rem; margin-top:var(--space-2xs); border-radius:50%;
  background:var(--muted); flex:none; }
.rec.high .sev { background:var(--bad); }
.rec.medium .sev { background:var(--warn); }
.rec.low .sev { background:var(--info); }
.rec.info .sev { background:var(--line-strong); }
.rec .body { flex:1; min-width:0; }
.rec .title { font-size:var(--text-sm); font-weight:700; }
.rec .detail { margin-top:var(--space-2xs); max-width:70ch; color:var(--muted); font-size:var(--text-sm); }
.rec .act { display:flex; flex:none; gap:var(--space-xs); align-items:center; flex-wrap:wrap; }
.saving { color:var(--accent); white-space:nowrap; font:var(--text-xs)/1.4 var(--font-mono); }
.profiles { display:flex; gap:var(--space-xs); flex-wrap:wrap; align-items:center; }
.hbar { display:grid; grid-template-columns:minmax(0,1fr) auto; gap:var(--space-2xs) var(--space-sm);
  align-items:center; padding:var(--space-xs) 0; }
.hbar .track { grid-column:1/-1; height:0.55rem; overflow:hidden;
  border-radius:var(--radius-pill); background:var(--accent-soft); }
.hbar .track span { display:block; height:100%; border-radius:inherit; background:var(--accent); }
.hbar .lbl { overflow:hidden; text-overflow:ellipsis; white-space:nowrap; font-size:var(--text-sm); }
svg[role="img"] { width:100%; height:auto; display:block; }
.grid { stroke:var(--line); stroke-width:1; }
.axis { fill:var(--muted); font:0.65rem var(--font-mono); }
.endlabel { fill:var(--accent); font:600 0.7rem var(--font-mono); }
.chart-area { fill:var(--accent); opacity:0.1; }
.chart-line { fill:none; stroke:var(--accent); stroke-width:2; stroke-linejoin:round; stroke-linecap:round; }
.dot { fill:var(--accent); }
.dot.end { stroke:var(--surface); stroke-width:1.5; }
.chart-empty, .emptymsg { color:var(--muted); font-size:var(--text-sm); }
.emptymsg { display:block; padding:var(--space-md); }
.chart-empty code, .emptymsg code, footer code { font:var(--text-xs)/1.4 var(--font-mono); }
.method-note { border-block:1px solid var(--line); padding-block:var(--space-md); }
.method-note summary { min-height:2.75rem; display:flex; align-items:center; cursor:pointer;
  color:var(--ink); font-weight:650; }
.method-note p { max-width:78ch; margin:var(--space-sm) 0 0; color:var(--muted); }
footer { display:flex; flex-direction:column; gap:var(--space-sm); color:var(--muted);
  font-size:var(--text-xs); line-height:1.6; }
.footline { display:flex; gap:var(--space-xs) var(--space-md); justify-content:space-between; flex-wrap:wrap; }
[hidden] { display:none !important; }
@media (hover:hover) and (pointer:fine) {
  .tabs button:hover, .theme-toggle:hover { color:var(--ink); background:var(--off-soft); }
  .search input:hover { background:var(--surface-raised); }
  .btn:hover { color:var(--accent); border-color:var(--accent); }
  .method-note summary:hover { color:var(--accent); }
  tbody tr:hover { border-color:var(--line-strong); }
}
.tabs button:active, .theme-toggle:active, .method-note summary:active { transform:translateY(1px); }
.tabs button:disabled, .theme-toggle:disabled { cursor:not-allowed; opacity:0.5; }
@media (min-width:40rem) {
  body { padding-block-start:var(--space-xl); padding-inline:max(var(--space-lg),env(safe-area-inset-left)); }
  header { grid-template-columns:minmax(0,1fr) auto; }
  .header-actions { justify-content:flex-end; flex-wrap:nowrap; }
  .tabs { order:1; width:auto; }
  .tabs button { flex:none; }
  .theme-toggle { order:2; }
  .tiles { grid-template-columns:repeat(4,minmax(0,1fr)); }
  .rec { align-items:center; }
  .hbar { grid-template-columns:9.5rem minmax(0,1fr) 4.5rem; gap:var(--space-sm); }
  .hbar .track { grid-column:auto; }
}
@media (min-width:60rem) {
  .tiles { grid-template-columns:repeat(8,minmax(0,1fr)); }
  .tile { grid-column:span 1; }
  #view-mcp > .tiles .tile:nth-child(3),
  #view-mcp > .tiles .tile:nth-child(4),
  #view-advisor > .tiles .tile,
  #view-skills > .tiles .tile { grid-column:span 2; }
  .tablewrap { overflow-x:auto; background:var(--surface); border:1px solid var(--line);
    border-radius:var(--radius-md); box-shadow:var(--shadow); }
  table { display:table; min-width:52rem; }
  thead { position:static; display:table-header-group; width:auto; height:auto;
    overflow:visible; clip-path:none; }
  tbody { display:table-row-group; }
  tr { display:table-row; padding:0; border:0; border-radius:0; box-shadow:none; background:transparent; }
  th, td { display:table-cell; text-align:start; vertical-align:middle; }
  th { padding:var(--space-sm) var(--space-md); border-bottom:1px solid var(--line);
    color:var(--muted); font-size:var(--text-xs); font-weight:650;
    letter-spacing:0.06em; text-transform:uppercase; }
  td { padding:var(--space-sm) var(--space-md); border-bottom:1px solid var(--line); font-size:var(--text-sm); }
  td::before { content:none; }
  tr:last-child td { border-bottom:0; }
  td.desc { max-width:28rem; }
  .cmd { max-width:20rem; }
  .ramcell { min-width:7.5rem; }
  .usecell { min-width:6.5rem; }
  .tablewrap .rec { margin:0; border:0; border-bottom:1px solid var(--line);
    border-radius:0; box-shadow:none; }
  .tablewrap .rec:last-child { border-bottom:0; }
}
@media (prefers-reduced-motion:reduce) {
  *, *::before, *::after { animation-duration:150ms !important;
    animation-iteration-count:1 !important; transition-duration:150ms !important; }
}
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
                    f'data-name="{esc(s["name"])}" '
                    f'role="switch" aria-checked="{"true" if state == "on" else "false"}" '
                    f'aria-label="Toggle {esc(s["name"])}"><i></i></button>')
        return (f'<span class="switch {state} static" title="Toggles work in live '
                f'mode: mcp-dashboard open"><i></i></span>')

    def prov_chip(s):
        cls, label = PROV_META.get(s.get("provenance", "unknown"),
                                   ("prov", s.get("provenance", "")))
        return f'<span class="{cls}">{esc(label)}</span>'

    def name_cell(s):
        return (f'<td class="name" data-label="Server">{esc(s["name"])} {prov_chip(s)}'
                f'<div class="chiprow"><span class="chip">{esc(s["agent"])}</span>'
                f'<span class="chip">{esc(s["scope"])}</span>'
                f'<span class="chip">{esc(s["transport"])}</span></div>'
                f'<div class="cmd">{esc(s["command"])}</div></td>')

    def status_cell(s):
        st = "disabled" if not s.get("enabled", True) else s.get("status", "unknown")
        cls, label = STATUS_META.get(st, STATUS_META["unknown"])
        v = s.get("verdict") or "quiet"
        return (f'<td data-label="Status"><span class="pill {cls}"><i></i>{label}</span>'
                f'<div><span class="verdict v-{v}">{VERDICT_TEXT.get(v, v)}</span></div></td>')

    def use_cell(s):
        c30, last = s.get("calls_30d", 0), s.get("last_used")
        sub = (f'<div class="sub2">last {last[:10]}</div>' if last
               else '<div class="sub2">never</div>')
        attribution = s.get("usage_attribution")
        if attribution in ("ambiguous", "unattributed"):
            sub += f'<div class="sub2">{esc(attribution)} attribution</div>'
        return (f'<td class="usecell" data-label="Calls 30d">'
                f'<span class="num">{c30}</span>{sub}</td>')

    def ctx_cell(s):
        tok, tools = s.get("ctx_tokens", 0), s.get("tools_count", 0)
        if s.get("probe_stale"):
            return ('<td data-label="Context"><span class="num">—</span>'
                    '<div class="sub2">probe stale</div></td>')
        if not tok:
            return ('<td data-label="Context"><span class="num">—</span>'
                    '<div class="sub2">not probed</div></td>')
        return (f'<td data-label="Context"><span class="num">{fmt_tokens(tok)}</span>'
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
        process_note = ('<div class="sub2">estimated</div>'
                        if s.get("process_attribution") == "shared-estimate" else "")
        dis = "" if s.get("enabled", True) else ' class="disabledrow"'
        search = " ".join(str(s.get(k, "")) for k in
                          ("name", "agent", "scope", "transport", "command", "verdict"))
        return (f'<tr{dis} data-filter-row="servers" data-search="{esc(search)}">'
                f'{name_cell(s)}{status_cell(s)}{use_cell(s)}{ctx_cell(s)}'
                f'<td class="num" data-label="Processes">'
                f'{f"{inst}&times;" if inst else "&mdash;"}{process_note}</td>'
                f'<td class="ramcell" data-label="CPU">{cpucell}</td>'
                f'<td class="ramcell" data-label="RAM">{bar}<span class="num">'
                f'{fmt_mb(ram) if ram else "&mdash;"}</span>'
                f'{svg_sparkline(hist_by_key.get(s["key"], []))}</td>'
                f'<td data-label="Enabled">{toggle(s)}</td></tr>')

    def remote_row(s):
        dis = "" if s.get("enabled", True) else ' class="disabledrow"'
        search = " ".join(str(s.get(k, "")) for k in
                          ("name", "agent", "scope", "transport", "command", "verdict"))
        return (f'<tr{dis} data-filter-row="servers" data-search="{esc(search)}">'
                f'{name_cell(s)}{status_cell(s)}{use_cell(s)}{ctx_cell(s)}'
                f'<td data-label="Enabled">{toggle(s)}</td></tr>')

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
                  if r["saving_bytes"] and r["action"] == "disable" else "")
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
    undo_html = (('<section><h2>Recovery <span class="hint">— restore the files '
                  'from the most recent successful dashboard change</span></h2>'
                  '<div class="card"><button class="btn" data-restore-last>'
                  'Undo last config change</button></div></section>') if live else "")

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
        search = " ".join((sk.get("name", ""), sk.get("source", ""), desc))
        return (f'<tr data-filter-row="skills" data-search="{esc(search)}">'
                f'<td class="name" data-label="Skill">{esc(sk["name"])}'
                f'<div class="chiprow">{chips}</div></td>'
                f'<td data-label="Calls 30d"><span class="num">{sk.get("calls_30d", 0)}</span>'
                f'<div class="sub2">{("last " + last[:10]) if last else "never"}</div></td>'
                f'<td class="desc" data-label="Description">'
                f'{esc(desc[:200] + ("…" if len(desc) > 200 else "")) or "—"}</td></tr>')

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

    nonce_attr = f' nonce="{esc(token)}"' if token else ""
    live_js = """
<script__NONCE__>
var statusRegion = document.getElementById('status-message');
function announce(message) {
  statusRegion.textContent = message || '';
}
function post(url, body, btn) {
  announce('');
  btn.disabled = true;
  btn.setAttribute('aria-busy', 'true');
  fetch(url, {method:'POST', headers:{'Content-Type':'application/json'},
    body: JSON.stringify(body)}).then(r => r.json()).then(j => {
      if (!j.ok) throw new Error(j.message || 'Request failed');
      location.reload();
    }).catch(e => {
      announce('Could not apply that change: ' + e.message);
      btn.disabled = false;
      btn.removeAttribute('aria-busy');
    });
}
document.querySelectorAll('button.switch').forEach(function (btn) {
  btn.addEventListener('click', function () {
    var action = btn.getAttribute('aria-checked') === 'true' ? 'switch off' : 'switch on';
    if (!confirm('Confirm: ' + action + ' "' + btn.dataset.name + '"? '
                 + 'A local recovery point will be created.')) return;
    post('/api/toggle', {key: btn.dataset.key}, btn);
  });
});
document.querySelectorAll('button[data-act="off"]').forEach(function (btn) {
  btn.addEventListener('click', function () {
    if (!confirm('Confirm: switch off this server? A local recovery point will be created.')) return;
    post('/api/set', {key: btn.dataset.key, enabled: false}, btn);
  });
});
document.querySelectorAll('button[data-profile]').forEach(function (btn) {
  btn.addEventListener('click', function () {
    if (!confirm('Apply profile "' + btn.dataset.profile + '"? Servers not in it '
                 + 'will be switched off.')) return;
    post('/api/profile', {name: btn.dataset.profile}, btn);
  });
});
document.querySelectorAll('button[data-restore-last]').forEach(function (btn) {
  btn.addEventListener('click', function () {
    if (!confirm('Restore the files from the most recent MCP Dashboard config change? '
                 + 'Current files will be backed up first.')) return;
    post('/api/restore', {}, btn);
  });
});
</script>""".replace("__NONCE__", nonce_attr)

    cpu_note = ("a live sample" if meta.get("psutil")
                else "the process-lifetime average (install psutil for live sampling)")
    probe_note = (f"probed {meta.get('probe_at', '')[:16].replace('T', ' ')}"
                  if meta.get("probe_at") else
                  "run with <code>--probe</code> to measure context cost and startup time")
    usage_note = ("Usage collection is disabled for this run"
                  if meta.get("usage_disabled") else
                  "Usage comes from your Claude Code and Codex transcripts")

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="referrer" content="no-referrer">
<meta name="color-scheme" content="light dark">
<title>MCP Server Dashboard</title>
<style>{CSS}</style>
</head>
<body>
<main>
  <header>
    <div class="brandline">
      <div class="brandmark" aria-hidden="true">MCP</div>
      <div>
        <h1>MCP Server Dashboard</h1>
        <div class="sub">v{esc(meta.get('version', 'dev'))} &middot; scanned {esc(meta['when'])} &middot; host {esc(meta['host'])}{' &middot; LIVE' if live else ''}{' &middot; DEMO DATA' if meta.get('demo') else ''}</div>
      </div>
    </div>
    <div class="header-actions">
      <nav class="tabs" role="tablist" aria-label="Dashboard views">
        <button id="tab-mcp" role="tab" aria-selected="true" aria-controls="view-mcp" data-tab="mcp">Servers</button>
        <button id="tab-advisor" role="tab" aria-selected="false" aria-controls="view-advisor" data-tab="advisor">Advisor{f' ({high})' if high else ''}</button>
        <button id="tab-skills" role="tab" aria-selected="false" aria-controls="view-skills" data-tab="skills">Skills</button>
      </nav>
      <button class="theme-toggle" type="button" aria-label="Theme: automatic">Theme: Auto</button>
    </div>
  </header>
  <div id="status-message" class="status-message" role="status" aria-live="polite"></div>

  <div id="view-mcp" role="tabpanel" aria-labelledby="tab-mcp" tabindex="0">
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

  <div class="toolbar">
    <label class="search"><span>Filter servers</span>
      <input type="search" data-filter="servers" placeholder="Name, agent, scope, verdict" autocomplete="off">
    </label>
    <div class="filter-summary" data-filter-summary="servers" aria-live="polite"></div>
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

  <div id="view-advisor" role="tabpanel" aria-labelledby="tab-advisor" tabindex="0" hidden>
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
  {undo_html}

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

  <div id="view-skills" role="tabpanel" aria-labelledby="tab-skills" tabindex="0" hidden>
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
  <div class="toolbar">
    <label class="search"><span>Filter skills</span>
      <input type="search" data-filter="skills" placeholder="Name, source, description" autocomplete="off">
    </label>
    <div class="filter-summary" data-filter-summary="skills" aria-live="polite"></div>
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
    <details class="method-note">
      <summary>How this dashboard measures cost</summary>
      <p>Each <strong>stdio</strong> server is a real OS process spawned per agent
      session &mdash; three open sessions run every stdio server three times.
      Context cost is the tool schemas a server injects into every request;
      {probe_note}. CPU is {cpu_note}. {usage_note}. Provenance:
      <span class="prov-self">yours</span> means a server you built. Switching a
      server off stashes its config; running sessions keep their processes until
      restarted.</p>
    </details>
    <div class="footline"><span>Local-first &middot; dependency-free &middot; MIT licensed</span>
      <span>Regenerate: <code>mcp-dashboard --open</code> &middot;
      live control: <code>mcp-dashboard open</code></span></div>
  </footer>
</main>
<script{nonce_attr}>
var tabButtons = Array.from(document.querySelectorAll('.tabs button'));
function activateTab(btn, moveFocus) {{
  tabButtons.forEach(function (candidate) {{
    var active = candidate === btn;
    candidate.setAttribute('aria-selected', active ? 'true' : 'false');
    candidate.tabIndex = active ? 0 : -1;
    document.getElementById(candidate.getAttribute('aria-controls')).hidden = !active;
  }});
  history.replaceState(null, '', '#' + btn.dataset.tab);
  if (moveFocus) btn.focus({{preventScroll:true}});
}}
tabButtons.forEach(function (btn, index) {{
  btn.addEventListener('click', function () {{ activateTab(btn, false); }});
  btn.addEventListener('keydown', function (event) {{
    var next = null;
    if (event.key === 'ArrowRight') next = (index + 1) % tabButtons.length;
    if (event.key === 'ArrowLeft') next = (index - 1 + tabButtons.length) % tabButtons.length;
    if (event.key === 'Home') next = 0;
    if (event.key === 'End') next = tabButtons.length - 1;
    if (next !== null) {{ event.preventDefault(); activateTab(tabButtons[next], true); }}
  }});
}});
var initialTab = tabButtons.find(function (btn) {{ return '#' + btn.dataset.tab === location.hash; }});
activateTab(initialTab || tabButtons[0], false);

var themeButton = document.querySelector('.theme-toggle');
var themes = ['auto', 'light', 'dark'];
function setTheme(mode) {{
  if (mode === 'auto') document.documentElement.removeAttribute('data-theme');
  else document.documentElement.setAttribute('data-theme', mode);
  themeButton.textContent = 'Theme: ' + mode.charAt(0).toUpperCase() + mode.slice(1);
  themeButton.setAttribute('aria-label', 'Theme: ' + (mode === 'auto' ? 'automatic' : mode));
  try {{ localStorage.setItem('mcp-dashboard-theme', mode); }} catch (e) {{}}
}}
var savedTheme = 'auto';
try {{ savedTheme = localStorage.getItem('mcp-dashboard-theme') || 'auto'; }} catch (e) {{}}
if (!themes.includes(savedTheme)) savedTheme = 'auto';
setTheme(savedTheme);
themeButton.addEventListener('click', function () {{
  var current = document.documentElement.getAttribute('data-theme') || 'auto';
  setTheme(themes[(themes.indexOf(current) + 1) % themes.length]);
}});

document.querySelectorAll('[data-filter]').forEach(function (input) {{
  var kind = input.dataset.filter;
  var rows = Array.from(document.querySelectorAll('[data-filter-row="' + kind + '"]'));
  var summary = document.querySelector('[data-filter-summary="' + kind + '"]');
  function filterRows() {{
    var query = input.value.trim().toLocaleLowerCase();
    var visible = 0;
    rows.forEach(function (row) {{
      var match = !query || (row.dataset.search || '').toLocaleLowerCase().includes(query);
      row.hidden = !match;
      if (match) visible += 1;
    }});
    summary.textContent = query ? 'Showing ' + visible + ' of ' + rows.length : rows.length + ' total';
  }}
  input.addEventListener('input', filterRows);
  filterRows();
}});
</script>
{live_js if live else ''}
</body>
</html>
"""
