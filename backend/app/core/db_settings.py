"""Переменные БД/SSH из .env (согласовано с smart_price_tracker/db/common_const.py)."""
from __future__ import annotations

import os

from app.core.env_bootstrap import load_repo_env

load_repo_env()

SSH_HOST = (os.getenv("SSH_HOST") or os.getenv("SSH_HOST_PROD") or "").strip()
_db_use_ssh_raw = os.getenv("DB_USE_SSH")
DB_USE_SSH = (
    _db_use_ssh_raw.lower() in ("true", "1", "yes")
    if _db_use_ssh_raw is not None
    else bool(SSH_HOST)
)
SSH_PORT = int(os.getenv("SSH_PORT", "22") or 22)
SSH_USER = os.getenv("SSH_USER")
SSH_PASSWORD = (os.getenv("SSH_PASSWORD") or "").strip().strip('"').strip("'")
SQL_HOSTNAME = os.getenv("SQL_HOSTNAME") or os.getenv("SQL_HOST") or "127.0.0.1"
SQL_PORT = int(os.getenv("SQL_PORT", "3306") or 3306)
SQL_USERNAME = os.getenv("SQL_USERNAME")
SQL_PASSWORD = os.getenv("SQL_PASSWORD")
SQL_DATABASE = os.getenv("SQL_DATABASE")
DB_HOST = os.getenv("DB_HOST") or os.getenv("SQL_HOST")


def remote_bind_address() -> tuple[str, int]:
    """MySQL на стороне SSH-сервера (remote_bind), как SQL_HOSTNAME/SQL_PORT в smart_price_tracker."""
    h = os.getenv("MYSQL_REMOTE_HOST") or SQL_HOSTNAME
    p = int(os.getenv("MYSQL_REMOTE_PORT") or SQL_PORT)
    return h, p


def direct_mysql_address() -> tuple[str, int]:
    """Прямое подключение при DB_USE_SSH=false."""
    h = DB_HOST or SQL_HOSTNAME or "127.0.0.1"
    return h, SQL_PORT
