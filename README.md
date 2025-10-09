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

- Unified CLI with interactive menu and scriptable workflows (playbooks)
- Structured logging pipeline (CSV + JSONL) with SIEM forwarding support
- Automated red/blue/purple task library providing actionable baselines
- Pluggable workflow engine for orchestrating multi-step incident workflows
- Strategy questionnaire to guide future enhancements and alignment
- Enhanced telemetry exports (Excel, Markdown reports, dashboards)
- Improved error handling, contextual logging, and configurable timeouts

---

## Modules

### Core Toolkit

- Logging utilities  
- Command execution helpers  
- Centralized menu and orchestration framework  

### Blue Team

- Shadow file hygiene baseline
- Active Directory export review and privilege auditing
- Local password risk detection
- Event log triage and network share auditing
- Patch posture, file integrity, backup verification, firewall status
- Malware persistence scanning, service/process inventory

### Red Team

- Guided Nmap scanning profiles
- Credential exposure simulation (registry/files)
- Lateral movement surface review
- Persistence and privilege escalation checks
- Phishing simulation template generator

### Purple Team

- Dashboard reporting from structured logs
- SIEM forwarding and correlation
- MITRE ATT&CK mapping via YAML definitions
- Threat intel lookups, automated reporting, alert simulation

---

## Installation

1. Clone the repository:

   ```bash
   git clone https://github.com/NoFlak/socKit.git
   cd socKit
   ```

2. Install dependencies:

   ```bash
   python -m pip install -r requirements.txt
   ```

3. *(Optional)* Enable the standalone GUI (requires Qt/PySide6):

   ```bash
   python -m pip install -r soc_gui/requirements.txt
   # launch with:
   python main.py --gui
   ```
   If the GUI dependencies are missing, the CLI launcher will fall back gracefully and remind you to install them.

## Usage

### Interactive mode

```bash
python main.py
```

Use the menu to run diagnostics, open red/blue/purple modules, launch playbooks,
or view the SOC strategy questionnaire.

Common CLI tasks:

| Command | Purpose |
| --- | --- |
| `python main.py --list-tasks` | Enumerate registered workflow tasks |
| `python main.py --playbook <path>` | Run a YAML playbook (add `--dry-run` to simulate) |
| `python main.py --manual [topic]` | Print inline instructions (`overview`, `gui`, `logging`, `playbooks`, `menus`, `artifact-store`) |
| `python main.py --gui` | Launch the optional PySide6 dashboard (after installing GUI deps) |

### Workflow automation

```bash
python main.py --list-tasks
python main.py --playbook playbooks/quick_health.yaml
python main.py --playbook playbooks/quick_health.yaml --dry-run
```

Add new playbooks under `playbooks/` to orchestrate bespoke incident response or
readiness checks. Registered task names are documented via `--list-tasks`.

## Documentation & Guides

- [docs/automenus.README.md](docs/automenus.README.md) – data-driven menus, generator usage, safeguards
- [docs/csv.README.md](docs/csv.README.md) – atomic CSV writer, shallow-copy behavior
- [docs/artifact_store_phase2.md](docs/artifact_store_phase2.md) – remote artifact store roadmap
- [docs/gui_setup.md](docs/gui_setup.md) – installing and configuring the optional GUI
- [Part1-README.md](Part1-README.md) / [Part2-README.md](Part2-README.md) – implementation notes and validation checklists
- [docs/update_status.md](docs/update_status.md) – branch status & release checklist

