import os
import platform
from logging_utils import write_action
from command_utils import execute_command

def create_directory(path):
    try:
        if not os.path.exists(path):
            os.makedirs(path)
            print(f"Directory created at {path}")
        else:
            print(f"Directory already exists at {path}")
    except OSError as e:
        print(f"Error creating directory at {path}: {e}")
        write_action(f"Error creating directory at {path}: {e}")

def list_directory_contents():
    try:
        contents = os.listdir(".")
        print("\n=== Directory Contents ===")
        for item in contents:
            print(item)
        write_action("Directory contents listed.")
    except Exception as e:
        print(f"Error listing directory contents: {e}")

def display_ip_configuration():
    os_name = platform.system()
    if os_name == "Windows":
        command = "ipconfig"
    else:
        command = "ifconfig"
    execute_command(command, "IP Configuration")

def display_mac_addresses():
    os_name = platform.system()
    if os_name == "Windows":
        command = "getmac"
    else:
        command = "ifconfig | grep ether"
    execute_command(command, "MAC Address Information")

def display_user_information():
    try:
        print(f"User Name: {os.getenv('USERNAME') or os.getenv('USER')}")
        print(f"User Domain: {os.getenv('USERDOMAIN') or 'N/A'}")
        print(f"Computer Name: {os.getenv('COMPUTERNAME') or platform.node()}")
        write_action("Displayed user information.")
    except Exception as e:
        print(f"Error displaying user information: {e}")
        write_action(f"Error displaying user information: {e}")