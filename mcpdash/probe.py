"""Process measurement (RAM/CPU) and optional MCP handshake probing.

Probing spawns a stdio server exactly as an agent would, completes the MCP
initialize handshake, and asks for its tool list. That yields three things
the process table cannot: how long the server takes to start, how many
tools it injects into every request (context-window cost), and the real
error output when a server fails.
"""

import json
import os
import platform
import queue
import subprocess
import threading
import time

from .common import PROBE_CACHE_PATH, load_json, run_cli, save_json

CHARS_PER_TOKEN = 4  # rough but consistent estimate for schema JSON


# ---------------------------------------------------------------------------
# Process table
# ---------------------------------------------------------------------------

def list_processes():
    """[{pid, ppid, rss, cpu, cmdline}]. psutil gives a real CPU sample;
    `ps` gives a lifetime average; Windows without psutil reports no CPU."""
    try:
        import psutil  # type: ignore
        procs = {}
        for p in psutil.process_iter(["pid", "ppid", "memory_info", "cmdline"]):
            try:
                i = p.info
                procs[i["pid"]] = {
                    "pid": i["pid"], "ppid": i["ppid"] or 0,
                    "rss": i["memory_info"].rss if i["memory_info"] else 0,
                    "cmdline": " ".join(i["cmdline"] or []), "cpu": 0.0, "_p": p}
                p.cpu_percent(None)
            except Exception:
                continue
        time.sleep(0.5)
        for d in procs.values():
            try:
                d["cpu"] = d.pop("_p").cpu_percent(None)
            except Exception:
                d.pop("_p", None)
                d["cpu"] = None
        return list(procs.values())
    except ImportError:
        pass

    if platform.system() == "Windows":
        ps_cmd = ("Get-CimInstance Win32_Process | Select-Object ProcessId,"
                  "ParentProcessId,WorkingSetSize,CommandLine | ConvertTo-Json -Compress")
        ok, out = run_cli(["powershell", "-NoProfile", "-Command", ps_cmd])
        try:
            data = json.loads(out.strip() or "[]")
            if isinstance(data, dict):
                data = [data]
            return [{"pid": d.get("ProcessId", 0), "ppid": d.get("ParentProcessId", 0),
                     "rss": d.get("WorkingSetSize") or 0, "cpu": None,
                     "cmdline": d.get("CommandLine") or ""} for d in data]
        except Exception:
            return []

    ok, out = run_cli(["ps", "-eo", "pid=,ppid=,rss=,pcpu=,args="], timeout=30)
    procs = []
    for line in out.splitlines():
        parts = line.split(None, 4)
        if len(parts) < 5:
            continue
        try:
            procs.append({"pid": int(parts[0]), "ppid": int(parts[1]),
                          "rss": int(parts[2]) * 1024, "cpu": float(parts[3]),
                          "cmdline": parts[4]})
        except ValueError:
            continue
    return procs


# Processes that may legitimately *be* an MCP server. Anything else whose
# command line merely mentions a server (a shell, an editor, a grep) must not
# be counted as one.
LAUNCHERS = {"node", "npx", "python", "python3", "py", "uv", "uvx", "deno",
             "bun", "docker", "podman", "ruby", "perl", "java", "dotnet",
             "go", "cargo", "php", "pwsh"}
NEVER = {"bash", "sh", "zsh", "fish", "dash", "cmd", "powershell", "grep",
         "rg", "sed", "awk", "cat", "less", "tail", "head", "vim", "nvim",
         "nano", "emacs", "code", "ps", "find", "fd", "git", "tee", "xargs"}


def _argv0(cmdline):
    """Basename of the executable in a command line, without extension."""
    text = cmdline.strip()
    if text.startswith('"'):
        end = text.find('"', 1)
        first = text[1:end] if end > 0 else text[1:]
    else:
        first = text.split()[0] if text.split() else ""
    base = os.path.basename(first.replace("\\", "/")).lower()
    for ext in (".exe", ".cmd", ".bat"):
        if base.endswith(ext):
            base = base[: -len(ext)]
    return base


def _ancestors(pid, by_pid):
    """Every parent of pid, so the shell that launched this scan is never
    mistaken for a server it happens to mention."""
    out, seen = set(), 0
    cur = by_pid.get(pid, {}).get("ppid", 0)
    while cur and cur not in out and seen < 40:
        out.add(cur)
        cur = by_pid.get(cur, {}).get("ppid", 0)
        seen += 1
    return out


def _plausible(proc, server):
    argv0 = _argv0(proc["cmdline"])
    if argv0 in NEVER:
        return False
    cmd = os.path.basename(str((server.get("raw") or {}).get("command", ""))).lower()
    for ext in (".exe", ".cmd", ".bat"):
        if cmd.endswith(ext):
            cmd = cmd[: -len(ext)]
    return argv0 in LAUNCHERS or (cmd and argv0 == cmd) or not argv0


