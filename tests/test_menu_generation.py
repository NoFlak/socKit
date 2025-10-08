import json
from pathlib import Path

import yaml


def test_menu_manifest_has_core_sections():
    path = Path('menus/menu.yml')
    assert path.exists(), 'menus/menu.yml missing'
    data = yaml.safe_load(path.read_text(encoding='utf-8'))
    assert 'home' in data
    assert 'tools' in data
    assert 'workflows' in data
    # Ensure Blue/Red/Purple entries exist on home
    labels = [e.get('label') for e in data['home'].get('entries', [])]
    for lab in ('Blue Team', 'Red Team', 'Purple Team'):
        assert lab in labels


def test_generator_dry_run(monkeypatch, capsys):
    from tools import generate_menus
    monkeypatch.setattr(generate_menus, 'OUT_DIR', Path('SystemToolkit/AdminTools'))
    generate_menus.main.__globals__['print']  # ensure import ok
    # Run in dry-run mode via function
    # We simulate argparse by calling renderers directly
    menu = generate_menus.load_menu()
    ps1 = generate_menus.render_ps1(menu)
    assert 'Auto Admin Tools' in ps1
    py = generate_menus.render_py(menu)
    assert 'MENU =' in py

