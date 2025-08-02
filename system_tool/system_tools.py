import platform
import psutil
import shutil
import string
import os
import distro
import subprocess
from ctypes import windll
from datetime import datetime
from utils.command_utils import execute_command, execute_command_async
from utils.logging_utils import write_action, log_findings

# --- OS Profile Detection ---
def detect_os_profile():
    os_name = platform.system()
    if os_name == "Windows":
        return "Windows"
    elif os_name == "Linux":
        return "Linux"
    elif os_name == "Darwin":
        return "macOS"
    else:
        return "Unknown"

# --- Logging for Errors ---
def _log_error(tool_name, exception, log_folder):
    error_msg = f"{tool_name} encountered an error: {exception}"
    print(error_msg)
    write_action(error_msg, log_folder, level="ERROR")

# --- Run Command Sync with Logging and Enhanced Status Parsing ---
def _run_command_sync(command, tool_name, log_folder):
    try:
        write_action(f"Starting {tool_name}: {command}", log_folder, level="INFO")
        if isinstance(command, str):
            completed = subprocess.run(command, shell=True, capture_output=True, text=True, check=True)
        else:
            completed = subprocess.run(command, shell=False, capture_output=True, text=True, check=True)
        
        output = completed.stdout

        # Enhanced summaries for known tools:
        summary = ""
        if tool_name == "System File Checker":
            if "did not find any integrity violations" in output:
                summary = "SFC: No integrity violations found."
            elif "found corrupt files and successfully repaired them" in output:
                summary = "SFC: Corrupt files found and repaired successfully."
            elif "found corrupt files but was unable to fix some of them" in output:
                summary = "SFC: Found corrupt files but unable to fix some."
            else:
                summary = "SFC: Scan completed. Review full output for details."

        elif tool_name == "DISM Repair":
            if "The restore operation completed successfully" in output:
                summary = "DISM: Restore operation completed successfully."
            else:
                summary = "DISM: Completed. Review output for details."

        elif tool_name == "Disk Cleanup":
            # Usually minimal output, just note completion.
            summary = "Disk Cleanup: Command executed."

        if summary:
            print(summary)
            write_action(summary, log_folder, level="INFO")

        write_action(f"{tool_name} output:\n{output}", log_folder, level="INFO")
        return True, output

    except subprocess.CalledProcessError as e:
        write_action(f"{tool_name} failed with error:\n{e.stderr}", log_folder, level="ERROR")
        print(f"{tool_name} failed: {e.stderr.strip()}")
        return False, e.stderr

# --- Core System Repair Tools ---
def package_repair(log_folder):
    os_name = platform.system()
    if os_name == "Linux":
        dist = distro.id()
        if dist in ("ubuntu", "debian"):
            cmd = "sudo apt-get --fix-broken install -y"
        elif dist in ("fedora", "centos", "rhel"):
            cmd = "sudo dnf check --refresh"
        elif dist in ("arch", "manjaro"):
            cmd = "sudo pacman -Syu --noconfirm"
        else:
            msg = f"Package repair command not set for distro: {dist}"
            print(msg)
            write_action(msg, log_folder, level="ERROR")
            return False
    elif os_name == "Windows":
        cmd = "DISM /Online /Cleanup-Image /RestoreHealth"
    elif os_name == "Darwin":
        cmd = "brew doctor"
    else:
        msg = f"Package Repair not supported on {os_name}"
        print(msg)
        write_action(msg, log_folder, level="ERROR")
        return False

    success, output = _run_command_sync(cmd, "Package Repair", log_folder)
    if not success:
        print("Package Repair failed:", output)
        write_action("Package Repair failed", log_folder, level="ERROR", detailed_results=output)
    return success

def system_file_checker(log_folder):
    os_name = platform.system()
    if os_name == "Windows":
        success, output = _run_command_sync("sfc /scannow", "System File Checker", log_folder)
        if not success:
            write_action("SFC failed, running DISM...", log_folder, level="WARNING")
            print("SFC scan failed, running DISM Repair...")
            _run_command_sync("DISM /Online /Cleanup-Image /RestoreHealth", "DISM Repair", log_folder)
    else:
        commands = {
            "Linux": "fsck -n",
            "Darwin": "diskutil verifyVolume /"
        }
        cmd = commands.get(os_name)
        if cmd:
            _run_command_sync(cmd, "System File Checker", log_folder)
        else:
            msg = f"System File Checker not supported on {os_name}"
            print(msg)
            write_action(msg, log_folder, level="ERROR")

