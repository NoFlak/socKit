import subprocess
from utils.logging_utils import write_action

def check_tool_availability(tool_name, install_instructions, log_folder=None):
    try:
        subprocess.run([tool_name, "--version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        msg = f"Tool '{tool_name}' is available."
        print(msg)
        if log_folder:
            write_action(msg, log_folder)
        return True
    except FileNotFoundError:
        msg = f"Error: Tool '{tool_name}' is not installed or not in PATH.\nResolution: {install_instructions}"
        print(msg)
        if log_folder:
            write_action(msg, log_folder)
        return False
    except subprocess.CalledProcessError:
        msg = f"Tool '{tool_name}' is installed but may not be functioning correctly."
        print(msg)
        if log_folder:
            write_action(msg, log_folder)
        return False

def check_required_tools(log_folder=None):
    tools = {
        "nmap": "Install via 'sudo apt install nmap' (Linux) or download from https://nmap.org/download.html (Windows/macOS).",
        "smartctl": "Install via 'sudo apt install smartmontools' (Linux).",
        "msfconsole": "Install via 'sudo apt install metasploit-framework' (Linux) or download from https://www.metasploit.com/ (Windows/macOS).",
        "traceroute": "Install via 'sudo apt install traceroute' (Linux) or ensure it is available on macOS.",
    }
    print("\nChecking required tools...")
    if log_folder:
        write_action("Checking required external tools.", log_folder)

    for tool, instructions in tools.items():
        check_tool_availability(tool, instructions, log_folder)

def initialize_environment(log_folder=None):
    print("Initializing environment...")
    if log_folder:
        write_action("Initializing environment setup.", log_folder)
    check_required_tools(log_folder)
    print("Environment check complete.")