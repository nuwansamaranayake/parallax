"""Script-level guards: the Standard-4 migration check must never skip silently."""
import os
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent


def test_check_migrations_refuses_to_skip_when_expected_count_unset():
    """An unset EXPECTED_TABLE_COUNT used to turn the table-count assertion into a silent
    no-op that still printed MIGRATION OK. It must fail loudly instead."""
    env = {k: v for k, v in os.environ.items() if k != "EXPECTED_TABLE_COUNT"}
    r = subprocess.run(
        [sys.executable, "scripts/check_migrations.py"],
        cwd=str(REPO), env=env, capture_output=True, text=True, timeout=30)
    assert r.returncode == 1
    assert "EXPECTED_TABLE_COUNT" in r.stderr
    assert "refusing to skip" in r.stderr
    assert "MIGRATION OK" not in r.stdout