def disk_cleanup(log_folder):
    os_name = platform.system()
    commands = {
        "Windows": "cleanmgr /sagerun:1",
        "Linux": "sudo rm -rf /tmp/* /var/tmp/*",
        "Darwin": "sudo periodic daily"
    }
    cmd = commands.get(os_name)
    if cmd:
        _run_command_sync(cmd, "Disk Cleanup", log_folder)
    else:
        msg = f"Disk Cleanup not supported on {os_name}"
        print(msg)
        write_action(msg, log_folder, level="ERROR")

def network_reset(log_folder):
    os_name = platform.system()
    commands = {
        "Windows": "ipconfig /flushdns && netsh winsock reset",
        "Linux": "sudo systemctl restart NetworkManager",
        "Darwin": "sudo killall -HUP mDNSResponder"
    }
    cmd = commands.get(os_name)
    if cmd:
        _run_command_sync(cmd, "Network Reset", log_folder)
    else:
        msg = f"Network Reset not supported on {os_name}"
        print(msg)
        write_action(msg, log_folder, level="ERROR")

def scan_and_repair(log_folder):
    """
    Runs package repair, system file checker, and disk cleanup as a single repair operation.
    Package repair is run first because it can fix broken packages that SFC or disk cleanup might rely on.
    """
    print("\n=== Scan and Repair All ===")
    write_action("Starting Scan and Repair All", log_folder, level="INFO")

    try:
        # Run package repair first (fix broken packages)
        package_repair(log_folder)
        # Then system file check
        system_file_checker(log_folder)
        # Then disk cleanup last
        disk_cleanup(log_folder)
        write_action("Completed Scan and Repair All", log_folder, level="INFO")
        print("Scan and Repair completed.")
    except Exception as e:
        _log_error("Scan and Repair All", e, log_folder)
        print("Scan and Repair encountered an error.")

# --- Resource and Power Tools ---
def resource_monitor(log_folder):
    try:
        cpu = psutil.cpu_percent(interval=1)
        mem = psutil.virtual_memory().percent
        disk = psutil.disk_usage('/').percent
        status_msg = (
            "=== System Resource Snapshot ===\n"
            f"CPU Usage: {cpu}%\n"
            f"Memory Usage: {mem}%\n"
            f"Disk Usage: {disk}%\n"
            "================================"
        )
        print(status_msg)
        write_action("Resource Monitor snapshot", log_folder, level="INFO", detailed_results=status_msg)
    except Exception as e:
        _log_error("Resource Monitor", e, log_folder)

def gpu_usage_monitor(log_folder):
    os_name = platform.system()
    try:
        if os_name == "Windows":
            ps_cmd = [
                "powershell",
                "-Command",
                "Get-CimInstance Win32_VideoController | Select-Object Name, AdapterRAM, DriverVersion | Format-Table -AutoSize"
            ]
            result = subprocess.run(ps_cmd, capture_output=True, text=True)
            print("GPU Info:\n", result.stdout)
            write_action("GPU Usage Monitor executed.", log_folder, level="INFO")
        elif os_name == "Linux":
            result = subprocess.run(["lshw", "-C", "display"], capture_output=True, text=True)
            print("GPU Info:\n", result.stdout)
            write_action("GPU Usage Monitor executed.", log_folder, level="INFO")
        else:
            print("GPU usage monitor not supported on this OS.")
            write_action("GPU usage monitor unsupported OS", log_folder, level="ERROR")
    except Exception as e:
        _log_error("GPU Usage Monitor", e, log_folder)

