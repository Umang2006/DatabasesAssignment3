import os


def get_env(name, default=None):
    value = os.environ.get(name)
    return value if value not in (None, "") else default


def get_db_settings():
    return {
        "host": get_env("DMS_DB_HOST", "localhost"),
        "user": get_env("DMS_DB_USER", "root"),
        "password": get_env("DMS_DB_PASSWORD", "dev@mysql@2"),
        "database": get_env("DMS_DB_NAME", "dms_db"),
    }


def get_jwt_secret():
    return get_env("JWT_SECRET", "dev-only-change-me")
