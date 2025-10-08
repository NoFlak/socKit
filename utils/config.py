"""Configuration management for socKit."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Any, Dict, MutableMapping

CONFIG_FILE = "config.json"
ENV_PREFIX = "SOCKIT_"


@dataclass
class Config:
    """Runtime configuration for the toolkit."""

    log_folder: str = "logs"
    timeout: int = 300
    default_scan_type: str = "Aggressive"
    playbooks_folder: str = "playbooks"
    artifacts_folder: str = "artifacts"
    questionnaire_file: str = "docs/direction_questionnaire.md"
    # Security and hygiene
    secure_logs: bool = True
    log_retention_days: int = 30
    redact_host_identifiers: bool = True
    extra: Dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> Dict[str, Any]:
        base = {
            "log_folder": self.log_folder,
            "timeout": self.timeout,
            "default_scan_type": self.default_scan_type,
            "playbooks_folder": self.playbooks_folder,
            "artifacts_folder": self.artifacts_folder,
            "questionnaire_file": self.questionnaire_file,
            "secure_logs": self.secure_logs,
            "log_retention_days": self.log_retention_days,
            "redact_host_identifiers": self.redact_host_identifiers,
        }
        base.update(self.extra)
        return base


def _merge_dict(base: MutableMapping[str, Any], updates: MutableMapping[str, Any]) -> None:
    for key, value in updates.items():
        if isinstance(value, MutableMapping) and isinstance(base.get(key), MutableMapping):
            _merge_dict(base[key], value)  # type: ignore[index]
        else:
            base[key] = value


def _ensure_directories(config: Config) -> None:
    os.makedirs(config.log_folder, exist_ok=True)
    os.makedirs(config.playbooks_folder, exist_ok=True)
    os.makedirs(config.artifacts_folder, exist_ok=True)


def _apply_environment_overrides(data: Dict[str, Any]) -> None:
    for key in list(data.keys()):
        env_key = f"{ENV_PREFIX}{key.upper()}"
        if env_key in os.environ:
            raw_value = os.environ[env_key]
            if isinstance(data[key], bool):
                data[key] = raw_value.lower() in {"1", "true", "yes", "on"}
            elif isinstance(data[key], int):
                try:
                    data[key] = int(raw_value)
                except ValueError:
                    pass
            else:
                data[key] = raw_value


def load_config(overrides: Dict[str, Any] | None = None) -> Config:
    """Load configuration from disk, environment variables, and overrides."""

    data: Dict[str, Any] = Config().as_dict()

    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                file_config = json.load(f)
            if isinstance(file_config, dict):
                _merge_dict(data, file_config)
            else:
                print("Warning: config.json does not contain a JSON object. Using defaults.")
        except json.JSONDecodeError as exc:
            print(f"Error loading configuration file: {exc}")
        except OSError as exc:
            print(f"Error opening configuration file: {exc}")

    if overrides:
        _merge_dict(data, overrides)

    _apply_environment_overrides(data)

    valid_fields = set(Config.__dataclass_fields__.keys())
    config_kwargs = {k: v for k, v in data.items() if k in valid_fields}
    config = Config(**config_kwargs)
    extra = {k: v for k, v in data.items() if k not in config_kwargs}
    config.extra = extra

    _ensure_directories(config)

    return config


def save_config(config: Config) -> None:
    """Persist the provided configuration to disk."""

    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config.as_dict(), f, indent=2)
    except OSError as exc:
        print(f"Error saving configuration file: {exc}")
