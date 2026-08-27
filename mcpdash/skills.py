"""Skill discovery across every place Claude Code loads skills from.

Roots are scanned in precedence order (vault/project first, then user,
synced, and plugins) so a name defined twice can be reported as shadowed.
"""

import os
import re
from pathlib import Path

from .common import VAULT_ROOT, load_json


def parse_skill_md(path):
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    name = desc = None
    m = re.match(r"^---\s*\n(.*?)\n---", text, re.S)
    if m:
        fm = m.group(1)
        nm = re.search(r"^name:\s*(.+)$", fm, re.M)
        dm = re.search(r"^description:\s*(.+?)(?=\n[\w-]+:|\Z)", fm, re.M | re.S)
        if nm:
            name = nm.group(1).strip().strip("\"'")
        if dm:
            desc = " ".join(dm.group(1).split()).strip().strip("\"'")
    return {"name": name or path.parent.name, "description": desc or "",
            "path": str(path), "size": len(text)}


def discover_skills():
    skills, seen_paths = [], set()

    def scan_root(root, source):
        """Roots are scanned in precedence order; a file already claimed by
        an earlier root is not re-listed. Without this, `~/.claude/skills`
        and its own `synced/` subfolder both claim the same SKILL.md and
        every synced skill looks like a name collision with itself."""
        root = Path(root)
        if not root.is_dir():
            return
        for md in sorted(root.glob("*/SKILL.md")) + sorted(root.glob("*/*/SKILL.md")):
            resolved = md.resolve()
            if resolved in seen_paths:
                continue
            info = parse_skill_md(md)
            if not info:
                continue
            seen_paths.add(resolved)
            info["source"] = source
            skills.append(info)

    # Project-local skills have precedence over user and plugin copies. Scan
    # the conventions used by both Claude Code and Codex-compatible agents.
    for rel, source in ((Path(".agents/skills"), "vault:agents"),
                        (Path(".codex/skills"), "vault:codex"),
                        (Path(".claude/skills"), "vault:claude")):
        scan_root(VAULT_ROOT / rel, source)
    cwd = Path(os.getcwd())
    if cwd != VAULT_ROOT:
        for rel, source in ((Path(".agents/skills"), "project:agents"),
                            (Path(".codex/skills"), "project:codex"),
                            (Path(".claude/skills"), "project:claude")):
            scan_root(cwd / rel, source)
    scan_root(Path.home() / ".claude" / "skills" / "synced", "synced")
    scan_root(Path.home() / ".agents" / "skills", "user:agents")
    scan_root(Path.home() / ".codex" / "skills", "user:codex")
    scan_root(Path.home() / ".claude" / "skills", "user:claude")
    plugins_root = Path.home() / ".claude" / "plugins"
    if plugins_root.is_dir():
        for plugdir in sorted(p for p in plugins_root.iterdir() if p.is_dir()):
            scan_root(plugdir / "skills", f"plugin:{plugdir.name}")

    codex_home = Path(os.environ.get("CODEX_HOME", Path.home() / ".codex"))
    scan_root(codex_home / "skills", "user:codex-home")
    codex_plugins = codex_home / "plugins"
    if codex_plugins.is_dir():
        # Plugin caches nest skill roots at varying depths. ``seen_paths``
        # keeps overlapping roots from reporting the same skill twice.
        for skill_root in sorted(p for p in codex_plugins.rglob("skills")
                                 if p.is_dir()):
            package = skill_root.parent.name or "codex"
            scan_root(skill_root, f"plugin:{package}")

    lock = load_json(VAULT_ROOT / "skills-lock.json") or \
        load_json(Path(os.getcwd()) / "skills-lock.json") or {}
    locked = lock.get("skills") or {}
    for s in skills:
        entry = locked.get(s["name"]) or {}
        s["locked"] = s["name"] in locked
        s["lock_source"] = entry.get("source", "")
    return skills
