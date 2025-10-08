# socKit Codebase Overview and Recommendations

> _Note: Grammar and formatting were minimally assisted by AI._

## High-Level Purpose
socKit is a cross-platform Security Operations Center (SOC) toolkit intended to bundle blue-, red-, and purple-team utilities into a single command-line interface. The entry point `main.py` initializes configuration (log location, timeouts, default scan profile) and exposes menus to drive system diagnostics, network diagnostics, and team-specific tool suites.

## Module Breakdown

### Configuration and Logging
- `config.py` provides `load_config()` to read configuration from `config.json`, falling back to defaults (log folder, timeout, default scan type).
- `logging_utils.py` implements `write_action()` for CSV log aggregation and optional detailed result storage. Many modules call this to centralize audit trails.

### Core Utilities
- `utils.py` offers helper functions to create directories, enumerate directory contents, and show system/network identity information. These primarily wrap OS commands via `execute_command()` from `command_utils.py`.
- `command_utils.py` provides synchronous and asynchronous command execution helpers with standard logging, using `subprocess` and optional thread pooling.
- `system_tools.py` defines `system_file_checker()` that chooses the appropriate OS-level integrity command (`sfc`, `fsck`, or `diskutil`) and runs it asynchronously.
- `network_tools.py` exposes `ping_test()`, a ping workflow that resolves hostnames, logs first-time tests, and invokes the correct ping syntax per platform.

### Team Menus
- `blue_team.py` houses menu-driven defensive tools. Currently only `ad_user_privileges()` is implemented using `ldap3` to query Active Directory and enumerate group memberships. All other menu entries print placeholder notices.
- `red_team.py` includes the red-team menu. The implemented capability is `vulnerability_scan()`, which wraps `nmap` with selectable scan profiles. The rest are placeholders describing planned functionality.
- `purple_team.py` implements collaborative workflows: `dashboard_report()` generates simple charts and exports, and `forward_logs_to_siem()` posts log data to a user-specified endpoint. Additional purple-team ideas remain placeholders.

### Specialized Tooling
- `malware_scanner.py` defines `MalwareRegistryScanner`, a Windows-centric persistence auditor that scans autorun registry keys and scheduled tasks for suspicious entries. The Blue Team menu exposes this under "Malware Persistence Scan".

## Usage Workflow
1. Install dependencies from `requirements.txt` (notably `ldap3`, `pandas`, `matplotlib`, `requests`).
2. Run `python main.py` to start the interactive CLI.
3. Navigate the menus to execute diagnostics or team tools. Outputs are logged to the configured `log_folder` and printed to the terminal. Some tools (Active Directory audit, malware persistence scan) require platform-specific prerequisites and may need elevated permissions.
4. Individual modules such as `malware_scanner.py` can also be invoked directly for targeted tasks.

## Implementation Gaps and Suggested Enhancements
The codebase contains numerous placeholders that indicate planned functionality. Below are prioritized recommendations:

1. **Robust Configuration and Path Handling**
   - Ensure `log_folder` defaults to a cross-platform path or allow overriding via environment variable/CLI flag. Currently it points to a Windows drive by default.
   - Validate configuration file structure and provide schema or sample config in the repository.

2. **Blue Team Implementations**
   - Flesh out placeholder functions (e.g., `shadow_file_management`, `event_log_analyzer`, `patch_status_checker`) with modular helpers so they can be unit-tested. Consider using PowerShell or OS APIs for Windows-specific tasks and fallback logic for Linux/macOS.
   - Refactor the menu logic to keep imports (`MalwareRegistryScanner`) at the top of the file, and tidy the indentation issues in the menu to avoid runtime errors.

3. **Red Team Feature Development**
   - Implement safe simulations or guidance for credential dumping and lateral movement, ensuring clear warnings about dual-use implications.
   - Add error handling for missing tools (e.g., `nmap`) and provide setup instructions in the README.

4. **Purple Team Collaboration Tools**
   - Expand `log_correlation_engine` and `mitre_attack_mapping` with basic rule matching and ATT&CK technique tagging, possibly leveraging existing CSV/JSON mappings.
   - Consider abstracting SIEM integrations to support authentication, headers, and batching for large log volumes.

5. **Testing and Structure**
   - Introduce unit tests for non-interactive logic, especially around log writing and configuration loading.
   - Separate CLI prompts from business logic to facilitate automated testing and potential future GUI/API frontends.

6. **Documentation Improvements**
   - Update `README.md` usage instructions to reference `main.py` (currently mentions `main_menu.py`, which does not exist) and clarify OS-specific limitations for tools that depend on Windows APIs (`winreg`, `schtasks`).
   - Document privilege requirements and any external dependencies (PowerShell, schtasks, etc.).

By addressing the placeholders and enhancing the documentation and configuration management, socKit can evolve from a conceptual toolkit into a practical, extensible platform for SOC workflows.
