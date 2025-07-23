import os
import pandas as pd
import matplotlib.pyplot as plt
import requests
from logging_utils import write_action
from config import load_config

config = load_config()
log_folder = config["log_folder"]

def dashboard_report():
    """
    Generate a dashboard report from logs and export to PDF or Excel.
    """
    log_file_path = os.path.join(log_folder, "ToolkitLog.csv")
    try:
        logs = pd.read_csv(log_file_path, names=["Timestamp", "Message"])
        print("\n=== Aggregated Toolkit Logs ===")
        print(logs)
        log_counts = logs["Message"].value_counts()
        log_counts.plot(kind="bar", figsize=(10, 6), color="skyblue")
        plt.title("Log Message Counts")
        plt.xlabel("Message")
        plt.ylabel("Count")
        plt.tight_layout()
        plt.savefig(os.path.join(log_folder, "DashboardReport.pdf"))
        print(f"Dashboard report saved as PDF in {log_folder}.")
        logs.to_excel(os.path.join(log_folder, "ToolkitLog.xlsx"), index=False)
        print(f"Logs exported to Excel in {log_folder}.")
    except Exception as e:
        print(f"Error generating dashboard report: {e}")
        write_action(f"Error generating dashboard report: {e}", log_folder)

def forward_logs_to_siem():
    """
    Forward logs to an external SIEM system via HTTP API.
    """
    log_file_path = os.path.join(log_folder, "ToolkitLog.csv")
    siem_url = input("Enter the SIEM API endpoint URL: ").strip()
    try:
        with open(log_file_path, "r") as f:
            logs = f.read()
        response = requests.post(siem_url, data={"logs": logs})
        if response.status_code == 200:
            print("Logs successfully forwarded to SIEM.")
            write_action("Logs forwarded to SIEM.", log_folder)
        else:
            print(f"Failed to forward logs. Status code: {response.status_code}")
            write_action(f"Failed to forward logs. Status code: {response.status_code}", log_folder)
    except Exception as e:
        print(f"Error forwarding logs to SIEM: {e}")
        write_action(f"Error forwarding logs to SIEM: {e}", log_folder)

def log_correlation_engine():
    print("[PLACEHOLDER] Log correlation engine not yet implemented.")

def mitre_attack_mapping():
    print("[PLACEHOLDER] MITRE ATT&CK mapping not yet implemented.")

def threat_intel_lookup():
    print("[PLACEHOLDER] Threat intelligence lookup not yet implemented.")

def automated_report_generator():
    print("[PLACEHOLDER] Automated report generator not yet implemented.")

def alert_simulation():
    print("[PLACEHOLDER] Alert simulation not yet implemented.")


def purple_team_menu():
    while True:
        print("\n==== Purple Team Tools ====")
        print("1. Dashboard Report")
        print("2. Forward Logs to SIEM")
        print("3. Log Correlation Engine")
        print("4. MITRE ATT&CK Mapping")
        print("5. Threat Intelligence Lookup")
        print("6. Automated Report Generator")
        print("7. Alert Simulation")
        print("Q. Back")
        choice = input("Select an option: ").strip().upper()
        if choice == "1":
            dashboard_report()
        elif choice == "2":
            forward_logs_to_siem()
        elif choice == "3":
            log_correlation_engine()
        elif choice == "4":
            mitre_attack_mapping()
        elif choice == "5":
            threat_intel_lookup()
        elif choice == "6":
            automated_report_generator()
        elif choice == "7":
            alert_simulation()
        elif choice == "Q":
            break
        else:
            print("Invalid selection.")