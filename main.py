import platform
from config import load_config
from logging_utils import write_action
from system_tools import system_file_checker
from network_tools import ping_test
from red_team import red_team_menu
from blue_team import blue_team_menu
from purple_team import purple_team_menu
from utils import (
    create_directory,
    list_directory_contents,
    display_ip_configuration,
    display_mac_addresses,
    display_user_information
)

# --- Initialization ---
config = load_config()
log_folder = config["log_folder"]
timeout = config["timeout"]
os_name = platform.system()
create_directory(log_folder)
print(f"Operating System Detected: {os_name}")
print(f"Log folder: {log_folder}")

def show_main_menu():
    while True:
        print("\n==========================================")
        print("      Cross-Platform SOC Toolkit v2.4     ")
        print("==========================================")
        print("1. System Diagnostics")
        print("2. Network Diagnostics")
        print("3. Red Team Tools")
        print("4. Blue Team Tools")
        print("5. Purple Team Tools")
        print("6. Directory Information")
        print("7. IP Configuration")
        print("8. MAC Address Information")
        print("9. User Information")
        print("Q. Quit")
        print("==========================================")
        choice = input("Enter your choice: ").strip().upper()
        if choice == "1":
            system_file_checker()
        elif choice == "2":
            ping_test()
        elif choice == "3":
            red_team_menu()
        elif choice == "4":
            blue_team_menu()
        elif choice == "5":
            purple_team_menu()
        elif choice == "6":
            list_directory_contents()
        elif choice == "7":
            display_ip_configuration()
        elif choice == "8":
            display_mac_addresses()
        elif choice == "9":
            display_user_information()
        elif choice == "Q":
            print("Exiting the toolkit. Goodbye!")
            break
        else:
            print("Invalid selection. Please try again.")

if __name__ == "__main__":
    show_main_menu()