"""Entry point for the socKit automation platform."""

from __future__ import annotations

import argparse
import platform
import sys
from pathlib import Path
from typing import Optional

from blue_team import blue_team_menu
from config import load_config
from network_tools import ping_test
from purple_team import purple_team_menu
from red_team import red_team_menu
from system_tools import (
    display_system_overview,
    enumerate_services,
    list_critical_paths,
    system_file_checker,
)
from utils import (
    create_directory,
    display_ip_configuration,
    display_mac_addresses,
    display_user_information,
    list_directory_contents,
)
from workflow_engine import bootstrap_builtin_tasks, ensure_playbook, list_tasks, run_playbook


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


def interactive_menu(questionnaire_path: Path) -> None:
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
        elif choice == "Q":
            print("Exiting the toolkit. Goodbye!")
            break
        else:
            print("Invalid selection. Please try again.")


def main() -> None:
    args = parse_args()
    config = load_config()
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
    interactive_menu(questionnaire_path)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit("\nInterrupted by user.")