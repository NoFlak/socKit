"""Purple team collaboration and analytics helpers."""

from __future__ import annotations

import csv
import json
import os
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple

import matplotlib.pyplot as plt
import pandas as pd
import requests
import yaml

from config import load_config
from logging_utils import log_table, write_action

config = load_config()
log_folder = config.log_folder


def _load_log_dataframe() -> pd.DataFrame:
    log_file_path = Path(log_folder) / "ToolkitLog.csv"
    if not log_file_path.exists():
        raise FileNotFoundError(f"Log file {log_file_path} not found. Run a workflow first.")
    return pd.read_csv(log_file_path)


def dashboard_report() -> None:
    """Generate summary charts from the consolidated toolkit logs."""

    try:
        df = _load_log_dataframe()
    except Exception as exc:
        print(f"Error loading logs: {exc}")
        write_action("Dashboard report failed.", level="ERROR", context={"error": str(exc)})
        return

    if df.empty:
        print("No log data available.")
        return

    message_counts = df["message"].value_counts()
    plt.figure(figsize=(10, 6))
    message_counts.plot(kind="bar", color="skyblue")
    plt.title("Log Message Counts")
    plt.xlabel("Message")
    plt.ylabel("Count")
    plt.tight_layout()
    output_pdf = Path(log_folder) / "DashboardReport.pdf"
    plt.savefig(output_pdf)
    plt.close()

    output_excel = Path(log_folder) / "ToolkitLog.xlsx"
    df.to_excel(output_excel, index=False)
    print(f"Dashboard report saved to {output_pdf} and {output_excel}.")
    write_action("Dashboard report generated.", context={"log_entries": len(df)})


def forward_logs_to_siem() -> None:
    """Forward logs to an external SIEM system via HTTP API."""

    log_file_path = Path(log_folder) / "ToolkitLog.jsonl"
    if not log_file_path.exists():
        print("Structured log file not found. Run some actions first.")
        write_action("SIEM forward skipped: no log file.", level="WARNING")
        return

    siem_url = input("Enter the SIEM API endpoint URL: ").strip()
    if not siem_url:
        print("No URL provided.")
        return

    try:
        with log_file_path.open("r", encoding="utf-8") as handle:
            payload = handle.read()
        response = requests.post(siem_url, data={"logs": payload}, timeout=30)
        if response.status_code == 200:
            print("Logs successfully forwarded to SIEM.")
            write_action("Logs forwarded to SIEM.", context={"url": siem_url})
        else:
            print(f"Failed to forward logs. Status code: {response.status_code}")
            write_action(
                "SIEM forward failed.",
                level="ERROR",
                context={"status": response.status_code, "url": siem_url},
                detailed_results=response.text,
            )
    except requests.RequestException as exc:
        print(f"Error forwarding logs to SIEM: {exc}")
        write_action("SIEM forward exception.", level="ERROR", context={"error": str(exc)})


def log_correlation_engine() -> None:
    """Perform basic correlation on the toolkit JSON logs."""

    log_path = Path(log_folder) / "ToolkitLog.jsonl"
    if not log_path.exists():
        print("JSON log file missing. Run some actions first.")
        return

    correlations: Dict[str, List[str]] = defaultdict(list)
    try:
        with log_path.open("r", encoding="utf-8") as handle:
            for line in handle:
                entry = json.loads(line)
                message = entry.get("message", "unknown")
                level = entry.get("level", "INFO")
                context = entry.get("context", {})
                key = context.get("target") or context.get("user") or message
                correlations[key].append(level)

        correlated = []
        for key, levels in correlations.items():
            severity_mix = Counter(levels)
            if severity_mix.get("ERROR") or severity_mix.get("WARNING"):
                correlated.append((key, dict(severity_mix)))

        for key, mix in correlated:
            print(f"Correlation for {key}: {mix}")

        log_table("log_correlation", ("key", "severity_mix"), ((k, json.dumps(v)) for k, v in correlated))
        write_action("Log correlation completed.", context={"entities": len(correlated)})
    except (OSError, json.JSONDecodeError) as exc:
        print(f"Failed to run correlation: {exc}")
        write_action("Log correlation failed.", level="ERROR", context={"error": str(exc)})


