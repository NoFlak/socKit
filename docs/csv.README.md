# CSV Logging Reliability

The toolkit maintains two human-friendly CSV views of activity (`ToolkitLog.csv` and
`ToolkitTables.csv`). Office applications such as Excel or OneDrive can temporarily lock
these files, preventing the automation from appending new rows. To avoid data loss we now
write CSV content atomically and fall back to timestamped shallow copies when the canonical
file is locked.

## Utility Overview

- `utils/csv_safe_writer.write_csv_rows_atomic(target_path, rows, header, max_retry_seconds)` –
  writes rows to a temporary file in the destination directory, then promotes it with
  `os.replace()`. If repeated attempts fail because another process holds a lock, a shallow
  copy named `ToolkitLog_shallow_YYYYMMDD-HHMMSS.csv` is emitted instead and its path is
  returned to the caller.
- `utils/csv_safe_writer.promote_shallow_copy(shallow, canonical)` – retries promotion after
  the caller detects that the canonical file is available again.

## Developer Guidance

1. Always prefer `write_csv_rows_atomic` over manual `open(..., "a")` calls when writing to
   `ToolkitLog.csv` (or any long-lived CSV logs).
2. When a shallow copy path is returned, keep operating against it or notify the operator.
   Optionally call `promote_shallow_copy` later in a background task.
3. Downstream analytics (e.g., the Purple Team dashboards) already handle both canonical and
   shallow log files.

## Testing

Automated tests under `tests/test_csv_safe_writer.py` cover:

- successful atomic writes,
- simulated `PermissionError` scenarios that trigger the shallow copy behavior,
- promotion of shallow copies back to the canonical file.
