import platform
from command_utils import execute_command_async

def system_file_checker():
    os_name = platform.system()
    if os_name == "Windows":
        command = "sfc /scannow"
    elif os_name == "Linux":
        command = "fsck -n"
    elif os_name == "Darwin":
        command = "diskutil verifyVolume /"
    else:
        print("System File Checker is not supported on this OS.")
        return
    print("System File Checker may take several minutes to complete. Please wait...")
    execute_command_async(command, "System File Checker")