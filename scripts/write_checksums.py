"""Write deterministic SHA-256 entries for release artifacts."""

import hashlib
from pathlib import Path


def main():
    artifacts = sorted(path for path in Path("dist").iterdir()
                       if path.is_file() and path.name != "SHA256SUMS")
    if not artifacts:
        raise SystemExit("no release artifacts found in dist/")
    lines = []
    for path in artifacts:
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        lines.append(f"{digest}  {path.name}")
    output = Path("dist") / "SHA256SUMS"
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(output.read_text(encoding="utf-8"), end="")


if __name__ == "__main__":
    main()
