from __future__ import annotations

import argparse
import sys
from pathlib import Path

_backend_root = Path(__file__).resolve().parent.parent
_project_root = _backend_root.parent
if str(_backend_root) not in sys.path:
    sys.path.insert(0, str(_backend_root))
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from app.core.env_bootstrap import load_repo_env
from app.core.logging_config import get_logger
from app.core.logging_config import setup_logging
from app.services.ftp_watch_ingest_service import FtpIngestConfig, FtpWatchIngestService

logger = get_logger("ftp-watch-ingest")


def build_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Сервис FTP-импорта часов: НОВЫЕ/БУ -> матчинг -> запись в БД"
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Выполнить только один проход",
    )
    parser.add_argument(
        "--skip-ozon",
        action="store_true",
        help="Не запускать Ozon import-layer после Avito",
    )
    parser.add_argument(
        "--skip-dns",
        action="store_true",
        help="Не запускать DNS import-layer после Avito/Ozon",
    )
    parser.add_argument(
        "--skip-wb",
        action="store_true",
        help="Do not run WB import-layer after Avito/Ozon/DNS",
    )
    parser.add_argument(
        "--ozon-dry-run",
        action="store_true",
        help="Проверить Ozon без записи в БД",
    )
    parser.add_argument(
        "--dns-dry-run",
        action="store_true",
        help="Проверить DNS без записи в БД",
    )
    parser.add_argument(
        "--wb-dry-run",
        action="store_true",
        help="Run WB import-layer without writing to DB",
    )
    return parser.parse_args()


def run_marketplace_import_once(source: str, *, dry_run: bool = False) -> None:
    from backend.import_layer.main import main as import_layer_main

    argv = ["--source", source, "--from-ftp", "--latest"]
    if dry_run:
        argv.append("--dry-run")

    log_source = source.upper()
    logger.info("[{}] Запуск import-layer: {}", log_source, " ".join(argv))
    exit_code = import_layer_main(argv)
    if exit_code:
        logger.warning("[{}] Import-layer завершился с кодом {}", log_source, exit_code)


def main() -> None:
    load_repo_env()
    setup_logging("ftp-watch-ingest")
    args = build_args()
    config = FtpIngestConfig.from_env()
    service = FtpWatchIngestService(config)

    def run_extra_imports() -> None:
        if not args.skip_ozon:
            run_marketplace_import_once("ozon", dry_run=args.ozon_dry_run)
        if not args.skip_dns:
            run_marketplace_import_once("dns", dry_run=args.dns_dry_run)
        if not args.skip_wb:
            run_marketplace_import_once("wb", dry_run=args.wb_dry_run)

    if args.once:
        service.run_once()
        run_extra_imports()
        return
    service.run_forever(after_run_once=run_extra_imports)


if __name__ == "__main__":
    main()
