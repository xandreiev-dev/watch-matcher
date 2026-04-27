from __future__ import annotations

import os
import re
import time
import json
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from ftplib import FTP
from pathlib import Path

import pandas as pd

from app.api.routes.process import build_process_logs, process_watch_row
from app.core.db import get_db_connection
from app.core.logging_config import get_logger
from app.services.excel_service import ExcelService
from app.services.watch_db_writer_service import WatchDbWriterService
from app.catalog.watch_reference_catalog import WatchReferenceCatalog

logger = get_logger("ftp_ingest")


def _env_bool(name: str, default: str = "false") -> bool:
    return (os.getenv(name) or default).strip().lower() in ("true", "1", "yes", "y", "on")


@dataclass(frozen=True)
class FtpIngestConfig:
    ftp_host: str
    ftp_port: int
    ftp_user: str
    ftp_pass: str
    ftp_remote_dir: str
    local_download_dir: Path
    # Минута часа (0–59): проверка FTP раз в час в HH:MM (например 25 → 14:25, 15:25)
    check_minute: int = 25
    # Локальная отладка: один проход run_once без ожидания слота :MM, перезапись в БД для даты из файла
    is_debug: bool = False
    shop_id: int = 2

    @classmethod
    def from_env(cls) -> "FtpIngestConfig":
        host = (os.getenv("FTP_HOST") or os.getenv("SMARTWATCH_FTP_HOST") or "").strip()
        user = (os.getenv("FTP_USER") or os.getenv("SMARTWATCH_FTP_USER") or "").strip()
        password = (os.getenv("FTP_PASS") or os.getenv("SMARTWATCH_FTP_PASS") or "").strip()
        if not host or not user or not password:
            raise RuntimeError(
                "Задайте FTP_HOST, FTP_USER и FTP_PASS в переменных окружения"
            )
        check_minute = int(
            os.getenv("FTP_CHECK_MINUTE") or os.getenv("SMARTWATCH_FTP_CHECK_MINUTE") or "25"
        )
        if not 0 <= check_minute <= 59:
            raise RuntimeError("FTP_CHECK_MINUTE должен быть в диапазоне 0…59")
        is_debug = _env_bool("IS_DEBUG", "false")
        return cls(
            ftp_host=host,
            ftp_port=int(os.getenv("FTP_PORT") or os.getenv("SMARTWATCH_FTP_PORT") or "21"),
            ftp_user=user,
            ftp_pass=password,
            ftp_remote_dir=(
                os.getenv("FTP_REMOTE_DIR")
                or os.getenv("SMARTWATCH_FTP_REMOTE_DIR")
                or "/Avito/watch"
            ).strip()
            or "/Avito/watch",
            local_download_dir=Path(
                os.getenv("FTP_LOCAL_DOWNLOAD_DIR")
                or os.getenv("SMARTWATCH_LOCAL_DOWNLOAD_DIR")
                or "tmp/ftp_avito"
            ).resolve(),
            check_minute=check_minute,
            is_debug=is_debug,
        )


def extract_date_from_filename(filename: str) -> date | None:
    ymd = re.search(r"(\d{8})", filename)
    if ymd:
        return datetime.strptime(ymd.group(1), "%Y%m%d").date()
    dmy = re.search(r"(\d{2})_(\d{2})_(\d{4})", filename)
    if dmy:
        day, month, year = dmy.groups()
        return date(int(year), int(month), int(day))
    iso = re.search(r"(\d{4})-(\d{2})-(\d{2})", filename)
    if iso:
        year, month, day = iso.groups()
        return date(int(year), int(month), int(day))
    return None


def _file_type_from_name(filename: str) -> bool | None:
    value = filename.lower()
    if "_used_" in value or "_old_" in value or "used" in value or "old" in value:
        return False
    if "_new_" in value or "new" in value:
        return True
    return None


def _pick_latest_by_type(
    files_with_mdtm: dict[str, datetime],
    *,
    is_new: bool,
) -> tuple[str, datetime] | None:
    candidates: dict[str, datetime] = {}
    for name, mdtm in files_with_mdtm.items():
        file_type = _file_type_from_name(name)
        if file_type is None or file_type != is_new:
            continue
        candidates[name] = mdtm
    if not candidates:
        return None
    file_name = max(candidates, key=candidates.get)
    return file_name, candidates[file_name]


