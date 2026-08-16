from __future__ import annotations

import os
from pathlib import Path


IMPORT_SOURCES = {
    "ozon": {
        "ftp_pattern": "Ozon_watch_ru_*.xlsx",
        "ftp_remote_dir": "/",
        "source_ftp_env_prefix": "OZON_WATCH_FTP",
        "source_ftp_remote_dirs": ["/ozon_watch_parser/brand_exports"],
        "filename_template": "Ozon_watch_ru_{date}.xlsx",
        "filename_templates": [
            "Ozon_watch_ru_{date}.xlsx",
            "Ozon_watch_ru_{iso_date}.xlsx",
        ],
        "shop_name": "Ozon",
        "preset": "ozon",
        "shop_id": 1,
        "default_is_new": True,
    },
    "dns": {
        "ftp_pattern": "DNS_watch_ru_*.xlsx",
        "ftp_remote_dir": "/",
        "source_ftp_env_prefix": "DNS_WATCH_FTP",
        "source_ftp_remote_dirs": ["/dns_watch_parser/brand_exports"],
        "filename_template": "DNS_watch_ru_{date}.xlsx",
        "filename_templates": [
            "DNS_watch_ru_{date}.xlsx",
            "DNS_watch_ru_{iso_date}.xlsx",
            "dns_watch_{date}.xlsx",
            "dns_watch_{iso_date}.xlsx",
        ],
        "shop_name": "DNS",
        "preset": "dns",
        "shop_id": 6,
        "default_is_new": True,
    },
    "wb": {
        "ftp_pattern": "WB_watch_ru_*.xlsx",
        "ftp_remote_dir": "/",
        "source_ftp_env_prefix": "WB_WATCH_FTP",
        "source_ftp_remote_dirs": [
            "/wb_watch_parser/brand_exports",
            "/wb_parser/brand_exports",
        ],
        "filename_template": "WB_watch_ru_{date}.xlsx",
        "filename_templates": [
            "WB_watch_ru_{date}.xlsx",
            "WB_watch_ru_{iso_date}.xlsx",
            "wb_watch_{date}.xlsx",
            "wb_watch_{iso_date}.xlsx",
        ],
        "shop_name": "WB",
        "preset": "wb",
        "shop_id": 3,
        "default_is_new": True,
    },
    "avito": {
        "ftp_pattern": "*avito_watch_*.xlsx",
        "ftp_remote_dir": "/Avito/watch",
        "filename_template": "avito_watch_{iso_date}_new.xlsx",
        "filename_templates": [
            "avito_watch_{iso_date}_new.xlsx",
            "avito_watch_{iso_date}_old.xlsx",
            "Avito_watch_{date}.xlsx",
            "Avito_watch_{iso_date}.xlsx",
        ],
        "shop_name": "Avito",
        "preset": "avito",
        "shop_id": 2,
        "default_is_new": True,
    },
}


def project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def backend_root() -> Path:
    return Path(__file__).resolve().parents[1]


def resolve_project_path(value: str | os.PathLike[str]) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    return (project_root() / path).resolve()


def import_input_dir() -> Path:
    return resolve_project_path(os.getenv("IMPORT_INPUT_DIR", "backend/input/ftp"))


def import_output_dir() -> Path:
    return resolve_project_path(
        os.getenv("IMPORT_OUTPUT_DIR", "backend/output/import_logs")
    )


def ensure_import_dirs() -> tuple[Path, Path]:
    input_dir = import_input_dir()
    output_dir = import_output_dir()
    input_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)
    return input_dir, output_dir
