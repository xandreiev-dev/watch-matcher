from __future__ import annotations

import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from app.core.logging_config import get_logger
from app.ml.watch_text_features import extract_all_watch, norm_text


logger = get_logger("watch_fake_runtime")

HERE = Path(__file__).resolve().parent
MODEL_PATH = HERE / "artifacts" / "watch_fake_detector.cbm"
THRESHOLDS_PATH = HERE / "artifacts" / "watch_fake_detector_thresholds.json"

TRAIL_DAYS = 30
MIN_ANCHOR_N = 8
REPLICA_PRICE_CEIL = 6500.0

CAT_FEATURES = ["brand"]
TEXT_FEATURES = ["title", "description"]

_model_cache = None


def select_df(sql: str) -> pd.DataFrame:
    from app.core.db import get_db_connection

    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(sql)
            rows = cursor.fetchall()
        return pd.DataFrame(rows)
    finally:
        conn.close()


def _col(df: pd.DataFrame, *names: str, default: Any = "") -> pd.Series:
    for name in names:
        if name in df.columns:
            return df[name]
    return pd.Series(default, index=df.index)


def _parse_reviews(value: object) -> float:
    text = re.sub(r"[^\d]", "", str(value or ""))
    return float(text) if text else np.nan


def _norm_alnum(value: object) -> str:
    return re.sub(r"[^a-z0-9]", "", str(value or "").lower())


def _split_two_clusters(log_prices: np.ndarray, iters: int = 20) -> tuple[np.ndarray, np.ndarray]:
    lo, hi = np.percentile(log_prices, [20, 80])
    if hi - lo < 1e-9:
        return np.ones_like(log_prices, dtype=bool), np.array([lo, hi])

    centers = np.array([lo, hi], dtype=float)
    for _ in range(iters):
        upper = np.abs(log_prices - centers[1]) < np.abs(log_prices - centers[0])
        if upper.all() or (~upper).all():
            break
        new_centers = np.array([log_prices[~upper].mean(), log_prices[upper].mean()])
        if np.allclose(new_centers, centers):
            centers = new_centers
            break
        centers = new_centers

    upper = np.abs(log_prices - centers[1]) < np.abs(log_prices - centers[0])
    return upper, centers


def robust_anchor(prices: list[float], min_n: int = MIN_ANCHOR_N) -> tuple[float, int]:
    positive = np.asarray([price for price in prices if price and price > 0], dtype=float)
    if len(positive) < min_n:
        return np.nan, len(positive)

    log_prices = np.log(positive)
    upper, centers = _split_two_clusters(log_prices)
    separation = float(np.exp(abs(centers[1] - centers[0])))
    if separation >= 2.2 and upper.sum() >= 3 and (~upper).sum() >= 3:
        median_upper = float(np.exp(np.median(log_prices[upper])))
        median_lower = float(np.exp(np.median(log_prices[~upper])))
        if median_lower <= REPLICA_PRICE_CEIL:
            return median_upper, int(upper.sum())

    for _ in range(2):
        q1, q3 = np.quantile(log_prices, 0.25), np.quantile(log_prices, 0.75)
        iqr = q3 - q1
        keep = (log_prices >= q1 - 1.5 * iqr) & (log_prices <= q3 + 1.5 * iqr)
        if keep.all() or keep.sum() < min_n:
            break
        log_prices = log_prices[keep]

    return float(np.exp(np.median(log_prices))), int(len(log_prices))


