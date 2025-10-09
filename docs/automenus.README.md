# AutoMenus Loader (Opt-in)

`SystemToolkit/AdminTools/load_automenus.py` provides a safe, read-only loader for the
data-driven menu manifest at `menus/menu.yml`.

## Quick usage

```python
from SystemToolkit.AdminTools.load_automenus import load_menu, render_menu_console

manifest = load_menu()
print(render_menu_console(manifest))
```

This module only loads and formats the manifest. It does not execute any menu commands.

