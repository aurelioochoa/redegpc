#!/usr/bin/env python3
"""Repository checks; no IPA or graphical desktop is needed."""
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
ENV = dict(os.environ)
ENV.setdefault("CARGO_BUILD_JOBS", "4")


def run(args, capture=False):
    print("+", " ".join(args), flush=True)
    result = subprocess.run(args, cwd=ROOT, env=ENV, text=True,
                            stdout=subprocess.PIPE if capture else None)
    if result.returncode:
        if capture:
            print(result.stdout)
        raise SystemExit(result.returncode)
    return result.stdout or ""


def focused_clippy():
    diagnostics = run(["cargo", "clippy", "--locked", "--lib", "--bins",
                       "--message-format=json"], capture=True)
    failures = []
    for line in diagnostics.splitlines():
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue
        if entry.get("reason") != "compiler-message":
            continue
        message = entry["message"]
        files = [span["file_name"] for span in message["spans"] if span["is_primary"]]
        focused = any(file.startswith(("src/redegpc", "src/window/movie.rs",
                                       "src/frameworks/media_player/movie_player"))
                      for file in files)
        if message["level"] == "error" or (focused and message["level"] == "warning"):
            failures.append(message["rendered"] or message["message"])
    if failures:
        print("\n".join(failures))
        raise SystemExit("Focused Clippy diagnostics must be resolved")
    print("FOCUSED_CLIPPY_PASSED", flush=True)


if __name__ == "__main__":
    if len(sys.argv) == 2 and sys.argv[1] == "--clippy":
        focused_clippy()
    else:
        run(["cargo", "fmt", "--all", "--", "--check"])
        run(["cargo", "build", "--locked", "--release", "--bins"])
        focused_clippy()
        run(["cargo", "test", "--locked", "--lib", "--", "--test-threads=1"])
        run([sys.executable, "scripts/verify_cli.py"])
        print("REDEGPC_CHECKS_PASSED", flush=True)
