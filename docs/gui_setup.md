# SOC GUI Setup & Usage

The optional PySide6 dashboard ships as an isolated template under `soc_gui/`.
It is not installed by default so that core CLI workflows stay lightweight.

## Install

```bash
# from the repository root
python -m pip install -r soc_gui/requirements.txt
```

Python 3.11 is recommended to match the rest of the toolkit. A virtual
environment (`python -m venv .venv && .\.venv\Scripts\activate`) keeps GUI
dependencies isolated.

## Launch

```bash
# Preferred: go through the main launcher
python main.py --gui

# Direct launch for development
cd soc_gui
python -m soc_gui.app
```

Launching via `main.py --gui` passes the current `Logs/` directory as a default
environment variable so the GUI auto-detects `ToolkitLog.csv` and
`ToolkitLog.jsonl` paths.

## Features

- **Dashboard** tab: statistic cards, line/bar charts driven by a telemetry feed
- **Logs** tab: tail & filter `.csv`/`.jsonl` files with regex matching
- **Settings** tab: configure log/export directories, theme, autosave interval
- Toolbar shortcuts: `Ctrl+O` to open a log file, `Ctrl+,` to jump to settings
- Dark mode toggle with persistent preferences

## Troubleshooting

- Missing Qt bindings (`ModuleNotFoundError: PySide6`) → run the install command above.
- GUI exits with status > 0 → inspect `soc_gui/logs/app.log` for stack traces.
- Logs not visible → open Settings and point `Logs Dir` at the toolkit’s
  `Logs/` directory (`SOC_GUI_DEFAULT_LOG_PATH` is honoured at launch).
- Headless/CI environments should avoid installing GUI dependencies; the CLI
  will show a warning and continue normally if PySide6 is unavailable.
