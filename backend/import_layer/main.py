from __future__ import annotations

import argparse
import hashlib
import os
import re
import sys
from datetime import date, datetime
from pathlib import Path
from typing import Sequence

from backend.import_layer.config import IMPORT_SOURCES, ensure_import_dirs
from backend.import_layer.ftp_client import (
    FtpConnectionSettings,
    FtpFileNotFoundError,
    FtpImportError,
    describe_ftp_settings,
    download_file,
    find_file_by_names,
    find_latest_file,
    ftp_settings_from_env_prefix,
)

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.core.env_bootstrap import load_repo_env
from app.core.logging_config import get_logger, setup_logging

logger = get_logger("watch_import_cli")


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    load_repo_env()
    setup_logging("watch-import")

    input_dir, output_dir = ensure_import_dirs()
    os.environ.setdefault("WATCH_IMPORT_OUTPUT_DIR", str(output_dir))
    os.environ.setdefault("WATCH_IMPORT_DEBUG_DIR", str(output_dir))

    source_cfg = IMPORT_SOURCES[args.source]
    source = source_cfg["preset"]

    try:
        input_path, remote_file, local_size = _resolve_input_file(
            args=args,
            source_cfg=source_cfg,
            input_dir=input_dir,
        )
        if _is_audit_conflict_file(input_path.name):
            raise ValueError(f"Audit/conflict XLSX is not importable as product data: {input_path.name}")
        file_date = (
            _date_from_arg(args.date)
            or _extract_date_from_filename(input_path.name)
            or date.today()
        )
        is_new = _infer_is_new_from_filename(
            input_path.name,
            default=bool(source_cfg.get("default_is_new", True)),
        )

        logger.info(
            "[IMPORT] source={} preset={} mode={} file={} size={}",
            args.source,
            source,
            "dry-run" if args.dry_run else "write",
            input_path,
            local_size,
        )

        if source != "avito" and not args.dry_run and not args.force:
            existing_price_count = _price_count_for_date(
                shop_id=int(source_cfg["shop_id"]),
                actual_date=file_date,
                is_new=is_new,
            )
            if existing_price_count:
                _print_already_imported(
                    args.source,
                    input_path.name,
                    file_date,
                    existing_price_count=existing_price_count,
                )
                return 0

        from app.importers.common_importer import run_matcher_pipeline

        result = run_matcher_pipeline(
            input_path,
            source=source,
            is_new=is_new,
            actual_date=file_date,
            dry_run=args.dry_run,
            debug_dir=output_dir,
        )

        _print_summary(
            shop_name=source_cfg["shop_name"],
            source=args.source,
            remote_file=remote_file,
            result=result,
            dry_run=args.dry_run,
        )
        return 0
    except (FtpImportError, FtpFileNotFoundError, ValueError) as exc:
        logger.error("[IMPORT] {}", exc)
        print(f"Import failed: {exc}")
        return 1
    except Exception as exc:
        logger.error("[IMPORT] unexpected error: {}", exc)
        print(f"Import failed: {exc}")
        return 1


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Import smartwatch XLSX files from FTP or local path"
    )
    parser.add_argument("--source", choices=sorted(IMPORT_SOURCES.keys()), required=True)
    parser.add_argument("--from-ftp", action="store_true")
    parser.add_argument("--latest", action="store_true")
    parser.add_argument("--date", help="File date in YYYYMMDD format")
    parser.add_argument("--input-file", help="Local XLSX path when --from-ftp is not used")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--force", action="store_true")
    return parser


def _resolve_input_file(
    *,
    args: argparse.Namespace,
    source_cfg: dict,
    input_dir: Path,
) -> tuple[Path, str | None, int]:
    if args.from_ftp:
        remote_file, ftp_settings = _resolve_remote_file(args, source_cfg)
        local_path = input_dir / Path(remote_file).name
        downloaded = download_file(remote_file, local_path, settings=ftp_settings)
        return downloaded, remote_file, downloaded.stat().st_size

    if not args.input_file:
        raise ValueError("Pass --input-file or use --from-ftp")

    path = Path(args.input_file).resolve()
    if not path.exists():
        raise ValueError(f"Local file not found: {path}")
    if path.stat().st_size == 0:
        raise ValueError(f"Local file is empty: {path}")
    return path, None, path.stat().st_size


def _resolve_remote_file(
    args: argparse.Namespace,
    source_cfg: dict,
) -> tuple[str, FtpConnectionSettings | None]:
    errors: list[str] = []
    for remote_dir, ftp_settings in _ftp_attempts(source_cfg):
        try:
            return _resolve_remote_file_in_dir(
                args,
                source_cfg,
                remote_dir=remote_dir,
                ftp_settings=ftp_settings,
            )
        except FtpFileNotFoundError as exc:
            errors.append(f"{describe_ftp_settings(ftp_settings)} {remote_dir}: {exc}")

    if errors:
        raise FtpFileNotFoundError(" | ".join(errors))
    raise FtpFileNotFoundError("FTP locations are not configured")


def _resolve_remote_file_in_dir(
    args: argparse.Namespace,
    source_cfg: dict,
    *,
    remote_dir: str,
    ftp_settings: FtpConnectionSettings | None,
) -> tuple[str, FtpConnectionSettings | None]:
    if args.latest:
        found = find_latest_file(
            source_cfg["ftp_pattern"],
            remote_dir=remote_dir,
            settings=ftp_settings,
        )
        logger.info(
            "[FTP] found latest file {} size={} location={}",
            found.path,
            found.size,
            describe_ftp_settings(ftp_settings),
        )
        return found.path, ftp_settings

    if args.date:
        candidates = _candidate_filenames(source_cfg, args.date)
        found = find_file_by_names(
            candidates,
            remote_dir=remote_dir,
            settings=ftp_settings,
        )
        logger.info(
            "[FTP] found file by date {} size={} location={}",
            found.path,
            found.size,
            describe_ftp_settings(ftp_settings),
        )
        return found.path, ftp_settings

    raise ValueError("For --from-ftp pass --latest or --date YYYYMMDD")


