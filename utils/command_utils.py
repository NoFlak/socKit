import subprocess
from concurrent.futures import ThreadPoolExecutor
from utils.logging_utils import write_action, log_tool_start, log_tool_end, log_error

# --- Execute Command (Synchronous) ---
def execute_command(command, description, log_folder, timeout=300):
    """Run a shell command synchronously with structured logging."""
    log_tool_start(description, log_folder)  # Log start
    try:
        # Run command and capture both stdout and stderr
        output = subprocess.check_output(
            command, shell=True, text=True, timeout=timeout, stderr=subprocess.STDOUT
        )
        print(output)  # Print output to console
        log_tool_end(description, log_folder)  # Log completion
        write_action(f"{description} completed successfully.", log_folder, detailed_results=output)
        return output
    except subprocess.CalledProcessError as e:
        # Log command failure
        log_error(description, e, log_folder)
        if "command not found" in str(e):
            print("Resolution: Ensure the required tool is installed and accessible in PATH.")
        return None
    except subprocess.TimeoutExpired as e:
        # Log timeout error
        log_error(description, f"Timeout after {timeout} seconds", log_folder)
        return None

# --- Execute Command (Asynchronous) ---
def execute_command_async(command, description, log_folder):
    """Run a shell command asynchronously using a thread pool."""
    with ThreadPoolExecutor() as executor:
        future = executor.submit(execute_command, command, description, log_folder)
        print(f"{description} is running in the background...")
        return future

# --- Safe Command Execution ---
def execute_command_safe(command, description, log_folder, timeout=300):
    """Execute a command and log errors without raising exceptions."""
    try:
        return execute_command(command, description, log_folder, timeout)
    except Exception as e:
        log_error(description, e, log_folder)
        return None

# --- Batch Command Execution ---
def command_summary(commands, log_folder):
    """Run a batch of commands with logging."""
    for description, command in commands.items():
        execute_command(command, description, log_folder)