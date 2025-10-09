from pathlib import Path

from SystemToolkit.AdminTools.load_automenus import load_menu, render_menu_console


def test_manifest_has_core_sections():
    manifest = load_menu()
    # Part 1 manifest exposes home/tools/workflows instead of items
    assert "home" in manifest
    assert "tools" in manifest
    assert "workflows" in manifest
    assert manifest.get("version") or manifest.get("menu_version")


def test_placeholder_tokens_preserved():
    text = Path("menus/menu.yml").read_text(encoding="utf-8")
    assert "PLACEHOLDER" in text
    summary = render_menu_console(load_menu())
    assert isinstance(summary, str)
