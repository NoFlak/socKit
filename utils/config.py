import os
import json

config_file = "config.json"
default_config = {
    "log_folder": "H:/Scripts/Logs",  # Or another valid drive/path
    "timeout": 300,
    "default_scan_type": "Aggressive"
}

def load_config():
    if os.path.exists(config_file):
        try:
            with open(config_file, "r") as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading configuration file: {e}")
    return default_config