def _ftp_attempts(source_cfg: dict) -> list[tuple[str, FtpConnectionSettings | None]]:
    attempts: list[tuple[str, FtpConnectionSettings | None]] = []
    env_prefix = source_cfg.get("source_ftp_env_prefix")
    source_settings = ftp_settings_from_env_prefix(env_prefix) if env_prefix else None

    if source_settings:
        remote_dirs = _source_ftp_remote_dirs(env_prefix, source_cfg)
        for remote_dir in remote_dirs:
            attempts.append((remote_dir, source_settings))

    attempts.append((source_cfg.get("ftp_remote_dir", "/"), None))
    return attempts


def _source_ftp_remote_dirs(env_prefix: str | None, source_cfg: dict) -> list[str]:
    if env_prefix:
        raw_value = os.getenv(f"{env_prefix}_REMOTE_DIR") or os.getenv(f"{env_prefix}_PATH")
        if raw_value:
            return [
                item.strip()
                for item in re.split(r"[;,]", raw_value)
                if item.strip()
            ]

    return list(source_cfg.get("source_ftp_remote_dirs") or ["/"])


def _date_from_arg(value: str | None) -> date | None:
    if not value:
        return None
    if len(value) != 8 or not value.isdigit():
        raise ValueError("--date must be in YYYYMMDD format")
    return date(int(value[:4]), int(value[4:6]), int(value[6:8]))


def _candidate_filenames(source_cfg: dict, raw_date: str) -> list[str]:
    parsed = _date_from_arg(raw_date)
    values = {
        "date": raw_date,
        "iso_date": parsed.isoformat(),
    }
    templates = source_cfg.get("filename_templates") or [source_cfg["filename_template"]]
    candidates: list[str] = []
    for template in templates:
        filename = template.format(**values)
        if filename not in candidates:
            candidates.append(filename)
    return candidates


def _calculate_file_hash(path: Path) -> str:
    sha = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            sha.update(chunk)
    return sha.hexdigest()


def _price_count_for_date(*, shop_id: int, actual_date: date, is_new: bool) -> int:
    from app.core.db import get_db_connection

    query = """
    SELECT COUNT(*) AS cnt
    FROM g_watch_price wp
    JOIN g_shop_watch sw ON sw.id = wp.shop_watch_id
    WHERE sw.shop_id = %s AND wp.actual_date = %s AND wp.is_new = %s
    """
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(query, (shop_id, actual_date, "Y" if is_new else "N"))
            row = cursor.fetchone() or {}
            return int(row.get("cnt") or 0)
    finally:
        conn.close()


def _extract_date_from_filename(filename: str) -> date | None:
    ymd = re.search(r"(\d{8})", filename)
    if ymd:
        return datetime.strptime(ymd.group(1), "%Y%m%d").date()

    iso = re.search(r"(\d{4})-(\d{2})-(\d{2})", filename)
    if iso:
        year, month, day = iso.groups()
        return date(int(year), int(month), int(day))

    dmy = re.search(r"(\d{2})_(\d{2})_(\d{4})", filename)
    if dmy:
        day, month, year = dmy.groups()
        return date(int(year), int(month), int(day))

    return None


def _infer_is_new_from_filename(filename: str, default: bool = True) -> bool:
    value = filename.lower()
    if "_old" in value or "_used" in value or "old" in value or "used" in value:
        return False
    if "_new" in value or "new" in value:
        return True
    return default


def _is_audit_conflict_file(filename: str) -> bool:
    value = filename.lower()
    return "new_used_conflicts" in value or value.endswith("_conflicts.xlsx")


def _print_already_imported(
    source: str,
    filename: str,
    file_date: date,
    *,
    existing_price_count: int,
) -> None:
    print("===== WATCH IMPORT SUMMARY =====")
    print(f"Shop: {source}")
    print(f"Filename: {filename}")
    print(f"File date: {file_date}")
    print(f"Existing price rows: {existing_price_count}")
    print("Already imported: True")
    print("Errors: -")
    print("================================")


def _print_summary(*, shop_name: str, source: str, remote_file: str | None, result, dry_run: bool) -> None:
    print("===== WATCH IMPORT SUMMARY =====")
    print(f"Shop: {shop_name}")
    print(f"Source: {source}")
    print(f"Filename: {result.filename}")
    print(f"Remote file: {remote_file or '-'}")
    print(f"File date: {result.file_date}")
    print(f"Mode: {'dry-run' if dry_run else 'write'}")
    print(f"Total rows: {result.total_rows}")
    print(f"Valid rows: {result.db_ready_rows}")
    print(f"Matched rows: {result.matched_rows}")
    print(f"Unmatched rows: {result.unmatched_rows}")
    print("Inserted watches: n/a (existing DB helper uses INSERT IGNORE)")
    print("Updated watches: n/a (existing DB helper uses INSERT IGNORE)")
    print("Inserted shop rows: n/a (existing DB helper uses UPSERT)")
    print("Updated shop rows: n/a (existing DB helper uses UPSERT)")
    print(f"Inserted prices: {0 if dry_run else result.db_ready_rows}")
    print("Skipped duplicates: 0")
    print("Already imported: False")
    print("Errors: -")
    print(f"Debug files: {result.output_file}, {result.ready_file}, {result.failed_file}")
    print("================================")


if __name__ == "__main__":
    raise SystemExit(main())