def thermal_sensor_check(log_folder):
    os_name = platform.system()
    try:
        if os_name == "Linux":
            temps = psutil.sensors_temperatures()
            for name, entries in temps.items():
                print(f"{name}:")
                for entry in entries:
                    print(f"  {entry.label or name} - {entry.current} C")
            write_action("Thermal sensor check executed.", log_folder, level="INFO")
        elif os_name == "Windows":
            ps_cmd = [
                "powershell",
                "-Command",
                "Get-WmiObject MSAcpi_ThermalZoneTemperature -Namespace root/wmi | Select-Object CurrentTemperature | Format-Table -AutoSize"
            ]
            result = subprocess.run(ps_cmd, capture_output=True, text=True)
            print("Thermal Sensor Info:\n", result.stdout)
            write_action("Thermal sensor check executed.", log_folder, level="INFO")
        else:
            print("Thermal sensor check not supported on this OS.")
            write_action("Thermal sensor check unsupported OS", log_folder, level="ERROR")
    except Exception as e:
        _log_error("Thermal Sensor Check", e, log_folder)

def startup_program_auditor(log_folder):
    try:
        ps_cmd = [
            "powershell",
            "-Command",
            "Get-CimInstance Win32_StartupCommand | Format-Table -AutoSize"
        ]
        result = subprocess.run(ps_cmd, capture_output=True, text=True)
        print("Startup Programs:\n", result.stdout)
        write_action("Startup Program Auditor executed.", log_folder, level="INFO")
    except Exception as e:
        _log_error("Startup Program Auditor", e, log_folder)

def scheduled_task_auditor(log_folder):
    try:
        result = subprocess.run(["schtasks", "/query", "/fo", "LIST"], capture_output=True, text=True)
        print("Scheduled Tasks:\n", result.stdout)
        write_action("Scheduled Task Auditor executed.", log_folder, level="INFO")
    except Exception as e:
        _log_error("Scheduled Task Auditor", e, log_folder)

def power_settings_optimizer(log_folder):
    os_name = platform.system()
    commands = {
        "Windows": "powercfg /L",
        "Darwin": "pmset -g",
        "Linux": "cat /sys/class/power_supply/*/status"
    }
    cmd = commands.get(os_name)
    if cmd:
        _run_command_sync(cmd, "Power Settings Optimizer", log_folder)
    else:
        msg = f"Power Settings Optimizer not supported on {os_name}"
        print(msg)
        write_action(msg, log_folder, level="ERROR")

def show_menu():
    print("\n=== System Toolkit Menu ===")
    print("1. System File Checker")
    print("2. Disk Cleanup")
    print("3. Package Repair")
    print("4. Network Reset")
    print("5. Resource Monitor")
    print("6. Power Settings Optimizer")
    print("7. GPU Usage Monitor")
    print("8. Thermal Sensor Check")
    print("9. Startup Program Auditor")
    print("10. Scheduled Task Auditor")
    print("11. Scan and Repair All")
    print("Q. Exit")
    print("===========================\n")

def system_tools_menu(log_folder):
    while True:
        show_menu()
        choice = input("Select an option (1–11 or Q): ").strip().lower()
        if choice == "1":
            system_file_checker(log_folder)
        elif choice == "2":
            disk_cleanup(log_folder)
        elif choice == "3":
            package_repair(log_folder)
        elif choice == "4":
            network_reset(log_folder)
        elif choice == "5":
            resource_monitor(log_folder)
        elif choice == "6":
            power_settings_optimizer(log_folder)
        elif choice == "7":
            gpu_usage_monitor(log_folder)
        elif choice == "8":
            thermal_sensor_check(log_folder)
        elif choice == "9":
            startup_program_auditor(log_folder)
        elif choice == "10":
            scheduled_task_auditor(log_folder)
        elif choice == "11":
            scan_and_repair(log_folder)
        elif choice in ["q", "quit", "exit"]:
            print("Exiting system toolkit.")
            write_action("Exited System Toolkit menu", log_folder, level="INFO")
            break
        else:
            print("Invalid choice. Please select a valid option.")
            write_action(f"Invalid menu choice: {choice}", log_folder, level="WARNING")

# --- Entry Point ---
def run(log_folder):
    system_tools_menu(log_folder)

def main():
    log_folder = os.path.join(os.getcwd(), "logs")
    os.makedirs(log_folder, exist_ok=True)
    print(f"Detected OS Profile: {detect_os_profile()}")
    system_tools_menu(log_folder)

if __name__ == "__main__":
    main()
