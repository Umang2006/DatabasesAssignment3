import datetime
import os
try:
    from .db import get_db_connection
except ImportError:
    from db import get_db_connection


LOG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs')
LOG_FILE = os.path.join(LOG_DIR, 'audit.log')
os.makedirs(LOG_DIR, exist_ok=True)


def _append_file_log(user, action, created_at):
    with open(LOG_FILE, "a", encoding="utf-8") as handle:
        handle.write(f"[{created_at}] USER: {user} ACTION: {action}\n")


def _ensure_audit_table(cursor):
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS audit_log (
            audit_id INT NOT NULL AUTO_INCREMENT,
            username VARCHAR(100) NOT NULL,
            action VARCHAR(255) NOT NULL,
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (audit_id),
            KEY idx_audit_created_at (created_at)
        )
    """)


def log_action(user, action):
    created_at = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        _ensure_audit_table(cursor)
        cursor.execute(
            "INSERT INTO audit_log (username, action, created_at) VALUES (%s, %s, %s)",
            (user, action, created_at)
        )
        conn.commit()
        cursor.close()
        conn.close()
    except Exception:
        pass

    _append_file_log(user, action, created_at)


def get_recent_logs(limit=200):
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        _ensure_audit_table(cursor)
        cursor.execute(
            "SELECT username, action, created_at FROM audit_log ORDER BY created_at DESC, audit_id DESC LIMIT %s",
            (limit,)
        )
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
        return [
            f"[{row['created_at']}] USER: {row['username']} ACTION: {row['action']}"
            for row in rows
        ]
    except Exception:
        try:
            with open(LOG_FILE, 'r', encoding='utf-8') as handle:
                lines = handle.readlines()
            return [line.strip() for line in reversed(lines) if line.strip()][:limit]
        except FileNotFoundError:
            return []
