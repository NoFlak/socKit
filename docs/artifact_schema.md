# Artifact Schema (Canonical JSON)

All tools that produce artifacts should write a normalized JSON alongside raw outputs.

Base directories (configurable):
- artifacts/raw/<ts>/...
- artifacts/json/<ts>/...

Fields
- timestamp (string, ISO8601 UTC, e.g., 2025-10-08T22:00:00Z)
- repository (string, e.g., socKit)
- operator (string)
- tool (string: nmap|osquery|tcpdump|winget|airodump|custom)
- tool_version (string)
- target (string or array)
- raw_artifact_path (string, relative path or URL)
- raw_sha256 (string, hex lowercase)
- summary (object: tool-specific counts, e.g., hosts, open_ports)
- mitre_tags (array<string> technique ids)
- dry_run (boolean)
- log_path (string)

Notes
- Preserve privacy-sensitive fields via existing logging redaction settings where applicable.
- Raw artifacts are not moved automatically; producers should pass the path to write_artifact.

