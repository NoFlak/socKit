import platform
import getpass
import socket
from logging_utils import write_action
from config import load_config
from command_utils import execute_command

config = load_config()
log_folder = config["log_folder"]
tested_devices = set()

def ping_test():
    target = input("Enter the target hostname or IP address for Ping Test: ").strip()
    user = getpass.getuser()
    # DNS resolution
    try:
        resolved_name = socket.gethostbyaddr(target)[0]
    except Exception:
        resolved_name = None
    try:
        resolved_ip = socket.gethostbyname(target)
    except Exception:
        resolved_ip = None

    # Info output
    if resolved_name:
        print(f"[INFO] DNS Name for {target}: {resolved_name}")
    if resolved_ip:
        print(f"[INFO] IP Address for {target}: {resolved_ip}")

    # Logging first test
    device_id = resolved_name or resolved_ip or target
    if device_id not in tested_devices:
        print(f"[INFO] First test on device: {device_id} by {user}")
        write_action(f"First test on device: {device_id} by {user}", log_folder)
        tested_devices.add(device_id)

    print(f"[INFO] Running Ping Test on {target} as {user}")
    write_action(f"Ping Test started on {target} by {user}", log_folder)
    os_name = platform.system()
    if os_name == "Windows":
        command = f"ping -n 4 {target}"
    else:
        command = f"ping -c 4 {target}"
    result = execute_command(command, f"Ping Test to {target}")
    if result:
        print(f"[SUCCESS] Ping Test to {target} completed.")
    else:
        print(f"[FAIL] Ping Test to {target} failed.")