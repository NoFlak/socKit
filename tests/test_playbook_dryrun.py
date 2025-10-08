from pathlib import Path
import json
import time


def test_ephemeral_playbook_created(monkeypatch, tmp_path):
    # Create a tiny playbook and run the wrapper in dry-run
    pb = tmp_path / 'pb.yml'
    pb.write_text('name: x\nsteps:\n  - {task: system.overview}\n', encoding='utf-8')

    # Copy into repo-relative for the script
    repo_pb = Path('playbooks') / 'tmp_test_pb.yml'
    repo_pb.parent.mkdir(parents=True, exist_ok=True)
    repo_pb.write_text(pb.read_text(encoding='utf-8'), encoding='utf-8')

    import subprocess, sys
    proc = subprocess.run([
        sys.executable,
        'playbooks/run_playbook.py',
        str(repo_pb),
        '--operator', 'tester',
        '--dry-run'
    ], capture_output=True, text=True)
    assert proc.returncode == 0
    assert 'ephemeral' in proc.stdout