class FtpWatchIngestService:
    def __init__(self, config: FtpIngestConfig):
        self.config = config
        self._models_catalog: list[dict] | None = None
        self._variants_catalog: list[dict] | None = None
        self.config.local_download_dir.mkdir(parents=True, exist_ok=True)
        self._state_path = self.config.local_download_dir / "import_state.json"

    def _load_state(self) -> dict:
        if not self._state_path.is_file():
            return {}
        try:
            return json.loads(self._state_path.read_text(encoding="utf-8"))
        except Exception as exc:
            logger.warning(f"[ФТП] Не удалось прочитать import_state.json: {exc}")
            return {}

    def _save_state(self, state: dict) -> None:
        self._state_path.parent.mkdir(parents=True, exist_ok=True)
        self._state_path.write_text(
            json.dumps(state, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    @staticmethod
    def _reimport_state_key(actual_date: date, is_new: bool) -> str:
        return f"{actual_date.isoformat()}:{'NEW' if is_new else 'USED'}"

    def _has_used_today_reimport(self, actual_date: date, is_new: bool) -> bool:
        state = self._load_state()
        key = self._reimport_state_key(actual_date, is_new)
        return key in state.get("today_reimports", {})

    def _mark_today_reimport(
        self,
        actual_date: date,
        is_new: bool,
        *,
        file_name: str,
        mdtm: datetime,
        existing_price_count: int,
    ) -> None:
        state = self._load_state()
        today_reimports = state.setdefault("today_reimports", {})
        key = self._reimport_state_key(actual_date, is_new)
        today_reimports[key] = {
            "file_name": file_name,
            "mdtm": mdtm.isoformat(),
            "existing_price_count": existing_price_count,
            "reimported_at": datetime.now().isoformat(timespec="seconds"),
        }
        self._save_state(state)

    def _seconds_until_next_hourly_slot(self) -> float:
        """Секунды до ближайшей отметки локального времени HH:MM, где MM = check_minute."""
        now = datetime.now()
        m = self.config.check_minute
        target = now.replace(minute=m, second=0, microsecond=0)
        if now >= target:
            target += timedelta(hours=1)
        return max(0.0, (target - now).total_seconds())

    def _ensure_catalog(self) -> tuple[list[dict], list[dict]]:
        if self._models_catalog is None or self._variants_catalog is None:
            self._models_catalog = WatchReferenceCatalog.load_models()
            self._variants_catalog = WatchReferenceCatalog.load_variants()
            logger.info(
                f"[ФТП] Каталог загружен: моделей={len(self._models_catalog)} вариантов={len(self._variants_catalog)}"
            )
        return self._models_catalog, self._variants_catalog

    def _list_ftp_files_with_mdtm(self) -> dict[str, datetime]:
        files: dict[str, datetime] = {}
        with FTP() as ftp:
            ftp.connect(self.config.ftp_host, self.config.ftp_port, timeout=20)
            ftp.login(self.config.ftp_user, self.config.ftp_pass)
            ftp.set_pasv(True)
            ftp.cwd(self.config.ftp_remote_dir)
            for name in ftp.nlst():
                if not name or name in {".", ".."} or not name.lower().endswith(".xlsx"):
                    continue
                response = ftp.sendcmd(f"MDTM {name}")
                if response.startswith("213 "):
                    ts = datetime.strptime(response[4:], "%Y%m%d%H%M%S")
                    files[name] = ts
        return files

    def _download_file(self, file_name: str) -> Path:
        target = self.config.local_download_dir / file_name
        with FTP() as ftp:
            ftp.connect(self.config.ftp_host, self.config.ftp_port, timeout=20)
            ftp.login(self.config.ftp_user, self.config.ftp_pass)
            ftp.set_pasv(True)
            ftp.cwd(self.config.ftp_remote_dir)
            with target.open("wb") as out:
                ftp.retrbinary(f"RETR {file_name}", out.write)
        return target

    def _price_count_for_date(self, actual_date: date, is_new: bool) -> int:
        query = """
        SELECT COUNT(*) AS cnt
        FROM g_watch_price wp
        JOIN g_shop_watch sw ON sw.id = wp.shop_watch_id
        WHERE sw.shop_id = %s AND wp.actual_date = %s AND wp.is_new = %s
        """
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    query,
                    (self.config.shop_id, actual_date, "Y" if is_new else "N"),
                )
                row = cursor.fetchone() or {}
                return int(row.get("cnt") or 0)
        finally:
            conn.close()

    def _has_prices_for_date(self, actual_date: date, is_new: bool) -> bool:
        return self._price_count_for_date(actual_date, is_new) > 0

    def _process_file(
        self,
        local_path: Path,
        *,
        actual_date: date,
        is_new: bool,
        force_reimport: bool,
    ) -> None:
        logger.info(
            f"[ФТП] Начата обработка файла={local_path.name} дата={actual_date} тип={'НОВЫЕ' if is_new else 'БУ'}"
            + (f" | принудительная_перезапись={force_reimport}" if force_reimport else "")
        )
        dataframe = pd.read_excel(local_path)
        logger.info(
            f"[ФТП] Входной XLSX файл={local_path.name} строк={len(dataframe)} колонок={len(dataframe.columns)}"
        )
        ExcelService.validate_columns(dataframe)
        processed_df = dataframe.fillna("").copy()
        models_catalog, variants_catalog = self._ensure_catalog()
        result: list[dict] = []
        for _, row in processed_df.iterrows():
            result.append(process_watch_row(row.to_dict(), models_catalog, variants_catalog))
        build_process_logs(result, is_new)
        WatchDbWriterService.prepare_and_write_watch_data_to_db(
            df_res=pd.DataFrame(result),
            actual_date=actual_date,
            shop_id=self.config.shop_id,
            is_new=is_new,
        )
        logger.info(
            f"[ФТП] Запись в БД завершена файл={local_path.name} строк={len(result)} тип={'НОВЫЕ' if is_new else 'БУ'}"
        )

    def run_once(self, *, force_reimport: bool | None = None) -> None:
        force = self.config.is_debug if force_reimport is None else force_reimport
        if force:
            logger.info("[ФТП] Режим перезаписи: пропуск проверки «данные за дату уже есть» (актуальные строки перезапишутся через UPSERT)")

        files = self._list_ftp_files_with_mdtm()
        logger.info(f"[ФТП] Найдено {len(files)} xlsx-файлов в {self.config.ftp_remote_dir}")
        for is_new in (True, False):
            picked = _pick_latest_by_type(files, is_new=is_new)
            if picked is None:
                logger.warning(f"[ФТП] Не найдено файлов типа {'НОВЫЕ' if is_new else 'БУ'}")
                continue
            file_name, mdtm = picked
            actual_date = extract_date_from_filename(file_name)
            if actual_date is None:
                logger.warning(f"[ФТП] Пропуск {file_name}: не удалось извлечь дату из имени файла")
                continue
            existing_price_count = self._price_count_for_date(actual_date, is_new)
            mark_today_reimport = False
            if not force and existing_price_count:
                if actual_date == date.today():
                    if self._has_used_today_reimport(actual_date, is_new):
                        logger.info(
                            f"[ФТП] Пропуск {file_name}: за дату={actual_date} и тип={'НОВЫЕ' if is_new else 'БУ'} "
                            f"уже есть записи ({existing_price_count}) и однократная повторная обработка сегодня уже выполнена"
                        )
                        continue
                    mark_today_reimport = True
                    logger.warning(
                        f"[ФТП] За дату={actual_date} и тип={'НОВЫЕ' if is_new else 'БУ'} уже есть "
                        f"{existing_price_count} price-строк — выполню один повторный импорт текущего дневного файла, "
                        "чтобы не оставить частичный импорт"
                    )
                else:
                    logger.info(
                        f"[ФТП] Пропуск {file_name}: записи за дату={actual_date} и тип={'НОВЫЕ' if is_new else 'БУ'} "
                        f"уже есть ({existing_price_count})"
                    )
                    continue
            if force and existing_price_count:
                logger.warning(
                    f"[ФТП] Отладка: данные за дату={actual_date} и тип={'НОВЫЕ' if is_new else 'БУ'} уже есть "
                    f"({existing_price_count}) — выполняю повторную обработку и перезапись"
                )
            logger.info(
                f"[ФТП] Скачивание {file_name} (mdtm={mdtm.isoformat()}) для типа={'НОВЫЕ' if is_new else 'БУ'}"
            )
            local_path = self._download_file(file_name)
            self._process_file(
                local_path,
                actual_date=actual_date,
                is_new=is_new,
                force_reimport=force,
            )
            if mark_today_reimport:
                self._mark_today_reimport(
                    actual_date,
                    is_new,
                    file_name=file_name,
                    mdtm=mdtm,
                    existing_price_count=existing_price_count,
                )

    def run_forever(self) -> None:
        if self.config.is_debug:
            logger.warning(
                f"[ФТП] IS_DEBUG=истина: один проход без ожидания :{self.config.check_minute:02d}, "
                f"перезапись по дате из файла; каталог={self.config.ftp_remote_dir}"
            )
            try:
                self.run_once()
            except Exception as exc:
                logger.exception(f"[ФТП] Ошибка итерации: {exc}")
            return

        logger.info(
            f"[ФТП] Сервис FTP-импорта запущен; расписание: каждый час в {self.config.check_minute:02d} минуту "
            f"(локальное время сервера); каталог={self.config.ftp_remote_dir}"
        )
        while True:
            wait_sec = int(self._seconds_until_next_hourly_slot())
            logger.info(
                f"[ФТП] Ожидание до следующей проверки: {wait_sec} с (следующий слот — на {self.config.check_minute:02d}-й минуте часа)"
            )
            time.sleep(max(0.0, float(wait_sec)))
            try:
                self.run_once()
            except Exception as exc:
                logger.exception(f"[ФТП] Ошибка итерации: {exc}")
