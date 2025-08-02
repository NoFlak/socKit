import os
import json
from datetime import datetime

# --- Log Headers ---
# CSV headers for toolkit and investigation logs
TOOLKIT_LOG_HEADERS = "Timestamp, Level, Message"
INVESTIGATION_LOG_HEADERS = "Timestamp, Tool, Item, Status, Used_GB, Total_GB, Percent_Used, Issue"

# --- Log Rotation ---
def rotate_log_if_needed(file_path, max_size_mb=5):
    """Rotate log file if it exceeds max_size_mb."""
    # Check if file exists and exceeds size threshold
    if os.path.exists(file_path) and os.path.getsize(file_path) > max_size_mb * 1024 * 1024:
        # Rename old file with timestamp suffix
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        rotated_path = f"{file_path}.{timestamp}.bak"
        os.rename(file_path, rotated_path)

# --- Main Action Logger ---
def write_action(message, log_folder, log_file="ToolkitLog.csv", level="INFO", detailed_results=None, detailed_file="DetailedResults.txt"):
    """Write a timestamped log entry and optional detailed results."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_file_path = os.path.join(log_folder, log_file)
    detailed_file_path = os.path.join(log_folder, detailed_file)

    # Rotate log if needed
    rotate_log_if_needed(log_file_path)

    # Write CSV headers if file is new
    if not os.path.exists(log_file_path):
        with open(log_file_path, "w") as f:
            f.write(TOOLKIT_LOG_HEADERS + "\n")

    try:
        # Write main log entry
        with open(log_file_path, "a") as f:
            f.write(f"{timestamp}, {level}, {message}\n")
        # Write detailed results if provided
        if detailed_results:
            with open(detailed_file_path, "a") as f:
                f.write(f"\n{timestamp} [{level}]\n{detailed_results}\n")
    except OSError as e:
        print(f"Error writing log: {e}")

# --- Lifecycle Logging Wrappers ---
def log_tool_start(tool_name, log_folder):
    """Log the start of a tool or command."""
    write_action(f"Starting {tool_name}...", log_folder, level="INFO")

def log_tool_end(tool_name, log_folder):
    """Log the successful completion of a tool or command."""
    write_action(f"{tool_name} completed successfully.", log_folder, level="INFO")

def log_error(tool_name, error, log_folder):
    """Log an error with context."""
    write_action(f"{tool_name} failed: {error}", log_folder, level="ERROR", detailed_results=str(error))

# --- General Event Logger ---
def log_event(message, log_folder, level="INFO"):
    """Log a general event without detailed output."""
    write_action(message, log_folder, level=level)

# --- Custom File Logger ---
def log_to_file(message, file_path):
    """Write a raw message to a custom log file."""
    try:
        with open(file_path, "a") as f:
            f.write(f"{datetime.now()} - {message}\n")
    except Exception as e:
        print(f"Error writing to custom log: {e}")

# --- Function Execution Decorator ---
def log_execution(func):
    """Decorator to log start and end of a function."""
    def wrapper(*args, **kwargs):
        log_folder = kwargs.get('log_folder', '.')
        log_tool_start(func.__name__, log_folder)
        result = func(*args, **kwargs)
        log_tool_end(func.__name__, log_folder)
        return result
    return wrapper

# --- Investigation Findings Logger ---
def log_findings(findings, log_folder, log_file="InvestigationLog.csv"):
    """Log structured findings from disk or system analysis."""
    path = os.path.join(log_folder, log_file)

    # Rotate log if needed
    rotate_log_if_needed(path)

    # Write CSV headers if file is new
    if not os.path.exists(path):
        with open(path, "w") as f:
            f.write(INVESTIGATION_LOG_HEADERS + "\n")

    # Write each finding as a CSV row
    with open(path, "a") as f:
        for result in findings:
            ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            metrics = result['metrics']
            line = (
                f"{ts}, {result['tool']}, {result['item']}, {result['status']}, "
                f"{metrics['used_gb']}, {metrics['total_gb']}, {metrics['percent_used']}, {result['issue']}\n"
            )
            f.write(line)
            print(line.strip())

# --- Optional JSON Export ---
def export_findings_json(findings, log_folder, filename="InvestigationLog.json"):
    """Export findings to a JSON file for external integration."""
    path = os.path.join(log_folder, filename)
    try:
        with open(path, "w") as f:
            json.dump(findings, f, indent=4)
        print(f"Findings exported to {filename}")
    except Exception as e:
        print(f"Error exporting JSON: {e}")
