"""Entry point for the socKit automation platform."""

from __future__ import annotations

import argparse
import os
import platform
import sys
from pathlib import Path
import subprocess
from typing import Optional
import time
import yaml

from blue_team import blue_team_menu
from config import load_config, save_config
from network_tools import ping_test
from purple_team import purple_team_menu
from red_team import red_team_menu
from system_tools import (
    display_system_overview,
    enumerate_services,
    list_critical_paths,
    system_file_checker,
)
from system_tool.system_tools import system_tools_menu
from utils import (
    create_directory,
    display_ip_configuration,
    display_mac_addresses,
    display_user_information,
    list_directory_contents,
)
from workflow_engine import bootstrap_builtin_tasks, ensure_playbook, list_tasks, run_playbook


def _first_run_setup(config) -> None:
    """Prompt for a log folder on first run if no config exists.

    If `config.json` is missing or `log_folder` is empty, ask the user whether
    to use the default path or provide a custom one, then persist via save_config.
    """
    cfg_path = Path("config.json")
    needs_prompt = (not cfg_path.exists()) or (not getattr(config, "log_folder", None))
    if not needs_prompt:
        return

    default_path = str((Path.cwd() / "logs").resolve())
    print("\n=== First‑Time Setup ===")
    print("Choose where to store logs.")
    user_input = input(f"Log folder [{default_path}]: ").strip()
    chosen = user_input or default_path
    # Ensure folder exists before saving
    try:
        Path(chosen).mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        print(f"[ERROR] Unable to create log folder at {chosen}: {exc}")
        print("Falling back to default.")
        chosen = default_path
        Path(chosen).mkdir(parents=True, exist_ok=True)

    # Persist selection
    config.log_folder = chosen
    try:
        save_config(config)
        print(f"Saved configuration to {cfg_path} (log_folder={chosen}).")
    except Exception:
        # Non-fatal; continue with in-memory config
        print("[WARN] Could not save configuration file. Using in-memory settings.")


def _ensure_writable_log_folder(config) -> None:
    """Verify the log folder is writable; if not, guide user to fix it.

    Attempts to create the folder and write a small test file. If it fails,
    prompts (when interactive) for an alternate path. Falls back to a default
    path under the current working directory without crashing.
    """
    target = Path(getattr(config, "log_folder", "logs"))
    default_path = (Path.cwd() / "logs").resolve()
    is_interactive = sys.stdin.isatty()

    while True:
        try:
            target.mkdir(parents=True, exist_ok=True)
            probe = target / ".write_test.tmp"
            probe.write_text("ok", encoding="utf-8")
            probe.unlink(missing_ok=True)
            # Writable, persist if different from config
            config.log_folder = str(target)
            try:
                save_config(config)
            except Exception:
                pass  # non-fatal
            print(f"Log folder confirmed: {target}")
            return
        except OSError as exc:
            print(f"[WARN] Log folder is not writable: {target} ({exc})")
            if is_interactive:
                new_path = input(f"Enter an alternate log path [{default_path}]: ").strip() or str(default_path)
                target = Path(new_path)
                continue
            else:
                # Non-interactive: silently fall back to default
                target = default_path
                continue


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Cross-platform SOC automation toolkit")
    parser.add_argument("--playbook", help="Run the specified workflow playbook")
    parser.add_argument("--dry-run", action="store_true", help="Preview a playbook without executing tasks")
    parser.add_argument("--list-tasks", action="store_true", help="List all available workflow tasks")
    parser.add_argument("--questionnaire", action="store_true", help="Display the direction questionnaire")
    parser.add_argument("--gui", action="store_true", help="Launch the optional SOC GUI instead of CLI menu")
    return parser.parse_args()


def display_questionnaire(path: Path) -> None:
    if not path.exists():
        # Fallback to docs/overview.md if configured path missing
        fallback = Path("docs/overview.md")
        if fallback.exists():
            print(f"\n[Info] Using fallback questionnaire: {fallback}")
            print("\n=== Strategy Questionnaire (Overview) ===\n")
            print(fallback.read_text(encoding="utf-8"))
            return
        print(f"Questionnaire file {path} not found. Consider reviewing docs for alignment.")
        return
    print("\n=== Strategy Questionnaire ===\n")
    print(path.read_text(encoding="utf-8"))


def _run_quick_health() -> None:
    print("\n[Quick Health] System overview...")
    display_system_overview()
    print("\n[Quick Health] Enumerating services (preview)...")
    enumerate_services()
    print("\n[Quick Health] Critical paths...")
    list_critical_paths([])


def _launch_admin_tools_ps() -> None:
    if platform.system() != "Windows":
        print("Admin Tools (PowerShell) is available on Windows only.")
        return
    try:
        script_path = Path(__file__).parent / "SystemToolkit" / "AdminTools" / "AdminTools.ps1"
        if not script_path.exists():
            print(f"Admin Tools script not found at {script_path}")
            return
        subprocess.run([
            "powershell",
            "-NoProfile",
            "-ExecutionPolicy", "Bypass",
            "-File", str(script_path)
        ])
    except Exception as exc:
        print(f"Failed to launch Admin Tools: {exc}")