def _fetch_trailing(actual_date, articles: list, trail_days: int = TRAIL_DAYS) -> tuple[pd.DataFrame, pd.DataFrame]:
    date_text = pd.to_datetime(actual_date).strftime("%Y-%m-%d")
    trail = select_df(
        f"""
        SELECT sw.watch_id, w.brand, w.model,
               (wp.price + IFNULL(wp.tax_price, 0)) AS eff_price
        FROM g_watch_price wp
        JOIN g_shop_watch sw ON sw.id = wp.shop_watch_id
        JOIN g_watch w ON w.id = sw.watch_id
        WHERE sw.shop_id = 2 AND wp.is_new = 'Y'
          AND wp.actual_date >= DATE_SUB('{date_text}', INTERVAL {trail_days} DAY)
          AND wp.actual_date < '{date_text}'
        """
    )

    article_ids = [
        str(int(article))
        for article in articles
        if article is not None and str(article).strip().lstrip("-").isdigit()
    ]

    history_frames = []
    for start in range(0, len(article_ids), 5000):
        chunk = ",".join(article_ids[start : start + 5000])
        if not chunk:
            continue
        history_frames.append(
            select_df(
                f"""
                SELECT sw.article,
                       COUNT(DISTINCT wp.actual_date) AS days_seen,
                       MIN(wp.actual_date) AS first_seen,
                       MIN(wp.price + IFNULL(wp.tax_price, 0)) AS hist_min,
                       MAX(wp.price + IFNULL(wp.tax_price, 0)) AS hist_max
                FROM g_watch_price wp
                JOIN g_shop_watch sw ON sw.id = wp.shop_watch_id
                WHERE sw.shop_id = 2 AND wp.is_new = 'Y'
                  AND wp.actual_date < '{date_text}' AND sw.article IN ({chunk})
                GROUP BY sw.article
                """
            )
        )

    if history_frames:
        article_history = pd.concat(history_frames, ignore_index=True)
    else:
        article_history = pd.DataFrame(
            columns=["article", "days_seen", "first_seen", "hist_min", "hist_max"]
        )
    return trail, article_history


def _normalize_online_rows(df: pd.DataFrame) -> pd.DataFrame:
    rows = pd.DataFrame(index=df.index)
    rows["article"] = df["article"].astype(str)
    rows["watch_id"] = df.get("watch_id")
    rows["title"] = _col(df, "Название", "title").map(norm_text)
    rows["description"] = _col(df, "Описание", "description").map(norm_text)
    rows["brand"] = _col(df, "brand", default="unknown").fillna("unknown")
    rows["model"] = _col(df, "model")
    rows["size"] = df.get("size")
    rows["price"] = pd.to_numeric(df.get("price"), errors="coerce")
    rows["seller"] = _col(df, "Продавец", "seller").astype(str).str.strip().str.lower().replace("nan", "")
    rows["seller_rating"] = pd.to_numeric(_col(df, "shop_rating", "Рейтинг продавца"), errors="coerce")
    rows["seller_reviews"] = _col(df, "review", "Отзывы").map(_parse_reviews)
    rows["pub_date"] = pd.to_datetime(_col(df, "Дата публикации"), errors="coerce")
    rows["bump_date"] = pd.to_datetime(_col(df, "Поднято"), errors="coerce")
    images = _col(df, "image_url", "Изображения")
    rows["n_images"] = images.astype(str).str.count(";").fillna(0) + 1
    return rows


