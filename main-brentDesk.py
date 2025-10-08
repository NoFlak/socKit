import importlib
import os
from utils import load_config, write_action

TOOL_CATEGORIES = {
    "Blue Team": "blue_team",
    "Red Team": "red_team",
    "Purple Team": "purple_team",
    "System Tools": "system_tool",  # Ensure this matches your folder/package names
    "Diagnostics": "utils.diagnostics"  # Optional separate category
}

def list_tools(package_name):
    """List available tool modules in the specified package folder."""
    try:
        package_path = os.path.join(os.path.dirname(__file__), *package_name.split('.'))
        tools = [
            f[:-3] for f in os.listdir(package_path)
            if f.endswith(".py") and f != "__init__.py"
        ]
        return tools
    except FileNotFoundError:
        print(f"Package directory '{package_name}' not found.")
        return []

def run_tool(package, tool_name, log_folder):
    """Import the tool module and run its run(log_folder) method if available."""
    try:
        module_path = f"{package}.{tool_name}"
        tool_module = importlib.import_module(module_path)
        write_action(f"Running {tool_name} from {package}", log_folder)
        if hasattr(tool_module, "run"):
            try:
                tool_module.run(log_folder=log_folder)
            except TypeError:
                tool_module.run()
        else:
            print(f"{tool_name} does not define a run() method.")
    except Exception as e:
        error_msg = f"Error running {tool_name}: {e}"
        print(error_msg)
        write_action(error_msg, log_folder)

def show_main_menu():
    print("\n=== SOC Toolkit Main Menu ===")
    for idx, category in enumerate(TOOL_CATEGORIES, start=1):
        print(f"{idx}. {category}")
    print("Q. Exit")

def show_tools_menu(category):
    package = TOOL_CATEGORIES[category]
    tools = list_tools(package)
    print(f"\n--- {category} ---")
    for idx, tool in enumerate(tools, start=1):
        print(f"{idx}. {tool}")
    print("0. Back")
    return tools, package

import os

def main():
    config = load_config()
    log_folder = config.get("log_folder", "logs")

    # Validate and create log folder safely
    try:
        os.makedirs(log_folder, exist_ok=True)
    except FileNotFoundError as e:
        print(f"⚠️ Could not create log folder at '{log_folder}': {e}")
        fallback_folder = os.path.join(os.getcwd(), "logs")
        os.makedirs(fallback_folder, exist_ok=True)
        print(f"Using fallback log folder: {fallback_folder}")
        log_folder = fallback_folder

    print(f"Log folder: {log_folder}")
    print("Starting SOC Toolkit...")

    while True:
        show_main_menu()
        choice = input("Select a category: ").strip().lower()

        if choice == "q":
            print("Exiting SOC Toolkit. Goodbye!")
            write_action("Exited SOC Toolkit.", log_folder)
            break

        try:
            choice_num = int(choice)
            if 1 <= choice_num <= len(TOOL_CATEGORIES):
                category = list(TOOL_CATEGORIES.keys())[choice_num - 1]
            else:
                raise ValueError
        except ValueError:
            print(f"Invalid selection. Enter 1–{len(TOOL_CATEGORIES)} or Q to exit.")
            continue

        tools, package = show_tools_menu(category)
        tool_choice = input("Select a tool: ").strip()

        if tool_choice == "0":
            continue

        try:
            tool_num = int(tool_choice)
            if 1 <= tool_num <= len(tools):
                tool_name = tools[tool_num - 1]
                run_tool(package, tool_name, log_folder)
            else:
                raise ValueError
        except ValueError:
            print(f"Invalid tool selection. Enter 1–{len(tools)} or 0 to go back.")
            continue

if __name__ == "__main__":
    try:
        main()
    except (KeyboardInterrupt, EOFError):
        print("\nInterrupted. Exiting SOC Toolkit.")
        write_action("SOC Toolkit interrupted by user.", "logs")