def _tools_hub_menu(log_folder: str) -> None:
    from network_tools import dns_health_check, tcp_port_scan
    while True:
        print("\n==== Tools Hub ====")
        print("1) System Tools")
        print("2) Network Tools")
        print("3) Admin Tools")
        print("4) Detailed System Toolkit")
        print("0) Back")
        choice = input("Select: ").strip()
        if choice == "1":
            while True:
                print("\n-- System Tools --")
                print("1) System Overview")
                print("2) Enumerate Services (preview)")
                print("3) Critical Path Inventory")
                print("4) System File Checker")
                print("0) Back")
                sc = input("Select: ").strip()
                if sc == "1":
                    display_system_overview()
                elif sc == "2":
                    enumerate_services()
                elif sc == "3":
                    list_critical_paths([])
                elif sc == "4":
                    system_file_checker()
                elif sc == "0":
                    break
                else:
                    print("Invalid selection.")
        elif choice == "2":
            while True:
                print("\n-- Network Tools --")
                print("1) Ping Test")
                print("2) DNS Health Check")
                print("3) TCP Port Scan")
                print("0) Back")
                nc = input("Select: ").strip()
                if nc == "1":
                    ping_test()
                elif nc == "2":
                    domains = input("Comma-separated domains (e.g., example.com,google.com): ").strip()
                    dom_list = [d.strip() for d in domains.split(',') if d.strip()]
                    if dom_list:
                        dns_health_check(dom_list)
                    else:
                        print("No domains provided.")
                elif nc == "3":
                    host = input("Host/IP: ").strip()
                    ports_raw = input("Ports (comma-separated, e.g., 22,80,443): ").strip()
                    try:
                        ports = [int(p.strip()) for p in ports_raw.split(',') if p.strip()]
                    except ValueError:
                        print("Invalid ports input.")
                        continue
                    tcp_port_scan(host, ports)
                elif nc == "0":
                    break
                else:
                    print("Invalid selection.")
        elif choice == "3":
            _launch_admin_tools_ps()
        elif choice == "4":
            system_tools_menu(log_folder)
        elif choice == "0":
            return
        else:
            print("Invalid selection.")


def _write_temp_playbook(steps: list[dict], name: str) -> Path:
    folder = Path("playbooks")
    folder.mkdir(parents=True, exist_ok=True)
    ts = time.strftime("%Y%m%d-%H%M%S")
    path = folder / f"{name}-{ts}.yaml"
    with path.open("w", encoding="utf-8") as f:
        yaml.safe_dump({"name": name, "steps": steps}, f, sort_keys=False)
    return path


def _workflows_menu() -> None:
    while True:
        print("\n==== Workflows ====")
        print("1) System Quick Health")
        print("2) Blue Team Baseline")
        print("3) Red Team Recon")
        print("4) Purple Analytics")
        print("5) Admin Winget Upgrades (preview)")
        print("L) List all tasks")
        print("0) Back")
        choice = input("Select: ").strip().upper()
        if choice == "1":
            steps = [
                {"task": "system.overview"},
                {"task": "system.services"},
                {"task": "network.ping", "args": {"target": "8.8.8.8", "count": 2}},
            ]
            path = _write_temp_playbook(steps, "quick_health")
            run_playbook(path)
        elif choice == "2":
            steps = [
                {"task": "blue.shadow"},
                {"task": "blue.patch_status"},
                {"task": "blue.file_integrity"},
            ]
            path = _write_temp_playbook(steps, "blue_baseline")
            run_playbook(path)
        elif choice == "3":
            steps = [
                {"task": "red.credential_exposure"},
                {"task": "red.lateral_movement"},
            ]
            path = _write_temp_playbook(steps, "red_recon")
            run_playbook(path)
        elif choice == "4":
            steps = [
                {"task": "purple.dashboard"},
                {"task": "purple.correlation"},
            ]
            path = _write_temp_playbook(steps, "purple_analytics")
            run_playbook(path)
        elif choice == "5":
            steps = [
                {"task": "admin.winget_upgrade", "args": {"include_unknown": True, "dry_run": True}},
            ]
            path = _write_temp_playbook(steps, "winget_preview")
            run_playbook(path)
        elif choice == "L":
            print("\nAvailable Tasks:")
            for task in list_tasks():
                print(f" - {task}")
        elif choice == "0":
            return
        else:
            print("Invalid selection.")


