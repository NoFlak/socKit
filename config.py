"""Compatibility shim for configuration access.

Exposes the public API from `utils.config` at the top level so modules
that import `config` continue to function.
"""

from utils.config import Config, load_config, save_config  # noqa: F401

__all__ = [
    "Config",
    "load_config",
    "save_config",
]

