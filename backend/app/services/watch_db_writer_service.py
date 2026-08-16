import hashlib
import re
from datetime import date
from typing import Optional

import pandas as pd

from app.core.db import get_db_connection
from app.core.logging_config import get_logger
from app.ml.watch_fake_runtime import add_fake_proba, load_thresholds

logger = get_logger("db_writer")

MAX_WARRANTY_YEARS = 5
MAX_WARRANTY_MONTHS = MAX_WARRANTY_YEARS * 12
MAX_WARRANTY_DAYS = MAX_WARRANTY_YEARS * 365
MAX_REASONABLE_PRICE_RUB = 1_000_000


SHOP_NAMES = {
    1: "Озон",
    2: "Авито",
    3: "WB",
    4: "Яндекс",
    5: "Али",
    6: "DNS",
}

AVITO_SHOP_ID = 2
BATCH_FALLBACK_SOURCE = "batch_fallback"
SQL_IN_CHUNK_SIZE = 800
AVITO_PREMIUM_LOW_PRICE_CEIL_RUB = 6_500
AVITO_PREMIUM_APPLE_MODELS = {
    "watchseries10",
    "watchseries11",
    "watchultra",
    "watchultra2",
    "watchultra3",
}
AVITO_PREMIUM_GARMIN_MODEL_RE = re.compile(r"(?:fenix|tactix|marq|epix)", re.IGNORECASE)
G_SHOP_WATCH_ML_COLUMNS = {
    "fake_grade": "INT NULL",
    "fake_proba": "FLOAT NULL",
}
_ENSURED_TABLE_COLUMNS: set[tuple[str, str]] = set()


def iter_chunks(values: list, size: int = SQL_IN_CHUNK_SIZE):
    for index in range(0, len(values), size):
        yield values[index : index + size]


def is_missing_value(value: object) -> bool:
    if value is None:
        return True

    try:
        return bool(pd.isna(value))
    except (TypeError, ValueError):
        return False


def generate_insert_on_duplicate(table_name: str, columns: list[str]) -> str:
    columns_str = ", ".join(columns)
    placeholders = ", ".join([f"%({col})s" for col in columns])
    update_str = ", ".join([f"{col} = VALUES({col})" for col in columns])

    query = f"""
    INSERT INTO {table_name}
    ({columns_str})
    VALUES
    ({placeholders})
    ON DUPLICATE KEY UPDATE
    {update_str}
    """
    return query.strip()


def bulk_insert(query: str, records: list[dict]) -> None:
    if not records:
        return

    cleaned_records = []
    for record in records:
        cleaned = {}
        for key, value in record.items():
            if is_missing_value(value):
                cleaned[key] = None
            else:
                cleaned[key] = value
        cleaned_records.append(cleaned)

    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.executemany(query, cleaned_records)
        conn.commit()
    finally:
        conn.close()


def select_df(query: str) -> pd.DataFrame:
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(query)
            rows = cursor.fetchall()
        return pd.DataFrame(rows)
    finally:
        conn.close()


def ensure_table_columns(table_name: str, columns: dict[str, str]) -> None:
    missing_columns: list[tuple[str, str]] = []
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            for column_name, column_definition in columns.items():
                cache_key = (table_name, column_name)
                if cache_key in _ENSURED_TABLE_COLUMNS:
                    continue

                cursor.execute(f"SHOW COLUMNS FROM `{table_name}` LIKE %s", (column_name,))
                if cursor.fetchone():
                    _ENSURED_TABLE_COLUMNS.add(cache_key)
                    continue

                cursor.execute(
                    f"ALTER TABLE `{table_name}` "
                    f"ADD COLUMN `{column_name}` {column_definition}"
                )
                _ENSURED_TABLE_COLUMNS.add(cache_key)
                missing_columns.append((column_name, column_definition))

        conn.commit()
    finally:
        conn.close()

    if missing_columns:
        added = ", ".join(f"{name} {definition}" for name, definition in missing_columns)
        logger.info(f"[DB] added missing columns to {table_name}: {added}")


