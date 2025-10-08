"""Entry point for the socKit automation platform."""

from __future__ import annotations

import argparse
import platform
import sys
from pathlib import Path
from typing import Optional

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
    return parser.parse_args()


def display_questionnaire(path: Path) -> None:
    if not path.exists():
        print(f"Questionnaire file {path} not found. Consider reviewing docs for alignment.")
        return
    print("\n=== Strategy Questionnaire ===\n")
    print(path.read_text(encoding="utf-8"))


def interactive_menu(questionnaire_path: Path, *, log_folder: str) -> None:
    while True:
        print("\n==========================================")
        print("      Cross-Platform SOC Toolkit v3.0     ")
        print("==========================================")
        print("1. System Diagnostics")
        print("2. Network Diagnostics")
        print("3. Red Team Automation")
        print("4. Blue Team Automation")
        print("5. Purple Team Analytics")
        print("6. Run Workflow Playbook")
        print("7. Directory Insights")
        print("8. IP Configuration")
        print("9. MAC Address Information")
        print("10. User Information")
        print("11. Show Strategy Questionnaire")
        print("12. System Toolkit (Detailed)")
        print("Q. Quit")
        print("==========================================")
        choice = input("Enter your choice: ").strip().upper()

        if choice == "1":
            display_system_overview()
            enumerate_services()
            list_critical_paths([])
            system_file_checker()
        elif choice == "2":
            ping_test()
        elif choice == "3":
            red_team_menu()
        elif choice == "4":
            blue_team_menu()
        elif choice == "5":
            purple_team_menu()
        elif choice == "6":
            playbook_name = input("Enter playbook filename (leave blank for default): ").strip() or "playbooks/quick_health.yaml"
            path = ensure_playbook(playbook_name)
            run_playbook(path)
        elif choice == "7":
            directory = input("Enter directory to inspect (blank for current): ").strip() or "."
            list_directory_contents(directory)
        elif choice == "8":
            display_ip_configuration()
        elif choice == "9":
            display_mac_addresses()
        elif choice == "10":
            display_user_information()
        elif choice == "11":
            display_questionnaire(questionnaire_path)
        elif choice == "12":
            system_tools_menu(log_folder)
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

    print(f"Operating System Detected: {platform.system()}")
    print(f"Log folder: {config.log_folder}")
    interactive_menu(questionnaire_path, log_folder=config.log_folder)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit("\nInterrupted by user.")