def _launch_gui(log_folder: str) -> None:
    """
    Attempt to launch the optional PySide6-based GUI shipped under soc_gui/.

    - If soc_gui is not present, inform the operator.
    - Pass default log paths via environment variables so the GUI can pre-populate settings.
    """
    repo_root = Path(__file__).resolve().parent
    gui_root = repo_root / "soc_gui"
    if not gui_root.exists():
        print("[WARN] soc_gui package not found in repository root. Ensure the GUI template is installed.")
        return

    env = os.environ.copy()
    try:
        env.setdefault("SOC_GUI_DEFAULT_LOG_PATH", str(Path(log_folder).resolve()))
        jsonl_path = Path(log_folder).resolve() / "ToolkitLog.jsonl"
        if jsonl_path.exists():
            env.setdefault("SOC_GUI_DEFAULT_JSONL_PATH", str(jsonl_path))
    except Exception:
        # Environment fallbacks are best-effort; ignore resolution errors.
        pass

    print("[INFO] Launching SOC GUI (python -m soc_gui.app). Close the window to return to CLI.")
    try:
        result = subprocess.run(
            [sys.executable, "-m", "soc_gui.app"],
            cwd=repo_root,
            env=env,
            check=False,
        )
        if result.returncode not in (0, None):
            print(f"[WARN] SOC GUI exited with code {result.returncode}. Check soc_gui/logs/app.log for details.")
    except FileNotFoundError:
        print("[ERROR] Unable to locate python executable for launching the GUI.")
    except Exception as exc:  # noqa: BLE001
        print(f"[ERROR] Failed to launch SOC GUI: {exc}")


def interactive_menu(questionnaire_path: Path, *, log_folder: str) -> None:
    while True:
        print("\n==========================================")
        print("      Cross-Platform SOC Toolkit v3.1     ")
        print("==========================================")
        print("1) Quick Health")
        print("2) Tools")
        print("3) Workflows")
        print("4) Blue Team")
        print("5) Red Team")
        print("6) Purple Team")
        print("7) System Maintenance Toolkit")
        print("8) Launch SOC GUI")
        print("9) Help / Questionnaire")
        print("Q) Quit")
        print("==========================================")
        choice = input("Select: ").strip().upper()

        if choice == "1":
            _run_quick_health()
        elif choice == "2":
            _tools_hub_menu(log_folder)
        elif choice == "3":
            _workflows_menu()
        elif choice == "4":
            try:
                blue_team_menu(log_folder=log_folder)
            except TypeError:
                try:
                    blue_team_menu(log_folder)
                except TypeError:
                    try:
                        blue_team_menu()
                    except Exception as exc:  # noqa: BLE001
                        print(f"[ERROR] Blue Team menu failed: {exc}")
            except Exception as exc:  # noqa: BLE001
                print(f"[ERROR] Blue Team menu failed: {exc}")
        elif choice == "5":
            try:
                red_team_menu()
            except TypeError:
                try:
                    red_team_menu(log_folder=log_folder)
                except TypeError:
                    print("[WARN] Red Team menu signature unsupported; skipping log context.")
                    try:
                        red_team_menu()
                    except Exception as exc:  # noqa: BLE001
                        print(f"[ERROR] Red Team menu failed: {exc}")
            except Exception as exc:  # noqa: BLE001
                print(f"[ERROR] Red Team menu failed: {exc}")
        elif choice == "6":
            try:
                purple_team_menu()
            except TypeError:
                try:
                    purple_team_menu(log_folder=log_folder)
                except TypeError:
                    print("[WARN] Purple Team menu signature unsupported; skipping log context.")
                    try:
                        purple_team_menu()
                    except Exception as exc:  # noqa: BLE001
                        print(f"[ERROR] Purple Team menu failed: {exc}")
            except Exception as exc:  # noqa: BLE001
                print(f"[ERROR] Purple Team menu failed: {exc}")
        elif choice == "7":
            system_tools_menu(log_folder)
        elif choice == "8":
            _launch_gui(log_folder)
        elif choice == "9":
            display_questionnaire(questionnaire_path)
        elif choice == "Q":
            print("Exiting the toolkit. Goodbye!")
            break
        else:
            print("Invalid selection. Please try again.")


def main() -> None:
    args = parse_args()
    config = load_config()
    # First-time setup: prompt for log folder if config.json is missing
    _first_run_setup(config)
    # Ensure log folder is writable; prompt/fallback if not
    _ensure_writable_log_folder(config)
    create_directory(config.log_folder)
    create_directory(config.artifacts_folder)

    bootstrap_builtin_tasks()

    if args.list_tasks:
        print("\nAvailable Tasks:")
        for task in list_tasks():
            print(f" - {task}")
        return

    questionnaire_path = Path(config.questionnaire_file)
    if args.questionnaire:
        display_questionnaire(questionnaire_path)
        if not args.playbook:
            return

    if args.playbook:
        playbook_path = ensure_playbook(args.playbook)
        run_playbook(playbook_path, dry_run=args.dry_run)
        return

    if args.gui:
        _launch_gui(config.log_folder)
        return

    print(f"Operating System Detected: {platform.system()}")
    print(f"Log folder: {config.log_folder}")
    interactive_menu(questionnaire_path, log_folder=config.log_folder)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit("\nInterrupted by user.")