def mitre_attack_mapping() -> None:
    """Map correlated events to MITRE ATT&CK tactics using a YAML mapping."""

    mapping_file = Path(config.playbooks_folder) / "mitre_mapping.yaml"
    if not mapping_file.exists():
        print(f"Mapping file {mapping_file} missing. Creating a starter template.")
        sample_mapping = {
            "ping test completed": {"tactic": "Discovery", "technique": "Active Scanning"},
            "credential exposure simulation complete.": {"tactic": "Credential Access", "technique": "OS Credential Dumping"},
        }
        with mapping_file.open("w", encoding="utf-8") as handle:
            yaml.safe_dump(sample_mapping, handle)
        print(f"Starter mapping created at {mapping_file}. Edit and re-run.")
        return

    try:
        with mapping_file.open("r", encoding="utf-8") as handle:
            mapping = yaml.safe_load(handle) or {}
    except yaml.YAMLError as exc:
        print(f"Error reading mapping file: {exc}")
        write_action("MITRE mapping load failed.", level="ERROR", context={"error": str(exc)})
        return

    df = _load_log_dataframe()
    matches = []
    for _, row in df.iterrows():
        message = row.get("message", "")
        if message in mapping:
            entry = mapping[message]
            matches.append((message, entry.get("tactic"), entry.get("technique")))

    if not matches:
        print("No MITRE mappings triggered. Update the YAML mapping to include more events.")
    else:
        print("\nMITRE ATT&CK Matches:")
        for message, tactic, technique in matches:
            print(f" - {message}: {tactic} / {technique}")

    log_table("mitre_mapping", ("message", "tactic", "technique"), matches)
    write_action("MITRE ATT&CK mapping complete.", context={"matches": len(matches)})


def threat_intel_lookup() -> None:
    """Look up IoCs in a user-provided CSV against threat intel API."""

    csv_path = Path(input("Enter path to IoC CSV: ").strip() or "iocs.csv")
    if not csv_path.exists():
        print(f"[WARN] IoC file {csv_path} not found.")
        return

    api_url = input("Enter threat intel API URL (supports GET with ?ioc=): ").strip()
    if not api_url:
        print("No API URL provided.")
        return

    results = []
    try:
        with csv_path.open("r", encoding="utf-8", errors="ignore") as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                indicator = row.get("indicator") or row.get("ioc")
                if not indicator:
                    continue
                response = requests.get(api_url, params={"ioc": indicator}, timeout=20)
                verdict = response.json().get("verdict", "unknown") if response.ok else "error"
                print(f"{indicator}: {verdict}")
                results.append((indicator, verdict))
    except (OSError, requests.RequestException, ValueError) as exc:
        print(f"Threat intel lookup failed: {exc}")
        write_action("Threat intel lookup failed.", level="ERROR", context={"error": str(exc)})
        return

    log_table("threat_intel_results", ("indicator", "verdict"), results)
    write_action("Threat intel lookup complete.", context={"indicators": len(results)})


def automated_report_generator() -> None:
    """Compile a markdown report summarizing recent activity."""

    report_path = Path(config.artifacts_folder) / "automation_report.md"
    df = _load_log_dataframe()
    recent = df.tail(50)
    content = ["# SOC Automation Summary", "", f"Generated: {datetime.utcnow().isoformat()}Z", ""]
    for _, row in recent.iterrows():
        content.append(f"- **{row['timestamp']}** [{row['level']}] {row['message']}")
    report_path.write_text("\n".join(content), encoding="utf-8")
    print(f"Report saved to {report_path}")
    write_action("Automated report generated.", context={"entries": len(recent)})


def alert_simulation() -> None:
    """Generate synthetic alerts for testing pipelines."""

    alert_count = int(input("How many simulated alerts? ").strip() or "5")
    severities = ["LOW", "MEDIUM", "HIGH"]
    alerts = []
    for idx in range(alert_count):
        severity = severities[idx % len(severities)]
        message = f"Simulated alert {idx + 1} severity {severity}"
        alerts.append((severity, message))
        write_action("Simulated alert generated.", context={"severity": severity, "message": message})
        print(message)

    log_table("simulated_alerts", ("severity", "message"), alerts)


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