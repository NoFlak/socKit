import platform
import getpass
import socket
import subprocess
import os

from utils.logging_utils import write_action
from utils.config import load_config
from utils.command_utils import execute_command

config = load_config()
log_folder = getattr(config, "log_folder", getattr(config, "get", lambda *_: "logs")("log_folder", "logs"))
tested_devices = set()


def ping_test(target=None):
    """
    Perform a ping test to the specified target hostname or IP.
    If no target provided, prompts user for input.
    Logs results and prints output.
    """
    if not target:
        target = input("Enter the target hostname or IP address for Ping Test: ").strip()
    if not target:
        print("[ERROR] No target specified. Aborting ping test.")
        return

    user = getpass.getuser()

    # DNS resolution
    resolved_name = None
    resolved_ip = None
    try:
        resolved_name = socket.gethostbyaddr(target)[0]
    except Exception:
        pass
    try:
        resolved_ip = socket.gethostbyname(target)
    except Exception:
        pass

    # Info output
    if resolved_name:
        print(f"[INFO] DNS Name for {target}: {resolved_name}")
    if resolved_ip:
        print(f"[INFO] IP Address for {target}: {resolved_ip}")

    # Logging first test for device
    device_id = resolved_name or resolved_ip or target
    if device_id not in tested_devices:
        print(f"[INFO] First test on device: {device_id} by user: {user}")
        write_action(f"First test on device: {device_id} by user: {user}", log_folder)
        tested_devices.add(device_id)

    print(f"[INFO] Running Ping Test on {target} as {user}...")

    os_name = platform.system()
    if os_name == "Windows":
        cmd = ["ping", "-n", "4", target]
    else:
        cmd = ["ping", "-c", "4", target]

    # Use execute_command helper, or fallback to subprocess if not available
    result = execute_command(" ".join(cmd), f"Ping Test to {target}", log_folder)
    if not result:
        # If execute_command returns False, fallback to subprocess to get output
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, check=True)
            print(proc.stdout)
            write_action(f"Ping Test to {target} output:\n{proc.stdout}", log_folder)
            print(f"[SUCCESS] Ping Test to {target} completed.")
        except subprocess.CalledProcessError as e:
            print(f"[FAIL] Ping Test to {target} failed:\n{e.stderr}")
            write_action(f"Ping Test to {target} failed:\n{e.stderr}", log_folder, level="ERROR")
    else:
        print(f"[SUCCESS] Ping Test to {target} completed.")


def traceroute_test(target="8.8.8.8"):
    """
    Performs a traceroute to the specified target IP or hostname.
    Supports Windows (tracert), Linux and macOS (traceroute).
    """
    if not target:
        print("[ERROR] No target specified for traceroute.")
        return

    os_name = platform.system()
    if os_name == "Windows":
        cmd = ["tracert", target]
    elif os_name in ("Linux", "Darwin"):  # Darwin is macOS
        cmd = ["traceroute", target]
    else:
        print(f"[ERROR] Traceroute not supported on OS: {os_name}.")
        return

    print(f"[INFO] Running traceroute to {target}...\n")

    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, check=True)
        print(proc.stdout)
        write_action(f"Traceroute to {target} output:\n{proc.stdout}", log_folder)
    except subprocess.CalledProcessError as e:
        print(f"[FAIL] Traceroute command failed with error:\n{e.stderr}")
        write_action(f"Traceroute command to {target} failed:\n{e.stderr}", log_folder, level="ERROR")
    except FileNotFoundError:
        print("[ERROR] Traceroute tool not found. Please ensure it is installed and in your PATH.")
        write_action("Traceroute tool not found.", log_folder, level="ERROR")


def main_menu():
    """
    Interactive menu for network tools.
    """
    while True:
        print("\n=== Network Tools Menu ===")
        print("1) Ping Test")
        print("2) Traceroute Test")
        print("Q) Quit")

        choice = input("Select an option: ").strip().upper()
        if choice == "1":
            ping_test()
        elif choice == "2":
            target = input("Enter target hostname or IP for traceroute (default 8.8.8.8): ").strip() or "8.8.8.8"
            traceroute_test(target)
        elif choice == "Q":
            print("Exiting Network Tools.")
            break
        else:
            print("Invalid choice, please try again.")


if __name__ == "__main__":
    main_menu()
