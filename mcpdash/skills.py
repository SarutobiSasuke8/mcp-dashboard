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

    scan_root(VAULT_ROOT / ".claude" / "skills", "vault")
    cwd = Path(os.getcwd())
    if cwd != VAULT_ROOT:
        scan_root(cwd / ".claude" / "skills", "project")
    scan_root(Path.home() / ".claude" / "skills" / "synced", "synced")
    scan_root(Path.home() / ".claude" / "skills", "user")
    plugins_root = Path.home() / ".claude" / "plugins"
    if plugins_root.is_dir():
        for plugdir in sorted(p for p in plugins_root.iterdir() if p.is_dir()):
            scan_root(plugdir / "skills", f"plugin:{plugdir.name}")

    lock = load_json(VAULT_ROOT / "skills-lock.json") or \
        load_json(Path(os.getcwd()) / "skills-lock.json") or {}
    locked = lock.get("skills") or {}
    for s in skills:
        entry = locked.get(s["name"]) or {}
        s["locked"] = s["name"] in locked
        s["lock_source"] = entry.get("source", "")
    return skills
