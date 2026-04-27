"""Загрузка корневого .env до импорта маршрутов (важно для отладки main.py и uvicorn reload)."""
from __future__ import annotations

from io import StringIO
from pathlib import Path

from dotenv import load_dotenv


def load_repo_env() -> None:
    root = Path(__file__).resolve().parents[3]
    env = root / ".env"
    if env.is_file():
        load_dotenv(stream=StringIO(env.read_text(encoding="utf-8-sig")))
    backend_env = root / "backend" / ".env"
    if backend_env.is_file():
        load_dotenv(stream=StringIO(backend_env.read_text(encoding="utf-8-sig")), override=False)
    mcp = root / "mcp-mysql" / ".env"
    if mcp.is_file():
        load_dotenv(stream=StringIO(mcp.read_text(encoding="utf-8-sig")), override=False)
