from __future__ import annotations

import os
import json
from datetime import datetime

# Delegate to central logger for redaction, security, and retention
import logging_utils as core_logger  # type: ignore

# --- Log Headers (legacy)
TOOLKIT_LOG_HEADERS = "Timestamp, Level, Message"
INVESTIGATION_LOG_HEADERS = "Timestamp, Tool, Item, Status, Used_GB, Total_GB, Percent_Used, Issue"


def write_action(message, log_folder, log_file="ToolkitLog.csv", level="INFO", detailed_results=None, detailed_file="DetailedResults.txt"):
    return core_logger.write_action(
        message,
        log_folder,
        level=level,
        log_file=log_file,
        detailed_results=detailed_results,
        detailed_file=detailed_file,
    )


def log_tool_start(tool_name, log_folder):
    write_action(f"Starting {tool_name}...", log_folder, level="INFO")


def log_tool_end(tool_name, log_folder):
    write_action(f"{tool_name} completed successfully.", log_folder, level="INFO")


def log_error(tool_name, error, log_folder):
    write_action(f"{tool_name} failed: {error}", log_folder, level="ERROR", detailed_results=str(error))


def log_event(message, log_folder, level="INFO"):
    write_action(message, log_folder, level=level)


def log_to_file(message, file_path):
    try:
        with open(file_path, "a", encoding="utf-8") as f:
            f.write(f"{datetime.now()} - {message}\n")
    except Exception as e:
        print(f"Error writing to custom log: {e}")


def log_execution(func):
    def wrapper(*args, **kwargs):
        log_folder = kwargs.get('log_folder', '.')
        log_tool_start(func.__name__, log_folder)
        result = func(*args, **kwargs)
        log_tool_end(func.__name__, log_folder)
        return result
    return wrapper


def log_findings(findings, log_folder, log_file="InvestigationLog.csv"):
    path = os.path.join(log_folder, log_file)
    # Best-effort header write
    if not os.path.exists(path):
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(INVESTIGATION_LOG_HEADERS + "\n")
        except OSError:
            pass

    with open(path, "a", encoding="utf-8") as f:
        for result in findings:
            ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            metrics = result['metrics']
            line = (
                f"{ts}, {result['tool']}, {result['item']}, {result['status']}, "
                f"{metrics['used_gb']}, {metrics['total_gb']}, {metrics['percent_used']}, {result['issue']}\n"
            )
            f.write(line)
            print(line.strip())


def export_findings_json(findings, log_folder, filename="InvestigationLog.json"):
    path = os.path.join(log_folder, filename)
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(findings, f, indent=4)
        print(f"Findings exported to {filename}")
    except Exception as e:
        print(f"Error exporting JSON: {e}")
