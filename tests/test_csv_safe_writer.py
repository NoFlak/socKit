import os
from pathlib import Path

from utils.csv_safe_writer import promote_shallow_copy, write_csv_rows_atomic


def test_write_csv_rows_atomic_success(tmp_path):
    target = tmp_path / "log.csv"
    result = write_csv_rows_atomic(target, [["alpha", "beta"]], header=["col1", "col2"])

    assert result == target
    content = target.read_text(encoding="utf-8").splitlines()
    assert content[0] == "col1,col2"
    assert content[1] == "alpha,beta"


def test_write_csv_rows_atomic_permission_fallback(monkeypatch, tmp_path):
    target = tmp_path / "ToolkitLog.csv"
    original_replace = os.replace

    def fake_replace(src, dst):
        if Path(dst) == target:
            raise PermissionError("locked")
        return original_replace(src, dst)

    monkeypatch.setattr("utils.csv_safe_writer.os.replace", fake_replace)
    monkeypatch.setattr("utils.csv_safe_writer.time.sleep", lambda _: None)
    monkeypatch.setattr("utils.csv_safe_writer.time.monotonic", lambda: 0.0)

    result = write_csv_rows_atomic(target, [["value"]], header=["message"], max_retry_seconds=0.0)
    assert result != target
    assert "shallow" in result.name
    assert result.exists()


def test_promote_shallow_copy(tmp_path):
    canonical = tmp_path / "ToolkitLog.csv"
    shallow = tmp_path / "ToolkitLog_shallow.csv"
    shallow.write_text("data", encoding="utf-8")

    success = promote_shallow_copy(shallow, canonical)
    assert success is True
    assert canonical.exists()
    assert not shallow.exists()
