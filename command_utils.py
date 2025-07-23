import subprocess
from concurrent.futures import ThreadPoolExecutor
from logging_utils import write_action
from config import load_config

config = load_config()
log_folder = config["log_folder"]

def execute_command(command, description, timeout=300):
    try:
        print(f"\nExecuting: {description} ...")
        output = subprocess.check_output(command, shell=True, text=True, timeout=timeout)
        print(output)
        write_action(f"{description} completed successfully.", log_folder, detailed_results=output)
        return output
    except subprocess.CalledProcessError as e:
        print(f"Error during {description}: {e}")
        write_action(f"Error during {description}: {e}", log_folder)
        if "command not found" in str(e):
            print(f"Resolution: Ensure the required tool is installed and accessible in PATH.")
        return None
    except subprocess.TimeoutExpired:
        print(f"Error: Command '{description}' timed out after {timeout} seconds.")
        write_action(f"Error: Command '{description}' timed out.", log_folder)
        return None

def execute_command_async(command, description):
    with ThreadPoolExecutor() as executor:
        future = executor.submit(execute_command, command, description)
        print(f"{description} is running in the background...")
        return future