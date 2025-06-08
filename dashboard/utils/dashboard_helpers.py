# dashboard/utils/dashboard_helpers.py

import json
from pathlib import Path

def load_control_flags():
    """
    Load control flags from the dashboard's control JSON.
    These can be used by the bot launcher or services to respond to user commands.
    """
    flag_file = Path("dashboard/controls/control_flags.json")
    if flag_file.exists():
        try:
            return json.loads(flag_file.read_text())
        except json.JSONDecodeError:
            return {}
    return {}
