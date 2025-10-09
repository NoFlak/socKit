from __future__ import annotations

import csv
import os
import time
from pathlib import Path
from typing import Iterable, Optional, Sequence


def write_csv_rows_atomic(
    target_path: Path,
    rows: Iterable[Sequence],
    header: Optional[Sequence] = None,
    max_retry_seconds: float = 30.0,
) -> Path:
    """Write rows to ``target_path`` atomically.

    When the canonical CSV cannot be replaced due to an exclusive lock, a shallow copy
    with a timestamp suffix is written and its path is returned to the caller.
    """
    target = Path(target_path)
    target.parent.mkdir(parents=True, exist_ok=True)

    timestamp = time.strftime("%Y%m%d-%H%M%S")
    tmp_name = f".{target.name}.{timestamp}.{os.getpid()}.tmp"
    tmp_path = target.parent / tmp_name

    with tmp_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        if header:
            writer.writerow(list(header))
        for row in rows:
            writer.writerow(list(row))

    deadline = time.monotonic() + max(0.0, max_retry_seconds)
    delay = 0.5

    while True:
        try:
            os.replace(tmp_path, target)
            return target
        except PermissionError:
            if time.monotonic() >= deadline:
                shallow = _write_shallow_copy(tmp_path, target)
                return shallow
            time.sleep(delay)
            delay = min(delay * 2, 5.0)
        except Exception:
            # Clean up the tmp file on unexpected errors before propagating.
            try:
                tmp_path.unlink(missing_ok=True)
            except OSError:
                pass
            raise


def promote_shallow_copy(shallow_path: Path, canonical_path: Path) -> bool:
    """Promote a shallow copy to become the canonical CSV if the lock clears."""
    try:
        os.replace(shallow_path, canonical_path)
        return True
    except PermissionError:
        return False
    except FileNotFoundError:
        return False


def _write_shallow_copy(tmp_path: Path, canonical_path: Path) -> Path:
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    stem = canonical_path.stem or "ToolkitLog"
    suffix = canonical_path.suffix or ".csv"
    shallow_name = f"{stem}_shallow_{timestamp}{suffix}"
    shallow_path = canonical_path.parent / shallow_name
    os.replace(tmp_path, shallow_path)
    return shallow_path
