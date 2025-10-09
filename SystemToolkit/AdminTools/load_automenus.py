"""
Safe loader utilities for the data-driven AutoMenu manifest.

Usage (opt-in):
    from SystemToolkit.AdminTools.load_automenus import load_menu, render_menu_console

    manifest = load_menu()
    print(render_menu_console(manifest))

This module does not execute commands; it only parses menus/menu.yml and returns
structured data so callers can render menus in their own UI layers.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

import yaml

DEFAULT_MANIFEST = Path("menus") / "menu.yml"


def load_menu(manifest_path: str | Path = DEFAULT_MANIFEST) -> Dict[str, Any]:
    """Load the menu manifest from YAML and return a dictionary."""
    manifest_path = Path(manifest_path)
    if not manifest_path.exists():
        raise FileNotFoundError(
            f"Menu manifest not found at {manifest_path}. "
            "Run tools/generate_menus.py or create menus/menu.yml."
        )

    data = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Menu manifest must be a YAML mapping. Got {type(data).__name__}")
    return data


def render_menu_console(manifest: Dict[str, Any]) -> str:
    """
    Render an informational console summary of the menu manifest.

    Placeholder entries are annotated so operators know which items require implementation.
    """
    lines: List[str] = []
    title = manifest.get("title") or "AutoMenu"
    lines.append(f"=== {title} ===")

    items = manifest.get("items", [])
    if not isinstance(items, list):
        lines.append("[WARN] manifest.items is not a list")
        return "\n".join(lines)

    for entry in items:
        label = entry.get("label", "Unnamed")
        placeholder = entry.get("placeholder", False)
        tag = " (PLACEHOLDER)" if placeholder else ""
        entry_type = entry.get("type", "item")

        if entry_type == "group":
            lines.append(f"\n## {label}{tag} ##")
            children = entry.get("items", [])
            if not isinstance(children, list):
                lines.append("  [WARN] group.items is not a list")
                continue
            for child in children:
                child_label = child.get("label", "Unnamed child")
                child_placeholder = child.get("placeholder", False)
                child_tag = " (PLACEHOLDER)" if child_placeholder else ""
                lines.append(f"  - {child_label}{child_tag}")
        else:
            lines.append(f"{label}{tag}")

    lines.append("")  # trailing newline for readability
    return "\n".join(lines)


__all__ = ["load_menu", "render_menu_console"]

