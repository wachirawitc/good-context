#!/usr/bin/env python3
"""Materialize the acme-orders fixture into a throwaway sandbox for good-context evals.

Usage:
    python setup_sandbox.py DEST_DIR      -> creates DEST_DIR/acme-orders and prints its path

Why this exists instead of using the fixture in place:
- The deliberately flawed agent-instruction files are stored as *.sample so that no agent
  tool auto-loads them while someone works on this repository. They get their real names
  (CLAUDE.md, AGENTS.md) only inside the sandbox.
- The fake GitLab token is assembled at runtime, so no secret-shaped string is committed
  (secret push protection would block it, and it would be a bad habit to model).
- The sandbox is a git repo whose instruction files were committed long before the code
  changed, so the freshness / drift checks have something real to find.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__)
        return 2
    dest = Path(sys.argv[1]).resolve() / "acme-orders"
    src = Path(__file__).resolve().parent / "files" / "acme-orders"
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(src, dest)

    fake_token = "glpat" + "-" + "Zq7fakeTOKENfixture9xQ"
    for sample in list(dest.rglob("*.sample")):
        real = sample.with_name(sample.name[: -len(".sample")])
        text = sample.read_text(encoding="utf-8").replace("__FAKE_GITLAB_TOKEN__", fake_token)
        real.write_text(text, encoding="utf-8", newline="\n")
        sample.unlink()

    base_env = dict(os.environ, GIT_AUTHOR_NAME="Fixture", GIT_AUTHOR_EMAIL="fixture@example.com",
                    GIT_COMMITTER_NAME="Fixture", GIT_COMMITTER_EMAIL="fixture@example.com")

    def git(*args: str, date: str | None = None) -> None:
        env = dict(base_env)
        if date:
            env["GIT_AUTHOR_DATE"] = env["GIT_COMMITTER_DATE"] = date
        subprocess.run(["git", "-C", str(dest), *args], check=True, env=env,
                       capture_output=True, text=True)

    git("init", "-q", "-b", "main")
    git("add", "CLAUDE.md", "README.md", "docs", "services/worker/AGENTS.md")
    git("commit", "-q", "-m", "docs: agent instructions", date="2025-01-15T10:00:00")
    git("add", "-A")
    git("commit", "-q", "-m", "feat: fastify api, worker, gitlab ci", date="2026-10-01T10:00:00")
    print(dest)
    return 0


if __name__ == "__main__":
    sys.exit(main())
