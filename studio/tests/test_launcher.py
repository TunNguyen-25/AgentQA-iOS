import subprocess
from pathlib import Path

LAUNCHER = Path(__file__).resolve().parents[2] / "bin" / "agentqa-studio"
REPO_ROOT = LAUNCHER.parents[1]


def test_launcher_prints_resolved_repo(tmp_path):
    (tmp_path / ".agentqa").mkdir()
    (tmp_path / ".agentqa" / "config.yml").write_text("platform: ios\n")
    out = subprocess.run(
        [str(LAUNCHER), "--dry-run"], cwd=tmp_path,
        capture_output=True, text=True,
    )
    assert out.returncode == 0, out.stderr
    assert "studio.server" in out.stdout
    assert str(tmp_path) in out.stdout


def test_launcher_resolves_git_toplevel(tmp_path):
    subprocess.run(["git", "init"], cwd=tmp_path, capture_output=True)
    (tmp_path / ".agentqa").mkdir()
    (tmp_path / ".agentqa" / "config.yml").write_text("platform: ios\n")
    top = subprocess.run(
        ["git", "-C", str(tmp_path), "rev-parse", "--show-toplevel"],
        capture_output=True, text=True,
    ).stdout.strip()
    out = subprocess.run(
        [str(LAUNCHER), "--dry-run"], cwd=tmp_path,
        capture_output=True, text=True,
    )
    assert out.returncode == 0, out.stderr
    assert top in out.stdout


def test_launcher_works_through_symlink(tmp_path):
    # Simulate the PATH install: a symlink pointing at the real launcher.
    bindir = tmp_path / "bin"
    bindir.mkdir()
    link = bindir / "agentqa-studio"
    link.symlink_to(LAUNCHER)
    work = tmp_path / "work"
    work.mkdir()
    out = subprocess.run(
        [str(link), "--dry-run"], cwd=work,
        capture_output=True, text=True,
    )
    assert out.returncode == 0, out.stderr
    # STUDIO_ROOT must resolve THROUGH the symlink to the real repo,
    # so `-m studio.server` can import the studio package.
    assert str(REPO_ROOT) in out.stdout
    assert str(bindir) not in out.stdout
