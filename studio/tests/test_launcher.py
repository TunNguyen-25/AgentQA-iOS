import subprocess
from pathlib import Path

LAUNCHER = Path(__file__).resolve().parents[2] / "bin" / "agentqa-studio"


def test_launcher_prints_resolved_repo(tmp_path):
    (tmp_path / ".agentqa").mkdir()
    (tmp_path / ".agentqa" / "config.yml").write_text("platform: ios\n")
    # --dry-run resolves paths and prints the server command without starting it
    out = subprocess.run(
        [str(LAUNCHER), "--dry-run"], cwd=tmp_path,
        capture_output=True, text=True,
    )
    assert out.returncode == 0, out.stderr
    assert "server.py" in out.stdout
    assert str(tmp_path) in out.stdout
