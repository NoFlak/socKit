from __future__ import annotations

"""
Artifact store helpers for SOC kit tooling.

Supports:
- local filesystem mirroring (default)
- S3/MinIO uploads with local shadow copies for auditability

Key environment variables:
- SOCKIT_ARTIFACT_STORE: one of "local", "s3", or "minio"
- SOCKIT_ARTIFACT_BUCKET: bucket/container name when using remote mode
- SOCKIT_ARTIFACT_ENDPOINT: endpoint URL for MinIO/S3 targets
- SOCKIT_ARTIFACT_BASE: base directory for local mode (defaults to artifacts/)
- SOCKIT_ARTIFACT_PREFIX: optional key prefix when uploading to remote storage
- SOCKIT_ARTIFACT_REGION / *_ACCESS_KEY / *_SECRET_KEY / *_SESSION_TOKEN for credentials
- SOCKIT_ARTIFACT_VERIFY_SSL: control TLS validation (true/false or path to CA bundle)
"""

import json
import os
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional, Union

from logging_utils import write_action

try:
    from botocore.exceptions import BotoCoreError, ClientError
except ImportError:  # pragma: no cover - only when boto3/botocore not installed
    BotoCoreError = ClientError = Exception  # type: ignore[assignment]

DEFAULT_LOCAL_BASE = Path("artifacts") / "remote_mirror"
_LOCK = threading.Lock()
_STORE: "ArtifactStore" | None = None


