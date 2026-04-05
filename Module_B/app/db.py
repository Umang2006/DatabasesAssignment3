import mysql.connector
try:
    from .config import get_db_settings
except ImportError:
    from config import get_db_settings

_SCHEMA_READY = False


def _index_exists(cursor, table_name, index_name):
    cursor.execute(
        """
        SELECT 1
        FROM information_schema.statistics
        WHERE table_schema = DATABASE()
          AND table_name = %s
          AND index_name = %s
        LIMIT 1
        """,
        (table_name, index_name)
    )
    return cursor.fetchone() is not None


def _ensure_runtime_schema(conn):
    global _SCHEMA_READY
    if _SCHEMA_READY:
        return

    cursor = conn.cursor()
    try:
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
        if not _index_exists(cursor, 'appointment', 'uq_appointment_doctor_date_slot'):
            try:
                cursor.execute(
                    "CREATE UNIQUE INDEX uq_appointment_doctor_date_slot ON appointment (doctor_id, appointment_date, slot_id)"
                )
            except mysql.connector.Error:
                pass
        if not _index_exists(cursor, 'appointment', 'uq_appointment_doctor_date_time'):
            try:
                cursor.execute(
                    "CREATE UNIQUE INDEX uq_appointment_doctor_date_time ON appointment (doctor_id, appointment_date, appointment_time)"
                )
            except mysql.connector.Error:
                pass
        conn.commit()
        _SCHEMA_READY = True
    finally:
        cursor.close()


def get_db_connection():
    settings = get_db_settings()
    conn = mysql.connector.connect(
        host=settings["host"],
        user=settings["user"],
        password=settings["password"],
        database=settings["database"]
    )
    _ensure_runtime_schema(conn)
    return conn
