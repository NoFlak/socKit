# socKit — Cross-Platform SOC Toolkit

**socKit** is an extensible, cross-platform Security Operations Center (SOC) toolkit designed to provide a wide range of defensive and offensive security utilities for cybersecurity professionals. The toolkit supports Blue Team, Red Team, and Purple Team workflows, featuring core foundational tools, malware scanning, network auditing, incident investigation, and more.

---

## Table of Contents

- [Overview](#overview)  
- [Features](#features)  
- [Modules](#modules)  
- [Installation](#installation)  
- [Usage](#usage)  
- [Contributing](#contributing)  
- [License](#license)  

---

## Overview

socKit aims to deliver a modular, open-source SOC toolkit supporting:

- **Blue Team:** Audit Active Directory, monitor event logs, detect malware persistence, check patch compliance, and validate content authenticity.  
- **Red Team:** Tools for penetration testing, privilege escalation, reconnaissance, and exploitation.  
- **Purple Team:** Integration tools and workflows to improve collaboration between Red and Blue teams.  
- **Core Utilities:** Logging, SIEM integration, system info collection, and centralized tool orchestration.

Dev note: July 23 2025
It is built for portability and can be run on Windows, Linux, and macOS environments with minimal dependencies.
It is also a side project while I am studying cyber security engineering to familiarize myself with tools used in the industry and simplify their usability for myself.
I had an older version with some tools built out already but lost some of it after a failed git merge attempt... mostly summed up as user error and no recent backup putting us where we are now.

---

## Features

- Interactive CLI menus for easy tool selection  
- Active Directory auditing and user privilege enumeration  
- File integrity monitoring and spoofed file detection  
- Malware persistence scanning across multiple vectors  
- Event log analysis and network share auditing  
- Patch compliance and firewall/AV status checking  
- Modular design for adding new capabilities rapidly  
- Logging and SIEM-ready output formatting  

---

## Modules

### Core Toolkit

- Logging utilities  
- Command execution helpers  
- Centralized menu and orchestration framework  

### Blue Team

- Shadow Copy & Alternate Data Auditor  
- AD Password Policy Audit  
- AD User Privilege Audit  
- Local Password Policy Audit  
- Windows Event Log Analyzer  
- Network Share Access Auditor  
- Patch Compliance Checker  
- File Integrity Monitor  
- Service & Process Monitor  
- Backup Integrity Verifier  
- User Session Auditor  
- Firewall & Antivirus Status Checker  
- Malware Persistence Scanner  
- File Type Spoofing Detector  

### Red Team (in development)

- Network reconnaissance  
- Privilege escalation helpers  
- Payload generation  

### Purple Team (planned)

- Incident simulation and detection tuning  
- Alert correlation and reporting  

---

## Installation

1. Clone the repository:

git clone https://github.com/NoFlak/socKit.git
cd socKit

2. Install dependencies:
   pip install -r requirements.txt

3.Run the main interface or call specific modules:

python main_menu.py,
or for example, 
call python malware_scanner.py from terminal directly it might not get logging you want from direct call of specific tools until I add the enhanced logging in better.
__________________________________________________
# Malware Persistence & Execution Tracker (MPET) #
-------------------------------------------------

A Python tool to assist Blue Teams during Windows endpoint audits by detecting
persistence mechanisms used by malware or attackers.

## Features
- Scans common registry autostart locations (`Run`, `RunOnce`, services)
- Inspects startup folder executables (user and all users)
- Enumerates suspicious scheduled tasks
- Analyzes Windows Prefetch files for suspicious executions
- Parses PowerShell Operational Event Log for suspicious script executions
- Outputs detailed logs to console and log file (timestamped or custom path)
- Requires Administrator privileges to run

## Requirements
- Python 3.x (tested with 3.11)
- Windows OS (requires Windows APIs for admin check and system paths)
- No external dependencies

## Usage

Run interactively from command line:

```bash
python mpet_scan.py [--log path_to_logfile.txt]