def measure_usage(servers, procs):
    """Attach instances, RAM, and CPU to each running stdio server."""
    children = {}
    for p in procs:
        children.setdefault(p["ppid"], []).append(p)
    by_pid = {p["pid"]: p for p in procs}

    def descendants(pid):
        out, stack = [], [pid]
        while stack:
            for c in children.get(stack.pop(), []):
                out.append(c["pid"])
                stack.append(c["pid"])
        return out

    self_pid = os.getpid()
    skip = _ancestors(self_pid, by_pid) | {self_pid}
    for s in servers:
        s.setdefault("instances", 0)
        s.setdefault("ram_bytes", 0)
        s.setdefault("cpu_pct", None)
        token = s.get("token")
        if s["transport"] != "stdio" or not token or not s.get("enabled", True):
            continue
        tl = token.lower()
        matched = [p["pid"] for p in procs
                   if tl in p["cmdline"].lower() and p["pid"] not in skip
                   and _plausible(p, s)]
        if not matched:
            continue
        mset = set(matched)
        roots = [pid for pid in matched if by_pid.get(pid, {}).get("ppid") not in mset]
        counted = set(matched)
        for pid in matched:
            counted.update(descendants(pid))
        s["instances"] = len(roots) or len(matched)
        s["ram_bytes"] = sum(by_pid[p]["rss"] for p in counted if p in by_pid)
        cpus = [by_pid[p]["cpu"] for p in counted
                if p in by_pid and by_pid[p]["cpu"] is not None]
        s["cpu_pct"] = round(sum(cpus), 1) if cpus else None


# ---------------------------------------------------------------------------
# MCP handshake probe
# ---------------------------------------------------------------------------

def _reader(stream, q):
    try:
        for line in stream:
            q.put(line)
    except Exception:
        pass
    finally:
        q.put(None)


def probe_server(cfg, timeout=25):
    """Start a stdio MCP server, handshake, and list its tools.

    Returns {ok, tools, tokens, ms, error, tool_names}. The server process is
    always terminated before returning."""
    result = {"ok": False, "tools": 0, "tokens": 0, "ms": None,
              "error": "", "tool_names": []}
    command = cfg.get("command")
    if not command:
        result["error"] = "no command (remote server)"
        return result

    env = {**os.environ, **{k: str(v) for k, v in (cfg.get("env") or {}).items()}}
    argv = [str(command)] + [str(a) for a in cfg.get("args", [])]
    started = time.time()
    try:
        proc = subprocess.Popen(
            argv, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, text=True, encoding="utf-8",
            errors="replace", bufsize=1, env=env,
            cwd=cfg.get("cwd") or None,
            shell=(platform.system() == "Windows"))
    except OSError as exc:
        result["error"] = f"failed to start: {exc}"
        return result

    q = queue.Queue()
    threading.Thread(target=_reader, args=(proc.stdout, q), daemon=True).start()
    errbuf = []
    threading.Thread(target=lambda: errbuf.extend(proc.stderr or []),
                     daemon=True).start()

    def send(obj):
        try:
            proc.stdin.write(json.dumps(obj) + "\n")
            proc.stdin.flush()
        except Exception:
            pass

    def await_id(want, deadline):
        while time.time() < deadline:
            try:
                line = q.get(timeout=0.2)
            except queue.Empty:
                if proc.poll() is not None:
                    return None
                continue
            if line is None:
                return None
            line = line.strip()
            if not line.startswith("{"):
                continue
            try:
                msg = json.loads(line)
            except json.JSONDecodeError:
                continue
            if msg.get("id") == want:
                return msg
        return None

    try:
        deadline = time.time() + timeout
        send({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {
            "protocolVersion": "2024-11-05", "capabilities": {},
            "clientInfo": {"name": "mcp-dashboard", "version": "1.0"}}})
        init = await_id(1, deadline)
        if init is None:
            result["error"] = ("no response to initialize"
                               if proc.poll() is None else
                               f"exited with code {proc.poll()}")
            result["error"] += _tail(errbuf)
            return result
        if init.get("error"):
            result["error"] = str(init["error"])[:200]
            return result
        result["ms"] = int((time.time() - started) * 1000)

        send({"jsonrpc": "2.0", "method": "notifications/initialized"})
        send({"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}})
        tools_msg = await_id(2, time.time() + max(5, timeout / 2))
        tools = ((tools_msg or {}).get("result") or {}).get("tools") or []
        result["ok"] = True
        result["tools"] = len(tools)
        result["tokens"] = int(len(json.dumps(tools)) / CHARS_PER_TOKEN)
        result["tool_names"] = [t.get("name", "") for t in tools][:200]
        return result
    finally:
        try:
            proc.terminate()
            proc.wait(timeout=5)
        except Exception:
            try:
                proc.kill()
            except Exception:
                pass


def _tail(errbuf, n=400):
    text = "".join(errbuf).strip()
    return f" — stderr: {text[-n:]}" if text else ""


def probe_all(servers, timeout=25, only_stdio=True):
    """Probe every enabled stdio server, caching results by key."""
    cache = load_json(PROBE_CACHE_PATH) or {}
    for s in servers:
        if only_stdio and s["transport"] != "stdio":
            continue
        if not s.get("enabled", True):
            continue
        res = probe_server(s.get("raw") or {}, timeout=timeout)
        res["at"] = time.strftime("%Y-%m-%dT%H:%M:%S")
        cache[s["key"]] = res
    save_json(PROBE_CACHE_PATH, cache)
    return cache


def attach_probe(servers, cache=None):
    cache = cache if cache is not None else (load_json(PROBE_CACHE_PATH) or {})
    for s in servers:
        p = cache.get(s["key"]) or {}
        s["tools_count"] = p.get("tools") or 0
        s["ctx_tokens"] = p.get("tokens") or 0
        s["probe_ms"] = p.get("ms")
        s["probe_error"] = p.get("error", "")
        s["probe_at"] = p.get("at", "")
    return servers
