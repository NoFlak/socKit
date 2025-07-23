import os
from datetime import datetime

def write_action(message, log_folder, log_file="ToolkitLog.csv", detailed_results=None, detailed_file="DetailedResults.txt"):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_file_path = os.path.join(log_folder, log_file)
    detailed_file_path = os.path.join(log_folder, detailed_file)
    try:
        with open(log_file_path, "a") as f:
            f.write(f"{timestamp}, {message}\n")
        if detailed_results:
            with open(detailed_file_path, "a") as f:
                f.write(f"\n{timestamp}\n{detailed_results}\n")
    except OSError as e:
        print(f"Error writing log: {e}")