from __future__ import annotations

import fnmatch
import os
from dataclasses import dataclass
from datetime import datetime
from ftplib import FTP, all_errors
from pathlib import Path, PurePosixPath


class FtpImportError(RuntimeError):
    pass


class FtpFileNotFoundError(FtpImportError):
    pass


def _clean_env(value: str | None, default: str | None = None) -> str | None:
    if value is None:
        return default
    cleaned = str(value).strip().strip('"').strip("'")
    return cleaned if cleaned else default


def _ftp_base_dir() -> str:
    return _clean_env(os.getenv("FTP_BASE_DIR"), "/") or "/"


@dataclass(frozen=True)
class RemoteFile:
    path: str
    name: str
    size: int | None = None
    modified_at: datetime | None = None


@dataclass(frozen=True)
class FtpConnectionSettings:
    host: str
    user: str
    password: str
    port: int = 21
    base_dir: str = "/"


def default_ftp_settings() -> FtpConnectionSettings:
    return FtpConnectionSettings(
        host=_clean_env(os.getenv("FTP_HOST")) or "",
        user=_clean_env(os.getenv("FTP_USER")) or "",
        password=_clean_env(os.getenv("FTP_PASS")) or "",
        port=int(_clean_env(os.getenv("FTP_PORT"), "21") or "21"),
        base_dir=_ftp_base_dir(),
    )


def ftp_settings_from_env_prefix(prefix: str) -> FtpConnectionSettings | None:
    """Return source-specific FTP settings when a parser server is configured."""
    host = _clean_env(os.getenv(f"{prefix}_HOST"))
    if not host:
        return None

    return FtpConnectionSettings(
        host=host,
        user=_clean_env(os.getenv(f"{prefix}_USER")) or _clean_env(os.getenv("FTP_USER")) or "",
        password=_clean_env(os.getenv(f"{prefix}_PASS")) or _clean_env(os.getenv("FTP_PASS")) or "",
        port=int(_clean_env(os.getenv(f"{prefix}_PORT"), _clean_env(os.getenv("FTP_PORT"), "21")) or "21"),
        base_dir=_clean_env(os.getenv(f"{prefix}_BASE_DIR"), "/") or "/",
    )


def describe_ftp_settings(settings: FtpConnectionSettings | None) -> str:
    settings = settings or default_ftp_settings()
    return f"{settings.host}:{settings.port}{settings.base_dir}"


def connect_ftp(settings: FtpConnectionSettings | None = None) -> FTP:
    settings = settings or default_ftp_settings()

    if not settings.host or not settings.user or settings.password is None:
        raise FtpImportError("Set FTP_HOST, FTP_USER and FTP_PASS in .env")

    try:
        ftp = FTP()
        ftp.connect(settings.host, settings.port, timeout=30)
        ftp.login(settings.user, settings.password)
        ftp.set_pasv(True)
        ftp.cwd(settings.base_dir)
        return ftp
    except all_errors as exc:
        raise FtpImportError(f"FTP connection failed: {exc}") from exc


def list_files(
    remote_dir: str = "/",
    *,
    settings: FtpConnectionSettings | None = None,
) -> list[RemoteFile]:
    try:
        with connect_ftp(settings) as ftp:
            _safe_cwd(ftp, remote_dir)
            names = [name for name in ftp.nlst() if name not in {"", ".", ".."}]
            files: list[RemoteFile] = []
            for name in names:
                filename = PurePosixPath(name).name
                if not filename:
                    continue
                files.append(
                    RemoteFile(
                        path=_join_remote(remote_dir, filename),
                        name=filename,
                        size=_file_size(ftp, filename),
                        modified_at=_modified_at(ftp, filename),
                    )
                )
            return files
    except FtpImportError:
        raise
    except all_errors as exc:
        raise FtpImportError(f"Could not list FTP files: {exc}") from exc


def download_file(
    remote_path: str,
    local_path: str | Path,
    *,
    settings: FtpConnectionSettings | None = None,
) -> Path:
    target = Path(local_path).resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    remote = PurePosixPath(remote_path)
    remote_dir = str(remote.parent) if str(remote.parent) != "." else "/"
    filename = remote.name

    if not filename:
        raise FtpImportError(f"Invalid FTP path: {remote_path}")

    try:
        with connect_ftp(settings) as ftp:
            _safe_cwd(ftp, remote_dir)
            with target.open("wb") as output:
                ftp.retrbinary(f"RETR {filename}", output.write)
    except FtpImportError:
        raise
    except all_errors as exc:
        raise FtpImportError(f"Could not download FTP file {remote_path}: {exc}") from exc

    if not target.exists() or target.stat().st_size == 0:
        raise FtpImportError(f"FTP file was downloaded empty: {remote_path}")

    return target


def find_latest_file(
    pattern: str,
    remote_dir: str = "/",
    *,
    settings: FtpConnectionSettings | None = None,
) -> RemoteFile:
    files = list_files(remote_dir, settings=settings)
    matched = [
        file_info
        for file_info in files
        if fnmatch.fnmatch(file_info.name, pattern)
        and not _is_audit_conflict_file(file_info.name)
    ]
    if not matched:
        available = ", ".join(file_info.name for file_info in files[:30]) or "empty"
        raise FtpFileNotFoundError(
            f"File not found by pattern {pattern}; visible on FTP: {available}"
        )

    return max(
        matched,
        key=lambda item: (
            item.modified_at or datetime.min,
            item.name,
        ),
    )


def find_file_by_names(
    candidates: list[str],
    remote_dir: str = "/",
    *,
    settings: FtpConnectionSettings | None = None,
) -> RemoteFile:
    files = list_files(remote_dir, settings=settings)
    wanted = {candidate.lower(): candidate for candidate in candidates}
    for file_info in files:
        if file_info.name.lower() in wanted and not _is_audit_conflict_file(file_info.name):
            return file_info

    available = ", ".join(file_info.name for file_info in files[:30]) or "empty"
    raise FtpFileNotFoundError(
        f"File not found. Tried: {', '.join(candidates)}; visible on FTP: {available}"
    )


def _safe_cwd(ftp: FTP, remote_dir: str) -> None:
    target_dir = remote_dir.strip() or "/"
    if target_dir == "/":
        return
    ftp.cwd(target_dir)


def _join_remote(remote_dir: str, filename: str) -> str:
    directory = remote_dir.strip() or "/"
    if directory == "/":
        return f"/{filename}"
    return f"{directory.rstrip('/')}/{filename}"


def _modified_at(ftp: FTP, filename: str) -> datetime | None:
    try:
        response = ftp.sendcmd(f"MDTM {filename}")
    except all_errors:
        return None
    if not response.startswith("213 "):
        return None
    try:
        return datetime.strptime(response[4:], "%Y%m%d%H%M%S")
    except ValueError:
        return None


def _file_size(ftp: FTP, filename: str) -> int | None:
    try:
        return int(ftp.size(filename))
    except all_errors:
        return None


def _is_audit_conflict_file(filename: str) -> bool:
    value = filename.lower()
    return "new_used_conflicts" in value or value.endswith("_conflicts.xlsx")