class WatchDbWriterService:
    @classmethod
    def validate_input_columns(cls, df_res: pd.DataFrame) -> None:
        required_columns = [
            "Бренд",
            "article",
            "URL",
            "image_url",
            "price",
            "match_status",
            "matched_model_name",
            "size_mm",
        ]

        missing = [col for col in required_columns if col not in df_res.columns]
        if missing:
            raise ValueError(
                f"Для записи в БД не хватает обязательных колонок: {missing}"
            )
        
    @staticmethod
    def normalize_text(value: object) -> str:
        if is_missing_value(value):
            return ""
        return str(value).strip()

    @staticmethod
    def normalize_bool_01(value: object) -> Optional[bool]:
        if is_missing_value(value):
            return None

        if isinstance(value, bool):
            return value

        text = str(value).strip().lower()
        if text.endswith(".0"):
            text = text[:-2]

        if text in {"1", "true", "yes", "y", "new"}:
            return True
        if text in {"0", "false", "no", "n", "old", "used"}:
            return False

        return None

    @staticmethod
    def format_log_sample(values: list[str], limit: int = 5) -> str:
        sample = [str(value) for value in values[:limit]]
        suffix = "" if len(values) <= limit else f", ... +{len(values) - limit}"
        return ", ".join(sample) + suffix

    @classmethod
    def add_avito_row_state(cls, df_ready: pd.DataFrame, *, shop_id: int, batch_is_new: bool) -> pd.DataFrame:
        df_ready = df_ready.copy()

        if shop_id != AVITO_SHOP_ID:
            df_ready["_price_is_new"] = "Y" if batch_is_new else "N"
            df_ready["_condition_source_norm"] = BATCH_FALLBACK_SOURCE
            return df_ready

        raw_is_new = (
            df_ready["row_is_new"]
            if "row_is_new" in df_ready.columns
            else df_ready["is_new"] if "is_new" in df_ready.columns else pd.Series([None] * len(df_ready), index=df_ready.index)
        )
        raw_condition_source = (
            df_ready["condition_source"]
            if "condition_source" in df_ready.columns
            else pd.Series([None] * len(df_ready), index=df_ready.index)
        )

        parsed = raw_is_new.apply(cls.normalize_bool_01)
        fallback_mask = parsed.isna()
        resolved = parsed.where(~fallback_mask, batch_is_new)

        df_ready["_row_is_new_bool"] = resolved.astype(bool)
        df_ready["_price_is_new"] = df_ready["_row_is_new_bool"].map({True: "Y", False: "N"})
        df_ready["_condition_source_norm"] = raw_condition_source.apply(
            lambda value: cls.normalize_text(value).lower() or BATCH_FALLBACK_SOURCE
        )
        df_ready.loc[fallback_mask, "_condition_source_norm"] = BATCH_FALLBACK_SOURCE

        new_count = int((df_ready["_price_is_new"] == "Y").sum())
        used_count = int((df_ready["_price_is_new"] == "N").sum())
        fallback_count = int(fallback_mask.sum())
        logger.info(
            "[AVITO] is_new resolved from XLSX: "
            f"rows={len(df_ready)} new={new_count} used={used_count} filename_fallback={fallback_count}"
        )

        if "avito_condition" in df_ready.columns:
            condition_counts = (
                df_ready["avito_condition"]
                .apply(cls.normalize_text)
                .replace("", pd.NA)
                .dropna()
                .value_counts()
                .head(5)
                .to_dict()
            )
            if condition_counts:
                logger.info(f"[AVITO] avito_condition sample counts: {condition_counts}")

        return df_ready

    @classmethod
    def resolve_avito_duplicate_conflicts(cls, df_ready: pd.DataFrame, *, shop_id: int) -> pd.DataFrame:
        if shop_id != AVITO_SHOP_ID or df_ready.empty or "article" not in df_ready.columns:
            return df_ready

        df_ready = df_ready.copy()
        df_ready["article"] = df_ready["article"].apply(cls.normalize_text)
        keep_indices: list[int] = []
        duplicate_rows = 0
        resolved_conflicts = 0
        dropped_conflicts = 0
        dropped_articles: list[str] = []

        for article, group in df_ready.groupby("article", sort=False, dropna=False):
            if len(group) == 1:
                keep_indices.append(group.index[0])
                continue

            duplicate_rows += len(group) - 1
            states = set(group["_price_is_new"].tolist())
            if len(states) == 1:
                keep_indices.append(group.index[0])
                continue

            trusted = group[group["_condition_source_norm"] != BATCH_FALLBACK_SOURCE]
            trusted_states = set(trusted["_price_is_new"].tolist())
            if len(trusted) == 1 or len(trusted_states) == 1:
                keep_indices.append(trusted.index[0])
                resolved_conflicts += 1
                continue

            dropped_conflicts += 1
            dropped_articles.append(str(article))

        if duplicate_rows:
            logger.warning(f"[AVITO] duplicate ad_id rows in import: rows={duplicate_rows}")
        if resolved_conflicts:
            logger.warning(
                "[AVITO] is_new conflicts resolved by condition_source priority: "
                f"conflicts={resolved_conflicts}"
            )
        if dropped_conflicts:
            logger.error(
                "[AVITO] is_new conflicts dropped because no deterministic winner: "
                f"conflicts={dropped_conflicts} examples={cls.format_log_sample(dropped_articles)}"
            )

        return df_ready.loc[keep_indices].copy()

    @classmethod
    def fetch_price_states_for_shop_watch_ids(
        cls,
        shop_watch_ids: list[int],
        *,
        actual_date: date,
    ) -> dict[int, set[str]]:
        ids = sorted({int(value) for value in shop_watch_ids if not is_missing_value(value)})
        if not ids:
            return {}

        states: dict[int, set[str]] = {}
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                for chunk in iter_chunks(ids):
                    placeholders = ", ".join(["%s"] * len(chunk))
                    query = f"""
                    SELECT shop_watch_id, is_new
                    FROM g_watch_price
                    WHERE actual_date = %s
                      AND shop_watch_id IN ({placeholders})
                    """
                    cursor.execute(query, [actual_date, *chunk])
                    for row in cursor.fetchall():
                        shop_watch_id = int(row.get("shop_watch_id"))
                        states.setdefault(shop_watch_id, set()).add(str(row.get("is_new")))
        finally:
            conn.close()

        return states

    @classmethod
    def delete_price_states(
        cls,
        shop_watch_ids: list[int],
        *,
        actual_date: date,
        is_new_value: str,
    ) -> int:
        ids = sorted({int(value) for value in shop_watch_ids if not is_missing_value(value)})
        if not ids:
            return 0

        deleted = 0
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                for chunk in iter_chunks(ids):
                    placeholders = ", ".join(["%s"] * len(chunk))
                    query = f"""
                    DELETE FROM g_watch_price
                    WHERE actual_date = %s
                      AND is_new = %s
                      AND shop_watch_id IN ({placeholders})
                    """
                    cursor.execute(query, [actual_date, is_new_value, *chunk])
                    deleted += int(cursor.rowcount or 0)
            conn.commit()
        finally:
            conn.close()

        return deleted

    @classmethod
    def fetch_price_states_for_avito_articles(
        cls,
        articles: list[str],
        *,
        actual_date: date,
    ) -> dict[str, set[str]]:
        normalized_articles = sorted({cls.normalize_text(value) for value in articles if cls.normalize_text(value)})
        if not normalized_articles:
            return {}

        states: dict[str, set[str]] = {}
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                for chunk in iter_chunks(normalized_articles):
                    placeholders = ", ".join(["%s"] * len(chunk))
                    query = f"""
                    SELECT sw.article, wp.is_new
                    FROM g_watch_price wp
                    JOIN g_shop_watch sw ON sw.id = wp.shop_watch_id
                    WHERE sw.shop_id = %s
                      AND wp.actual_date = %s
                      AND sw.article IN ({placeholders})
                    """
                    cursor.execute(query, [AVITO_SHOP_ID, actual_date, *chunk])
                    for row in cursor.fetchall():
                        article = cls.normalize_text(row.get("article"))
                        if article:
                            states.setdefault(article, set()).add(str(row.get("is_new")))
        finally:
            conn.close()

        return states

    @classmethod
    def delete_price_states_for_avito_articles(
        cls,
        articles: list[str],
        *,
        actual_date: date,
        is_new_value: str,
    ) -> int:
        normalized_articles = sorted({cls.normalize_text(value) for value in articles if cls.normalize_text(value)})
        if not normalized_articles:
            return 0

        deleted = 0
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                for chunk in iter_chunks(normalized_articles):
                    placeholders = ", ".join(["%s"] * len(chunk))
                    query = f"""
                    DELETE wp
                    FROM g_watch_price wp
                    JOIN g_shop_watch sw ON sw.id = wp.shop_watch_id
                    WHERE sw.shop_id = %s
                      AND wp.actual_date = %s
                      AND wp.is_new = %s
                      AND sw.article IN ({placeholders})
                    """
                    cursor.execute(query, [AVITO_SHOP_ID, actual_date, is_new_value, *chunk])
                    deleted += int(cursor.rowcount or 0)
            conn.commit()
        finally:
            conn.close()

        return deleted

    @classmethod
    def protect_avito_price_state(
        cls,
        df_ready: pd.DataFrame,
        *,
        shop_id: int,
        actual_date: date,
    ) -> pd.DataFrame:
        if shop_id != AVITO_SHOP_ID or df_ready.empty:
            return df_ready

        df_ready = df_ready.copy()
        states = cls.fetch_price_states_for_avito_articles(
            df_ready["article"].tolist(),
            actual_date=actual_date,
        )
        if not states:
            return df_ready

        keep_mask = pd.Series(True, index=df_ready.index)
        authoritative_opposite: dict[str, list[str]] = {"Y": [], "N": []}
        skipped_fallback = 0

        for index, row in df_ready.iterrows():
            article = cls.normalize_text(row["article"])
            desired_state = str(row["_price_is_new"])
            opposite_state = "N" if desired_state == "Y" else "Y"
            existing_states = states.get(article, set())
            if opposite_state not in existing_states:
                continue

            if str(row.get("_condition_source_norm")) == BATCH_FALLBACK_SOURCE:
                keep_mask.loc[index] = False
                skipped_fallback += 1
                continue

            authoritative_opposite[opposite_state].append(article)

        for opposite_state, articles in authoritative_opposite.items():
            deleted = cls.delete_price_states_for_avito_articles(
                articles,
                actual_date=actual_date,
                is_new_value=opposite_state,
            )
            if deleted:
                logger.warning(
                    "[AVITO] removed opposite price state before insert: "
                    f"is_new={opposite_state} rows={deleted}"
                )

        if skipped_fallback:
            logger.warning(
                "[AVITO] skipped fallback rows because opposite is_new already exists for same date: "
                f"rows={skipped_fallback}"
            )

        return df_ready.loc[keep_mask].copy()

    @classmethod
    def normalize_brand(cls, brand: str | None) -> str | None:
        if not brand:
            return None
        return str(brand).strip()

    @classmethod
    def normalize_model_for_db(cls, model_name: str | None) -> str | None:
        """
        Храним model без пробелов, как просил Дмитрий.
        Пример:
        Galaxy Watch5 Pro -> galaxywatch5pro
        Watch GT 5 Pro -> watchgt5pro
        """
        if not model_name:
            return None

        value = str(model_name).strip().lower()
        value = value.replace("ё", "е")
        value = value.replace("+", "plus")
        value = re.sub(r"[\s\-/_,()]+", "", value)
        value = re.sub(r"[^a-z0-9]", "", value)

        return value or None

    @classmethod
    def normalize_size(cls, size_mm: object) -> int:
        """
        В БД size хранится числом:
        46, 41, 51
        если размер отсутствует -> 0
        """
        if pd.isna(size_mm) or size_mm is None or size_mm == "":
            return 0

        try:
            return int(size_mm)
        except Exception:
            return 0

    @classmethod
    def extract_review_number(cls, value: object) -> Optional[int]:
        if pd.isna(value) or value is None:
            return None

        if isinstance(value, (int, float)) and not isinstance(value, bool):
            return int(value)

        digits = re.sub(r"[^\d]", "", str(value))
        if not digits:
            return None

        try:
            return int(digits)
        except Exception:
            return None

    @classmethod
    def convert_warranty_to_days(cls, value: object) -> Optional[int]:
        if is_missing_value(value):
            return None

        text = str(value).lower().strip()
        if not text:
            return None

        text = text.replace("ё", "е")

        # Записываем только явный срок гарантии; просто слово "гарантия" оставляем NULL.
        match = re.search(
            r"(\d+)\s*"
            r"(дн(?:ей|я)?|день|дня|дней|days?|"
            r"мес(?:яц(?:ев|а)?)?|months?|"
            r"год|года|лет|years?)",
            text,
        )
        if match:
            num = int(match.group(1))
            unit = match.group(2)

            if num <= 0:
                return None

            if unit.startswith("дн") or unit in {"день", "дня", "дней"} or "day" in unit:
                return num if num <= MAX_WARRANTY_DAYS else None
            if unit.startswith("мес") or "month" in unit:
                return num * 30 if num <= MAX_WARRANTY_MONTHS else None
            if unit.startswith("год") or unit == "лет" or "year" in unit:
                return num * 365 if num <= MAX_WARRANTY_YEARS else None

        return None

    @classmethod
    def convert_days_to_delivery(cls, value: object) -> Optional[int]:
        if pd.isna(value) or value is None:
            return None

        text = str(value).strip()
        if not text:
            return None

        # Не вытаскиваем числа из постороннего текста вроде "38 отзывов".
        if not re.fullmatch(r"\d+(?:[.,]\d+)?", text) and not re.search(
            r"\b(день|дня|дней|day|days)\b",
            text.lower(),
        ):
            return None

        match = re.search(r"(\d+)", text)
        if not match:
            return None

        try:
            return int(match.group(1))
        except Exception:
            return None

    @classmethod
    def clean_color(cls, value: object) -> Optional[str]:
        if pd.isna(value) or value is None:
            return None

        text = str(value).strip()
        if not text or text == "—":
            return None

        return text[:40]

    @classmethod
    def normalize_article_for_db(cls, value: object, source: object = None, shop_id: object = None) -> Optional[str]:
        if is_missing_value(value):
            return None

        text = str(value).strip()
        if not text:
            return None

        source_text = str(source or "").strip().lower()
        is_dns = source_text == "dns" or str(shop_id or "").strip() == "6"

        if is_dns and re.fullmatch(r"[0-9a-f]{8,32}", text, re.IGNORECASE):
            digest = hashlib.blake2b(text.lower().encode("ascii"), digest_size=8).digest()
            article_id = int.from_bytes(digest, "big") & 0x7FFFFFFFFFFFFFFF
            return str(article_id or 1)

        return text

    @classmethod
    def article_matches_product_url(cls, row: pd.Series) -> bool:
        product_url = str(row.get("product_url") or "")
        article = str(row.get("article") or "")
        source_article = str(row.get("_source_article") or "")

        return bool(
            (article and article in product_url)
            or (source_article and source_article in product_url)
        )

    @classmethod
    def normalize_is_global(cls, value: object) -> str:
        if is_missing_value(value):
            return "N"

        text = str(value).strip().lower()
        if text in {"y", "yes", "true", "1", "да", "global", "глобальная", "глобальный"}:
            return "Y"

        return "N"

    @classmethod
    def normalize_fake_grade(cls, value: object) -> Optional[int]:
        if is_missing_value(value):
            return None

        try:
            return int(float(str(value).strip()))
        except (TypeError, ValueError):
            return None

    @classmethod
    def add_fake_ml_fields(
        cls,
        df_ready: pd.DataFrame,
        *,
        actual_date: date,
        shop_id: int,
    ) -> pd.DataFrame:
        df_ready = df_ready.copy()

        if "fake_grade" in df_ready.columns:
            df_ready["fake_grade"] = df_ready["fake_grade"].apply(cls.normalize_fake_grade)
        else:
            df_ready["fake_grade"] = None

        df_ready["fake_proba"] = None

        if shop_id != AVITO_SHOP_ID or df_ready.empty:
            return df_ready

        try:
            scored = add_fake_proba(df_ready.copy(), actual_date)
            df_ready.loc[scored.index, "fake_proba"] = scored["fake_proba"]
            logger.info(
                "[AVITO] fake_proba scored: "
                f"rows={int(scored['fake_proba'].notna().sum())}/{len(df_ready)}"
            )
        except Exception as err:
            logger.warning(f"[AVITO] fake_proba scoring skipped: {err}")

        return df_ready

    @classmethod
    def filter_avito_fake_price_rows(
        cls,
        df_ready: pd.DataFrame,
        *,
        shop_id: int,
    ) -> pd.DataFrame:
        if shop_id != AVITO_SHOP_ID or df_ready.empty or "fake_proba" not in df_ready.columns:
            return df_ready

        thresholds = load_thresholds()
        warn_threshold = float(thresholds.get("warn", 0.7))
        fake_proba = pd.to_numeric(df_ready["fake_proba"], errors="coerce")
        drop_mask = fake_proba >= warn_threshold
        if not drop_mask.any():
            return df_ready

        dropped = df_ready.loc[drop_mask].copy()
        tier_counts = {
            "risk": int((fake_proba.loc[drop_mask] >= float(thresholds.get("risk", 0.9))).sum()),
            "warn": int((fake_proba.loc[drop_mask] < float(thresholds.get("risk", 0.9))).sum()),
        }
        logger.warning(
            "[AVITO] skipped fake-like rows before g_watch_price insert: "
            f"rows={len(dropped)} warn_threshold={warn_threshold} tiers={tier_counts}"
        )

        return df_ready.loc[~drop_mask].copy()

    @classmethod
    def build_avito_price_quarantine_mask(
        cls,
        df_ready: pd.DataFrame,
        *,
        shop_id: int,
    ) -> pd.Series:
        if shop_id != AVITO_SHOP_ID or df_ready.empty:
            return pd.Series(False, index=df_ready.index)

        mask = pd.Series(False, index=df_ready.index)

        if "fake_proba" in df_ready.columns:
            thresholds = load_thresholds()
            warn_threshold = float(thresholds.get("warn", 0.7))
            fake_proba = pd.to_numeric(df_ready["fake_proba"], errors="coerce")
            mask = mask | (fake_proba >= warn_threshold)

        required_columns = {"brand", "model", "price"}
        if required_columns.issubset(df_ready.columns):
            brand = df_ready["brand"].astype(str).str.strip().str.lower()
            model = df_ready["model"].astype(str).str.strip().str.lower()
            price = pd.to_numeric(df_ready["price"], errors="coerce")

            apple_premium = (brand == "apple") & model.isin(AVITO_PREMIUM_APPLE_MODELS)
            garmin_premium = (brand == "garmin") & model.str.contains(
                AVITO_PREMIUM_GARMIN_MODEL_RE,
                na=False,
            )
            low_premium_price = (
                price.notna()
                & (price <= AVITO_PREMIUM_LOW_PRICE_CEIL_RUB)
                & (apple_premium | garmin_premium)
            )
            mask = mask | low_premium_price

        return mask

    @classmethod
    def delete_prices_for_shop_watch_ids(
        cls,
        shop_watch_ids: list[int],
        *,
        shop_id: int,
    ) -> int:
        ids = sorted({int(value) for value in shop_watch_ids if not is_missing_value(value)})
        if not ids:
            return 0

        deleted = 0
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                for chunk in iter_chunks(ids):
                    placeholders = ", ".join(["%s"] * len(chunk))
                    query = f"""
                    DELETE wp
                    FROM g_watch_price wp
                    JOIN g_shop_watch sw ON sw.id = wp.shop_watch_id
                    WHERE sw.shop_id = %s
                      AND wp.shop_watch_id IN ({placeholders})
                    """
                    cursor.execute(query, [shop_id, *chunk])
                    deleted += int(cursor.rowcount or 0)
            conn.commit()
        finally:
            conn.close()

        return deleted

    @classmethod
    def cleanup_avito_quarantined_price_history(
        cls,
        df_ready: pd.DataFrame,
        *,
        shop_id: int,
    ) -> int:
        if shop_id != AVITO_SHOP_ID or df_ready.empty or "shop_watch_id" not in df_ready.columns:
            return 0

        quarantine_mask = cls.build_avito_price_quarantine_mask(df_ready, shop_id=shop_id)
        if not quarantine_mask.any():
            return 0

        quarantined_ids = df_ready.loc[quarantine_mask, "shop_watch_id"].dropna().tolist()
        deleted = cls.delete_prices_for_shop_watch_ids(quarantined_ids, shop_id=shop_id)
        logger.warning(
            "[AVITO] deleted historical prices for quarantined rows: "
            f"shop_watch_ids={len(set(quarantined_ids))} deleted_prices={deleted}"
        )
        return deleted

    @classmethod
    def filter_avito_quarantined_price_rows(
        cls,
        df_ready: pd.DataFrame,
        *,
        shop_id: int,
    ) -> pd.DataFrame:
        if shop_id != AVITO_SHOP_ID or df_ready.empty:
            return df_ready

        quarantine_mask = cls.build_avito_price_quarantine_mask(df_ready, shop_id=shop_id)
        if not quarantine_mask.any():
            return df_ready

        dropped = df_ready.loc[quarantine_mask].copy()
        reasons = {
            "fake_like": 0,
            "low_premium_price": 0,
        }

        if "fake_proba" in df_ready.columns:
            thresholds = load_thresholds()
            warn_threshold = float(thresholds.get("warn", 0.7))
            fake_proba = pd.to_numeric(df_ready["fake_proba"], errors="coerce")
            reasons["fake_like"] = int((fake_proba >= warn_threshold).sum())

        if {"brand", "model", "price"}.issubset(df_ready.columns):
            brand = df_ready["brand"].astype(str).str.strip().str.lower()
            model = df_ready["model"].astype(str).str.strip().str.lower()
            price = pd.to_numeric(df_ready["price"], errors="coerce")
            premium_mask = (
                ((brand == "apple") & model.isin(AVITO_PREMIUM_APPLE_MODELS))
                | (
                    (brand == "garmin")
                    & model.str.contains(AVITO_PREMIUM_GARMIN_MODEL_RE, na=False)
                )
            )
            reasons["low_premium_price"] = int(
                (price.notna() & (price <= AVITO_PREMIUM_LOW_PRICE_CEIL_RUB) & premium_mask).sum()
            )

        logger.warning(
            "[AVITO] skipped quarantined rows before g_watch_price insert: "
            f"rows={len(dropped)} reasons={reasons}"
        )

        return df_ready.loc[~quarantine_mask].copy()

    @classmethod
    def prepare_matched_rows(cls, df_res: pd.DataFrame) -> pd.DataFrame:
        df = df_res.copy()
        start_count = len(df)

        df = df[df["match_status"] == "matched"].copy()
        after_match_status = len(df)
        df = df[df["matched_model_name"].notna()].copy()
        after_model_name = len(df)
        df = df[df["Бренд"].notna()].copy()
        after_brand = len(df)
        df = df[df["article"].notna()].copy()
        after_article = len(df)
        df = df[df["URL"].notna()].copy()
        after_url = len(df)
        rows_without_price = df[df["price"].isna()].copy()
        df = df[df["price"].notna()].copy()
        after_price_present = len(df)

        if not rows_without_price.empty:
            source_counts = (
                rows_without_price["source"].fillna("unknown").astype(str).value_counts().head(5).to_dict()
                if "source" in rows_without_price.columns
                else {}
            )
            sample_columns = [
                col
                for col in ["source", "shop_id", "article", "URL", "matched_model_name"]
                if col in rows_without_price.columns
            ]
            sample = rows_without_price[sample_columns].head(5).to_dict(orient="records")
            logger.warning(
                "[DB] matched rows without price skipped before insert: "
                f"count={len(rows_without_price)} | sources={source_counts} | sample={sample}"
            )

        df["brand"] = df["Бренд"].apply(cls.normalize_brand)
        df["model"] = df["matched_model_name"].apply(cls.normalize_model_for_db)
        df["size"] = df["size_mm"].apply(cls.normalize_size)

        df["product_url"] = df["URL"].astype(str).str.strip()
        df["image_url"] = df["image_url"]
        df["_source_article"] = df["article"].astype(str).str.strip()
        df["article"] = df.apply(
            lambda row: cls.normalize_article_for_db(
                row.get("_source_article"),
                source=row.get("source"),
                shop_id=row.get("shop_id"),
            ),
            axis=1,
        )

        df["price"] = pd.to_numeric(df["price"], errors="coerce")
        df["rating"] = None

        if "shop_rating" in df.columns:
            df["shop_rating"] = pd.to_numeric(df["shop_rating"], errors="coerce")
        else:
            df["shop_rating"] = None

        if "review" in df.columns:
            df["review"] = df["review"].apply(cls.extract_review_number)
        else:
            df["review"] = None

        if "Гарантия" in df.columns:
            df["warranty_period"] = df["Гарантия"].apply(cls.convert_warranty_to_days)
        else:
            df["warranty_period"] = None

        if "days_to_delivery" in df.columns:
            df["days_to_delivery"] = df["days_to_delivery"].apply(cls.convert_days_to_delivery)
        else:
            df["days_to_delivery"] = None

        if "Цвет" in df.columns:
            df["color"] = df["Цвет"].apply(cls.clean_color)
        else:
            df["color"] = None

        if "is_global" in df.columns:
            df["is_global"] = df["is_global"].apply(cls.normalize_is_global)
        else:
            df["is_global"] = "N"

        if "currency" in df.columns:
            df["currency"] = df["currency"].fillna("RUB")
        else:
            df["currency"] = "RUB"

        if "tax_price" in df.columns:
            df["tax_price"] = pd.to_numeric(df["tax_price"], errors="coerce")
        else:
            df["tax_price"] = None
        df["ali_affiliate_url"] = None

        if "fake_grade" in df.columns:
            df["fake_grade"] = df["fake_grade"].apply(cls.normalize_fake_grade)
        else:
            df["fake_grade"] = None
        df["fake_proba"] = None

        df = df[df["brand"].notna() & (df["brand"] != "")]
        after_normalized_brand = len(df)
        df = df[df["model"].notna() & (df["model"] != "")]
        after_normalized_model = len(df)
        df = df[df["product_url"].notna() & (df["product_url"] != "")]
        after_product_url = len(df)
        df = df[df["article"].notna() & (df["article"] != "")]
        after_article_text = len(df)
        df = df[df["price"].notna()]
        after_price_numeric = len(df)
        bad_price_mask = (df["price"] <= 0) | (df["price"] > MAX_REASONABLE_PRICE_RUB)
        if bad_price_mask.any():
            logger.warning(
                "[DB] skipped rows with suspicious price before insert: "
                f"count={int(bad_price_mask.sum())} | max_allowed={MAX_REASONABLE_PRICE_RUB}"
            )
        df = df[~bad_price_mask].copy()
        after_price_reasonable = len(df)

        df = df[df.apply(cls.article_matches_product_url, axis=1)].copy()
        after_article_in_url = len(df)

        logger.info(
            "[БД] prepare_matched_rows funnel: "
            f"start={start_count} -> match_status={after_match_status} -> matched_model={after_model_name} "
            f"-> brand={after_brand} -> article={after_article} -> url={after_url} "
            f"-> price_present={after_price_present} -> normalized_brand={after_normalized_brand} "
            f"-> normalized_model={after_normalized_model} -> product_url={after_product_url} "
            f"-> article_text={after_article_text} -> price_numeric={after_price_numeric} "
            f"-> price_reasonable={after_price_reasonable} -> article_in_url={after_article_in_url}"
        )

        return df

    @classmethod
    def insert_g_watch(cls, df_ready: pd.DataFrame) -> None:
        df_watch = df_ready[["brand", "model", "size"]].drop_duplicates().copy()

        query = """
        INSERT IGNORE INTO g_watch (brand, model, size)
        VALUES (%(brand)s, %(model)s, %(size)s)
        """

        columns = ["brand", "model", "size"]

        records = (
            df_watch[columns]
            .replace({pd.NA: None})
            .where(pd.notnull(df_watch[columns]), None)
            .to_dict(orient="records")
        )

        bulk_insert(query, records)

    @classmethod
    def attach_watch_id(cls, df_ready: pd.DataFrame) -> pd.DataFrame:
        g_watch_df = select_df("SELECT id, brand, model, size FROM g_watch")

        if g_watch_df.empty:
            raise ValueError("g_watch пустая после вставки")

        df_ready = df_ready.copy()
        g_watch_df = g_watch_df.copy()

        for col in ["brand", "model"]:
            df_ready[col] = df_ready[col].astype(str).str.strip().str.lower()
            g_watch_df[col] = g_watch_df[col].astype(str).str.strip().str.lower()

        df_ready["size"] = pd.to_numeric(df_ready["size"], errors="coerce").fillna(0).astype(int)
        g_watch_df["size"] = pd.to_numeric(g_watch_df["size"], errors="coerce").fillna(0).astype(int)

        df_merged = df_ready.merge(
            g_watch_df[["id", "brand", "model", "size"]],
            how="inner",
            on=["brand", "model", "size"],
        ).rename(columns={"id": "watch_id"})

        return df_merged

    @classmethod
    def insert_g_shop_watch(cls, df_ready: pd.DataFrame, shop_id: int) -> None:
        df_ready = df_ready.copy()
        df_ready["shop_id"] = shop_id
        cls.ensure_g_shop_watch_ml_columns()

        columns = [
            "watch_id",
            "shop_id",
            "product_url",
            "image_url",
            "rating",
            "shop_rating",
            "review",
            "is_global",
            "warranty_period",
            "color",
            "article",
            "days_to_delivery",
            "ali_affiliate_url",
            "fake_grade",
            "fake_proba",
        ]

        query = generate_insert_on_duplicate("g_shop_watch", columns)

        records = (
            df_ready[columns]
            .where(pd.notnull(df_ready[columns]), None)
            .to_dict(orient="records")
        )

        bulk_insert(query, records)

    @classmethod
    def ensure_g_shop_watch_ml_columns(cls) -> None:
        ensure_table_columns("g_shop_watch", G_SHOP_WATCH_ML_COLUMNS)

    @classmethod
    def attach_shop_watch_id(cls, df_ready: pd.DataFrame, shop_id: int) -> pd.DataFrame:
        g_shop_watch_df = select_df(
            "SELECT id AS shop_watch_id, watch_id, shop_id, article FROM g_shop_watch"
        )

        df_ready = df_ready.copy()
        g_shop_watch_df = g_shop_watch_df.copy()

        df_ready["shop_id"] = shop_id
        df_ready["article"] = df_ready["article"].astype(str).str.strip()
        g_shop_watch_df["article"] = g_shop_watch_df["article"].astype(str).str.strip()

        df_merged = df_ready.merge(
            g_shop_watch_df,
            how="inner",
            on=["watch_id", "shop_id", "article"],
        )

        return df_merged

    @classmethod
    def insert_g_watch_price(
        cls,
        df_ready: pd.DataFrame,
        actual_date: date,
        is_new: bool,
    ) -> None:
        df_ready = df_ready.copy()
        df_ready["actual_date"] = actual_date
        if "_price_is_new" in df_ready.columns:
            df_ready["is_new"] = df_ready["_price_is_new"]
        else:
            df_ready["is_new"] = "Y" if is_new else "N"

        columns = [
            "shop_watch_id",
            "price",
            "tax_price",
            "currency",
            "actual_date",
            "is_new",
        ]

        query = generate_insert_on_duplicate("g_watch_price", columns)

        records = (
            df_ready[columns]
            .where(pd.notnull(df_ready[columns]), None)
            .to_dict(orient="records")
        )

        bulk_insert(query, records)

        type_counts = df_ready["is_new"].value_counts().to_dict()
        logger.info(f"[DB] price is_new counts: {type_counts}")

        logger.info(
            f"[БД] цены записаны: {len(records)} | "
            f"магазин={SHOP_NAMES.get(df_ready['shop_id'].iloc[0], 'неизвестно')} | "
            f"тип={'НОВЫЕ' if is_new else 'БУ'}"
        )

    @classmethod
    def prepare_and_write_watch_data_to_db(
        cls,
        df_res: pd.DataFrame,
        actual_date: date,
        shop_id: int,
        is_new: bool,
    ) -> None:
        cls.validate_input_columns(df_res)
        df_ready = cls.prepare_matched_rows(df_res)
        df_ready = cls.add_avito_row_state(df_ready, shop_id=shop_id, batch_is_new=is_new)
        df_ready = cls.resolve_avito_duplicate_conflicts(df_ready, shop_id=shop_id)

        logger.info(f"[БД] строк после подготовки: {len(df_ready)}")

        if df_ready.empty:
            logger.warning("Нет строк для записи в БД")
            return

        cls.insert_g_watch(df_ready)
        df_ready = cls.attach_watch_id(df_ready)
        df_ready = cls.add_fake_ml_fields(
            df_ready,
            actual_date=actual_date,
            shop_id=shop_id,
        )

        logger.info(f"[БД] строк после привязки идентификатора watch_id: {len(df_ready)}")

        if df_ready.empty:
            logger.warning("После объединения с g_watch не осталось строк")
            return

        cls.insert_g_shop_watch(df_ready, shop_id=shop_id)
        df_ready = cls.attach_shop_watch_id(df_ready, shop_id=shop_id)

        logger.info(f"[БД] строк после привязки идентификатора shop_watch_id: {len(df_ready)}")

        if df_ready.empty:
            logger.warning("После объединения с g_shop_watch не осталось строк")
            return

        df_ready = cls.protect_avito_price_state(
            df_ready,
            shop_id=shop_id,
            actual_date=actual_date,
        )

        if df_ready.empty:
            logger.warning("[AVITO] no rows left after is_new conflict protection")
            return

        cls.cleanup_avito_quarantined_price_history(df_ready, shop_id=shop_id)
        df_ready = cls.filter_avito_quarantined_price_rows(df_ready, shop_id=shop_id)

        if df_ready.empty:
            logger.warning("[AVITO] no rows left after quarantined price filtering")
            return

        cls.insert_g_watch_price(
            df_ready=df_ready,
            actual_date=actual_date,
            is_new=is_new,
        )

    @classmethod
    def prepare_and_write_watch_new_and_used_to_db(
        cls,
        df_new: pd.DataFrame,
        df_used: pd.DataFrame,
        actual_date: date,
        shop_id: int = 2,
    ) -> None:
        logger.info("=== Запись НОВЫХ часов ===")
        cls.prepare_and_write_watch_data_to_db(
            df_res=df_new,
            actual_date=actual_date,
            shop_id=shop_id,
            is_new=True,
        )

        logger.info("=== Запись Б/У часов ===")
        cls.prepare_and_write_watch_data_to_db(
            df_res=df_used,
            actual_date=actual_date,
            shop_id=shop_id,
            is_new=False,
        )
