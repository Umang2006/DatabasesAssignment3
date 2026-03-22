import datetime
import os

# logger.py lives in app/ — write logs to app/logs/audit.log
# auth_routes.py is in app/routes/ and does os.path.dirname/../logs
# Both resolve to app/logs/ — same folder, no mismatch
LOG_DIR  = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs')
LOG_FILE = os.path.join(LOG_DIR, 'audit.log')
os.makedirs(LOG_DIR, exist_ok=True)

def log_action(user, action):
    with open(LOG_FILE, "a") as f:
        f.write(f"[{datetime.datetime.now()}] USER: {user} ACTION: {action}\n")