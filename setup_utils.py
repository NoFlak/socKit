import subprocess

def check_tool_availability(tool_name, install_instructions):
    try:
        subprocess.run([tool_name, "--version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        print(f"Tool '{tool_name}' is available.")
        return True
    except FileNotFoundError:
        print(f"Error: Tool '{tool_name}' is not installed or not in PATH.")
        print(f"Resolution: {install_instructions}")
        return False
    except subprocess.CalledProcessError:
        print(f"Tool '{tool_name}' is installed but may not be functioning correctly.")
        return False

def check_required_tools():
    tools = {
        "nmap": "Install via 'sudo apt install nmap' (Linux) or download from https://nmap.org/download.html (Windows/macOS).",
        "smartctl": "Install via 'sudo apt install smartmontools' (Linux).",
        "msfconsole": "Install via 'sudo apt install metasploit-framework' (Linux) or download from https://www.metasploit.com/ (Windows/macOS).",
        "traceroute": "Install via 'sudo apt install traceroute' (Linux) or ensure it is available on macOS.",
    }
    print("\nChecking required tools...")
    for tool, instructions in tools.items():
        check_tool_availability(tool, instructions)