def _sanitize(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


def _parse_verify(value: Optional[str]) -> Union[bool, str]:
    if value is None:
        return True
    trimmed = value.strip()
    if not trimmed:
        return True
    lowered = trimmed.lower()
    if lowered in {"false", "0", "no"}:
        return False
    if lowered in {"true", "1", "yes"}:
        return True
    return trimmed


@dataclass
class ArtifactStoreConfig:
    mode: str = "local"
    bucket: str = "soc-kit"
    endpoint: str | None = None
    base_dir: Path = Path("artifacts")
    prefix: str = ""
    region: str | None = None
    access_key: str | None = None
    secret_key: str | None = None
    session_token: str | None = None
    verify_ssl: Union[bool, str] = True

    @staticmethod
    def from_env() -> "ArtifactStoreConfig":
        mode = os.getenv("SOCKIT_ARTIFACT_STORE", "local").strip().lower()
        bucket = os.getenv("SOCKIT_ARTIFACT_BUCKET", "soc-kit")
        endpoint = os.getenv("SOCKIT_ARTIFACT_ENDPOINT")
        base = Path(os.getenv("SOCKIT_ARTIFACT_BASE", "artifacts")).resolve()
        prefix = os.getenv("SOCKIT_ARTIFACT_PREFIX", "").strip().strip("/")
        region = _sanitize(os.getenv("SOCKIT_ARTIFACT_REGION"))
        access_key = _sanitize(os.getenv("SOCKIT_ARTIFACT_ACCESS_KEY"))
        secret_key = _sanitize(os.getenv("SOCKIT_ARTIFACT_SECRET_KEY"))
        session_token = _sanitize(os.getenv("SOCKIT_ARTIFACT_SESSION_TOKEN"))
        verify_ssl = _parse_verify(os.getenv("SOCKIT_ARTIFACT_VERIFY_SSL"))
        return ArtifactStoreConfig(
            mode=mode,
            bucket=bucket,
            endpoint=endpoint,
            base_dir=base,
            prefix=prefix,
            region=region,
            access_key=access_key,
            secret_key=secret_key,
            session_token=session_token,
            verify_ssl=verify_ssl,
        )


class ArtifactStore:
    """Lightweight artifact store facade with a local fallback."""

    def __init__(self, config: ArtifactStoreConfig) -> None:
        self._config = config
        self._remote_enabled = config.mode in {"s3", "minio"}
        self._remote_prefix = (config.prefix or "").strip("/")
        self._client = None

        if self._remote_enabled:
            # Remote targets still mirror to local path for audits.
            self._root = DEFAULT_LOCAL_BASE
            try:
                self._client = _build_remote_client(config)
            except RuntimeError as exc:
                write_action(
                    "Artifact store remote client unavailable.",
                    level="WARNING",
                    context={
                        "mode": config.mode,
                        "bucket": config.bucket,
                        "endpoint": config.endpoint or "",
                        "error": str(exc),
                    },
                )
        else:
            self._root = config.base_dir

        self._root.mkdir(parents=True, exist_ok=True)
        write_action(
            "Artifact store initialized.",
            context={
                "mode": config.mode,
                "bucket": config.bucket,
                "endpoint": config.endpoint or "",
                "remote_prefix": self._remote_prefix,
                "root": str(self._root),
            },
        )

    # Public API ---------------------------------------------------------
    def save_json(self, *, relative_path: str, document: Dict[str, Any]) -> Path:
        """Persist JSON metadata to the configured backend."""
        path = self._root / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        serialized = json.dumps(document, indent=2)
        path.write_text(serialized, encoding="utf-8")
        self._maybe_mirror_remote(relative_path, serialized)
        return path

    def save_file(self, *, relative_path: str, source: Path) -> Path:
        """Copy/link an existing artifact into the store."""
        path = self._root / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        if source.exists():
            data = source.read_bytes()
            path.write_bytes(data)
            self._maybe_mirror_remote(relative_path, data)
        else:
            write_action(
                "Artifact store missing source file.",
                level="WARNING",
                context={"source": str(source), "destination": str(path)},
            )
        return path

    # Internal helpers ---------------------------------------------------
    def _maybe_mirror_remote(self, key: str, payload: Any) -> None:
        if not self._remote_enabled:
            return

        remote_key = self._remote_key(key)
        preview = self._preview(payload)
        body = self._payload_bytes(payload)

        if self._client is None:
            write_action(
                "Artifact store remote upload skipped (client unavailable).",
                level="WARNING",
                context={
                    "bucket": self._config.bucket,
                    "endpoint": self._config.endpoint or "",
                    "key": remote_key,
                    "preview": preview,
                },
            )
            return

        try:
            self._client.put_object(Bucket=self._config.bucket, Key=remote_key, Body=body)
            write_action(
                "Artifact store remote upload complete.",
                context={
                    "bucket": self._config.bucket,
                    "key": remote_key,
                },
            )
        except (BotoCoreError, ClientError, OSError) as exc:
            write_action(
                "Artifact store remote upload failed.",
                level="ERROR",
                context={
                    "bucket": self._config.bucket,
                    "key": remote_key,
                    "preview": preview,
                },
                detailed_results=str(exc),
            )

    @staticmethod
    def _preview(payload: Any) -> str:
        if isinstance(payload, (bytes, bytearray)):
            return f"<binary {len(payload)} bytes>"
        text = str(payload)
        if len(text) > 200:
            return text[:200] + "... (truncated)"
        return text

    @staticmethod
    def _payload_bytes(payload: Any) -> bytes:
        if isinstance(payload, (bytes, bytearray)):
            return bytes(payload)
        if isinstance(payload, str):
            return payload.encode("utf-8")
        return json.dumps(payload).encode("utf-8")

    def _remote_key(self, key: str) -> str:
        normalized = key.replace("\\", "/")
        if self._remote_prefix:
            return f"{self._remote_prefix}/{normalized}"
        return normalized


def get_store(config: ArtifactStoreConfig | None = None) -> ArtifactStore:
    """Return a process-wide singleton store."""
    global _STORE
    with _LOCK:
        if config is None and _STORE is not None:
            return _STORE

        cfg = config or ArtifactStoreConfig.from_env()
        store = ArtifactStore(cfg)
        if config is None:
            _STORE = store
        return store


__all__ = ["ArtifactStore", "ArtifactStoreConfig", "get_store"]


def _build_remote_client(config: ArtifactStoreConfig):
    try:
        import boto3
        from botocore.config import Config as BotoConfig
    except ImportError as exc:  # pragma: no cover - environment without boto3
        raise RuntimeError("Remote artifact storage requires boto3 to be installed.") from exc

    session_kwargs: Dict[str, Any] = {}
    if config.access_key and config.secret_key:
        session_kwargs["aws_access_key_id"] = config.access_key
        session_kwargs["aws_secret_access_key"] = config.secret_key
    if config.session_token:
        session_kwargs["aws_session_token"] = config.session_token

    session = boto3.session.Session(region_name=config.region or "us-east-1", **session_kwargs)
    s3_options = {"addressing_style": "path"} if config.mode == "minio" else None
    boto_cfg = (
        BotoConfig(signature_version="s3v4", s3=s3_options) if s3_options else BotoConfig(signature_version="s3v4")
    )

    verify = config.verify_ssl
    use_ssl = True if not isinstance(verify, bool) else bool(verify)
    client = session.client(
        "s3",
        endpoint_url=config.endpoint,
        use_ssl=use_ssl,
        verify=verify,
        config=boto_cfg,
    )
    return client
