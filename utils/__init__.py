"""Utilities package for socKit with lazy exports.

Avoids importing heavy submodules at package import time to prevent
circular imports. Selected attributes are exposed lazily via __getattr__.
"""

from __future__ import annotations

import importlib
from types import ModuleType
from typing import Any, Dict

_EXPORTS: Dict[str, tuple[str, str]] = {
    # Diagnostics helpers
    "create_directory": ("utils.diagnostics", "create_directory"),
    "list_directory_contents": ("utils.diagnostics", "list_directory_contents"),
    "display_ip_configuration": ("utils.diagnostics", "display_ip_configuration"),
    "display_mac_addresses": ("utils.diagnostics", "display_mac_addresses"),
    "display_user_information": ("utils.diagnostics", "display_user_information"),
    "system_diagnostics": ("utils.diagnostics", "run"),
    # Logging
    "write_action": ("logging_utils", "write_action"),
    # Command execution
    "execute_command_async": ("utils.command_utils", "execute_command_async"),
    # Environment/setup
    "initialize_environment": ("utils.setup_utils", "initialize_environment"),
    # Config (legacy compat)
    "load_config": ("utils.config", "load_config"),
}


def __getattr__(name: str) -> Any:
    target = _EXPORTS.get(name)
    if not target:
        raise AttributeError(f"module 'utils' has no attribute '{name}'")
    module_name, attr = target
    module: ModuleType = importlib.import_module(module_name)
    return getattr(module, attr)


__all__ = list(_EXPORTS.keys())