def _finalize_features(
    rows: pd.DataFrame,
    dev_anchor: dict,
    model_anchor: dict,
    article_history: dict,
    seller_counts: pd.Series,
    actual_date,
) -> pd.DataFrame:
    current_date = pd.to_datetime(actual_date)
    out = pd.DataFrame(index=rows.index)
    out["article"] = rows["article"]
    out["watch_id"] = rows.get("watch_id")
    out["title"] = rows["title"]
    out["description"] = rows["description"]
    out["brand"] = rows["brand"].fillna("unknown")

    price = pd.to_numeric(rows["price"], errors="coerce")
    out["price"] = price
    out["log_price"] = np.log1p(price)

    anchors, anchor_ns = [], []
    for watch_id, brand, model in zip(
        rows.get("watch_id"),
        rows["brand"],
        rows.get("model", pd.Series("", index=rows.index)),
    ):
        anchor, count = np.nan, 0
        if pd.notna(watch_id) and int(watch_id) in dev_anchor:
            anchor, count = dev_anchor[int(watch_id)]
        if not (anchor == anchor):
            brand_model = (str(brand or "").strip().lower(), str(model or "").strip().lower())
            anchor, count = model_anchor.get(brand_model, (np.nan, 0))
        anchors.append(anchor)
        anchor_ns.append(count)

    out["anchor_price"] = anchors
    out["anchor_n"] = anchor_ns
    out["ratio_anchor"] = out["price"] / out["anchor_price"]
    out["is_replica_priced"] = (out["price"] <= REPLICA_PRICE_CEIL).astype(int)

    out["seller_rating"] = pd.to_numeric(rows.get("seller_rating"), errors="coerce")
    out["seller_reviews"] = pd.to_numeric(rows.get("seller_reviews"), errors="coerce")
    out["has_seller_stats"] = out["seller_rating"].notna().astype(int)

    seller = rows.get("seller", pd.Series("", index=rows.index)).fillna("")
    out["seller_n_articles"] = seller.map(seller_counts).fillna(0)
    seller_mean_ratio = out.assign(_seller=seller.values).groupby("_seller")["ratio_anchor"].transform("mean")
    out["seller_mean_ratio"] = seller_mean_ratio.where(seller.values != "", np.nan)

    desc_key = out["description"].astype(str).str[:120]
    duplicate_counts = desc_key.value_counts()
    out["desc_dup_count"] = desc_key.map(duplicate_counts).where(desc_key.str.len() > 20, 1)

    pub_date = pd.to_datetime(rows.get("pub_date"), errors="coerce")
    bump_date = pd.to_datetime(rows.get("bump_date"), errors="coerce")
    out["days_since_pub"] = (current_date - pub_date).dt.total_seconds() / 86400
    out["days_since_bump"] = (current_date - bump_date).dt.total_seconds() / 86400
    out["n_images"] = pd.to_numeric(rows.get("n_images"), errors="coerce").fillna(1)

    days_seen, age_days, spread = [], [], []
    for article in rows["article"]:
        history = article_history.get(str(article))
        if history and history.get("days_seen"):
            days_seen.append(history["days_seen"])
            first_seen = history.get("first_seen")
            age_days.append(
                (current_date - pd.to_datetime(first_seen)).days
                if first_seen is not None and pd.notna(first_seen)
                else 0
            )
            hist_min, hist_max = history.get("hist_min", np.nan), history.get("hist_max", np.nan)
            spread.append(((hist_max - hist_min) / hist_max) if hist_max and hist_max == hist_max and hist_max > 0 else 0.0)
        else:
            days_seen.append(0)
            age_days.append(0)
            spread.append(0.0)

    out["days_seen_before"] = days_seen
    out["age_days"] = age_days
    out["hist_price_spread"] = spread

    hist_min_by_article = {
        article: (article_history.get(str(article)) or {}).get("hist_min", np.nan)
        for article in rows["article"]
    }
    out["price_vs_hist_min"] = [
        (price_value / hist_min_by_article[article])
        if hist_min_by_article[article]
        and hist_min_by_article[article] == hist_min_by_article[article]
        and hist_min_by_article[article] > 0
        else np.nan
        for article, price_value in zip(rows["article"], price)
    ]

    text_features = pd.DataFrame(
        [extract_all_watch(title, description) for title, description in zip(rows["title"], rows["description"])],
        index=rows.index,
    )
    out = pd.concat([out, text_features], axis=1)

    norm_title = rows["title"].map(_norm_alnum)
    norm_model = rows.get("model", pd.Series("", index=rows.index)).map(_norm_alnum)
    out["title_has_model"] = [int(bool(model) and model in title) for model, title in zip(norm_model, norm_title)]

    sizes_in_title = rows["title"].map(
        lambda value: {int(size) for size in re.findall(r"\b(\d{2})\s?(?:mm|мм)\b", str(value or "").lower())}
    )
    card_size = pd.to_numeric(rows.get("size"), errors="coerce").fillna(0).astype(int)
    out["title_size_match"] = [int(size in title_sizes) if size and title_sizes else 0 for size, title_sizes in zip(card_size, sizes_in_title)]
    out["title_other_size"] = [int(bool(title_sizes) and size not in title_sizes) if size else 0 for size, title_sizes in zip(card_size, sizes_in_title)]

    return out


