"""End-to-end test of the shipped example: run agent.py and check its artifacts.

This is the most expensive test (a full agent run: several Kimi K3 calls plus two
web_fetch summarizations via Claude Haiku, ~2-3 minutes and a few cents of tokens).
It is marked `slow` so it can be deselected with `-m "not slow"`.

It runs agent.py in an isolated temp directory with its own session and a copy of the
source files it reads, so it never disturbs the repo's own ./.agent session or an
existing REVIEW.md. It asserts the run exits cleanly, produces REVIEW.md, and uses the
web_fetch tool -- and that the run log is free of the model-card InternalServerException.
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.slow
def test_agent_py_runs_and_writes_review(bedrock, tmp_path):
    # Copy the files agent.py reads/needs into an isolated working dir.
    for name in ("agent.py", "README.md", "requirements.txt"):
        shutil.copy(REPO_ROOT / name, tmp_path / name)

    # Use a throwaway session id so we don't touch the demo session.
    agent_src = (tmp_path / "agent.py").read_text()
    agent_src = agent_src.replace('"id": "kimi-k3-demo"', '"id": "e2e-test-session"')
    (tmp_path / "agent.py").write_text(agent_src)

    env = dict(os.environ)
    env.setdefault("AWS_REGION", "us-east-1")

    proc = subprocess.run(
        [sys.executable, "agent.py"],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        timeout=600,
    )
    log = proc.stdout + proc.stderr

    assert proc.returncode == 0, f"agent.py exited {proc.returncode}\n{log}"
    # A raised exception shows up as a Python traceback, not as the agent writing the
    # word "InternalServerException" into its REVIEW.md prose -- match the traceback.
    assert "Traceback (most recent call last)" not in log, f"agent.py raised:\n{log}"
    assert "botocore.errorfactory.InternalServerException" not in log, (
        f"Converse raised InternalServerException:\n{log}"
    )

    review = tmp_path / "REVIEW.md"
    assert review.exists(), "agent.py did not write REVIEW.md"
    assert review.stat().st_size > 500, "REVIEW.md is suspiciously small"

    # The task requires fetching the model card; confirm the tool was exercised.
    assert "web_fetch" in log, "expected web_fetch to be used during the run"
