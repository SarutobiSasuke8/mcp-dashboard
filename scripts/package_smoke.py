"""Build-artifact smoke test used by CI and the release checklist."""

import os
import subprocess
import tempfile
import venv
from pathlib import Path


def run(command, env=None):
    print("+", " ".join(map(str, command)))
    subprocess.run(command, check=True, env=env)


def main():
    wheels = sorted(Path("dist").glob("mcp_dashboard-*.whl"))
    if len(wheels) != 1:
        raise SystemExit(f"expected exactly one wheel in dist/, found {len(wheels)}")
    wheel = wheels[0].resolve()
    with tempfile.TemporaryDirectory(prefix="mcp-dashboard-smoke-") as td:
        root = Path(td)
        environment = root / "venv"
        venv.EnvBuilder(with_pip=True, clear=True).create(environment)
        scripts = environment / ("Scripts" if os.name == "nt" else "bin")
        python = scripts / ("python.exe" if os.name == "nt" else "python")
        command = scripts / ("mcp-dashboard.exe" if os.name == "nt" else "mcp-dashboard")
        run([python, "-m", "pip", "install", "--no-index", "--no-deps", wheel])
        smoke_env = {**os.environ, "MCP_DASHBOARD_HOME": str(root / "home")}
        run([command, "--version"], smoke_env)
        run([command, "--doctor", "--port", "0"], smoke_env)
        html = root / "dashboard.html"
        note = root / "directory.md"
        run([command, "--demo", "--html", html, "--note", note,
             "--no-usage"], smoke_env)
        if not html.is_file() or "MCP Server Dashboard" not in html.read_text(
                encoding="utf-8"):
            raise SystemExit("installed CLI did not generate a valid dashboard")
    print("Package smoke test passed.")


if __name__ == "__main__":
    main()