def build_features(df_ready: pd.DataFrame, actual_date) -> pd.DataFrame:
    df = df_ready.copy()
    df["article"] = df["article"].astype(str)

    trail, article_history_df = _fetch_trailing(actual_date, df["article"].tolist())

    dev_pool: dict[int, list[float]] = defaultdict(list)
    model_pool: dict[tuple, list[float]] = defaultdict(list)
    if len(trail):
        trail["eff_price"] = pd.to_numeric(trail["eff_price"], errors="coerce")
        for watch_id, group in trail.groupby("watch_id"):
            prices = group["eff_price"].dropna().tolist()
            dev_pool[int(watch_id)].extend(prices)
            model_pool[
                (
                    str(group["brand"].iloc[0]).strip().lower(),
                    str(group["model"].iloc[0]).strip().lower(),
                )
            ].extend(prices)

    current_prices = pd.to_numeric(df.get("price"), errors="coerce")
    today_pool: dict[int, list[float]] = defaultdict(list)
    for watch_id, price in zip(df.get("watch_id", pd.Series(dtype=float)), current_prices):
        if pd.notna(watch_id) and pd.notna(price):
            today_pool[int(watch_id)].append(float(price))
    for watch_id, prices in today_pool.items():
        dev_pool[watch_id].extend(prices)

    if "watch_id" in df.columns:
        brand_model_by_watch = df.dropna(subset=["watch_id"]).groupby("watch_id")[["brand", "model"]].first()
        for watch_id, prices in today_pool.items():
            if watch_id in brand_model_by_watch.index:
                brand_model = (
                    str(brand_model_by_watch.loc[watch_id, "brand"]).strip().lower(),
                    str(brand_model_by_watch.loc[watch_id, "model"]).strip().lower(),
                )
                model_pool[brand_model].extend(prices)

    dev_anchor = {watch_id: robust_anchor(prices) for watch_id, prices in dev_pool.items()}
    model_anchor = {brand_model: robust_anchor(prices) for brand_model, prices in model_pool.items()}

    article_history: dict[str, dict] = {}
    for _, row in article_history_df.iterrows():
        article_history[str(row["article"])] = {
            "days_seen": int(row["days_seen"]),
            "first_seen": row["first_seen"],
            "hist_min": float(row["hist_min"]) if row["hist_min"] is not None else np.nan,
            "hist_max": float(row["hist_max"]) if row["hist_max"] is not None else np.nan,
        }

    rows = _normalize_online_rows(df)
    seller_counts = rows["seller"].value_counts()
    return _finalize_features(rows, dev_anchor, model_anchor, article_history, seller_counts, actual_date)


def feature_frame(df: pd.DataFrame) -> pd.DataFrame:
    drop_cols = {"article", "watch_id", "url", "file_date", "label", "sublabel", "source", "comment", "y", "w"}
    features = df.drop(columns=[column for column in drop_cols if column in df.columns])
    for column in CAT_FEATURES:
        features[column] = features[column].fillna("unknown").astype(str)
    for column in TEXT_FEATURES:
        features[column] = features[column].fillna("")
    numeric_columns = [column for column in features.columns if column not in CAT_FEATURES and column not in TEXT_FEATURES]
    for column in numeric_columns:
        features[column] = pd.to_numeric(features[column], errors="coerce")
    return features


def make_pool(features: pd.DataFrame):
    from catboost import Pool

    return Pool(
        features,
        cat_features=[features.columns.get_loc(column) for column in CAT_FEATURES if column in features.columns],
        text_features=[features.columns.get_loc(column) for column in TEXT_FEATURES if column in features.columns],
    )


def get_model():
    global _model_cache
    if _model_cache is None:
        from catboost import CatBoostClassifier

        if not MODEL_PATH.exists():
            raise RuntimeError(f"watch fake model is missing: {MODEL_PATH}")

        model = CatBoostClassifier()
        model.load_model(str(MODEL_PATH))
        _model_cache = model
    return _model_cache


def load_thresholds() -> dict:
    if THRESHOLDS_PATH.exists():
        return json.loads(THRESHOLDS_PATH.read_text(encoding="utf-8"))
    return {"risk": 0.9, "warn": 0.7}


def add_fake_proba(df_ready: pd.DataFrame, actual_date) -> pd.DataFrame:
    model = get_model()
    features = build_features(df_ready, actual_date)
    names = model.feature_names_
    missing = [column for column in names if column not in features.columns]
    if missing:
        raise ValueError(f"watch_fake_runtime: missing features {missing}")

    pool = make_pool(feature_frame(features)[names])
    out = df_ready.copy()
    out["fake_proba"] = np.round(model.predict_proba(pool)[:, 1], 6)
    return out
