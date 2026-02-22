import json
import shutil
import os
from datetime import datetime

def get_config():
    with open("config.json", "r") as f:
        config = json.load(f)
    return config

def save_config(config: dict):
    # Backup config file before saving
    for file in os.listdir():
        if file.startswith("config_backup_") and file.endswith(".json"):
            backup_time = datetime.strptime(file[len("config_backup_"):-len(".json")], "%Y%m%d_%H%M%S")
            if (datetime.now() - backup_time).total_seconds() > 30 * 24 * 3600:  # Older than 30 days
                os.remove(file)
    shutil.copy("config.json", f"config_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
    
    with open("config.json", "w") as f:
        json.dump(config, f, indent=4)

config = get_config()
