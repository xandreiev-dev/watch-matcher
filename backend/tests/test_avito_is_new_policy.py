import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import app.services.watch_db_writer_service as db_writer
from app.services.watch_db_writer_service import WatchDbWriterService


def test_avito_xlsx_is_new_overrides_new_filename_fallback():
    df = pd.DataFrame(
        [
            {
                "article": "123",
                "row_is_new": 0,
                "condition_source": "parser_condition",
            }
        ]
    )

    result = WatchDbWriterService.add_avito_row_state(df, shop_id=2, batch_is_new=True)

    assert result.loc[0, "_price_is_new"] == "N"
    assert result.loc[0, "_condition_source_norm"] == "parser_condition"


def test_avito_xlsx_is_new_overrides_old_filename_fallback():
    df = pd.DataFrame(
        [
            {
                "article": "123",
                "row_is_new": 1,
                "condition_source": "parser_condition",
            }
        ]
    )

    result = WatchDbWriterService.add_avito_row_state(df, shop_id=2, batch_is_new=False)

    assert result.loc[0, "_price_is_new"] == "Y"
    assert result.loc[0, "_condition_source_norm"] == "parser_condition"


def test_avito_duplicate_conflict_prefers_non_batch_condition_source():
    df = pd.DataFrame(
        [
            {
                "article": "123",
                "row_is_new": 1,
                "condition_source": "batch_fallback",
            },
            {
                "article": "123",
                "row_is_new": 0,
                "condition_source": "parser_condition",
            },
        ]
    )

    prepared = WatchDbWriterService.add_avito_row_state(df, shop_id=2, batch_is_new=True)
    result = WatchDbWriterService.resolve_avito_duplicate_conflicts(prepared, shop_id=2)

    assert len(result) == 1
    assert result.iloc[0]["_price_is_new"] == "N"


def test_avito_old_xlsx_without_is_new_uses_filename_fallback():
    df = pd.DataFrame([{"article": "123"}])

    result = WatchDbWriterService.add_avito_row_state(df, shop_id=2, batch_is_new=False)

    assert result.loc[0, "_price_is_new"] == "N"
    assert result.loc[0, "_condition_source_norm"] == "batch_fallback"


def test_ensure_g_shop_watch_ml_columns_adds_missing_columns(monkeypatch):
    executed = []
    existing_columns = set()

    class FakeCursor:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

        def execute(self, query, params=None):
            executed.append((query, params))
            if query.startswith("ALTER TABLE"):
                existing_columns.add(query.split("`")[3])

        def fetchone(self):
            column = executed[-1][1][0]
            return {"Field": column} if column in existing_columns else None

    class FakeConnection:
        def cursor(self):
            return FakeCursor()

        def commit(self):
            executed.append(("COMMIT", None))

        def close(self):
            executed.append(("CLOSE", None))

    monkeypatch.setattr(db_writer, "_ENSURED_TABLE_COLUMNS", set())
    monkeypatch.setattr(db_writer, "get_db_connection", lambda: FakeConnection())

    WatchDbWriterService.ensure_g_shop_watch_ml_columns()

    alter_queries = [query for query, _ in executed if query.startswith("ALTER TABLE")]
    assert len(alter_queries) == 2
    assert any("`fake_grade` INT NULL" in query for query in alter_queries)
    assert any("`fake_proba` FLOAT NULL" in query for query in alter_queries)


def test_insert_g_shop_watch_keeps_fake_fields_and_ensures_columns(monkeypatch):
    calls = []
    captured = {}

    def fake_ensure():
        calls.append("ensure")

    def fake_bulk_insert(query, records):
        calls.append("insert")
        captured["query"] = query
        captured["records"] = records

    monkeypatch.setattr(WatchDbWriterService, "ensure_g_shop_watch_ml_columns", fake_ensure)
    monkeypatch.setattr(db_writer, "bulk_insert", fake_bulk_insert)

    df = pd.DataFrame(
        [
            {
                "watch_id": 10,
                "product_url": "https://example.test/item/123",
                "image_url": "https://example.test/item.jpg",
                "rating": None,
                "shop_rating": 4.8,
                "review": 12,
                "is_global": "N",
                "warranty_period": None,
                "color": "black",
                "article": "123",
                "days_to_delivery": None,
                "ali_affiliate_url": None,
                "fake_grade": -2,
                "fake_proba": 0.9476,
            }
        ]
    )

    WatchDbWriterService.insert_g_shop_watch(df, shop_id=2)

    assert calls == ["ensure", "insert"]
    assert "fake_grade" in captured["query"]
    assert "fake_proba" in captured["query"]
    assert captured["records"][0]["fake_grade"] == -2
    assert captured["records"][0]["fake_proba"] == 0.9476


def test_add_fake_ml_fields_scores_all_avito_rows(monkeypatch):
    calls = []

    def fake_add_fake_proba(df_ready, actual_date):
        calls.append((df_ready["article"].tolist(), actual_date))
        scored = df_ready.copy()
        scored["fake_proba"] = [0.81 for _ in range(len(scored))]
        return scored

    monkeypatch.setattr(db_writer, "add_fake_proba", fake_add_fake_proba)

    df = pd.DataFrame(
        [
            {"article": "new-1", "_price_is_new": "Y", "fake_grade": "-2"},
            {"article": "old-1", "_price_is_new": "N", "fake_grade": "0"},
        ]
    )

    result = WatchDbWriterService.add_fake_ml_fields(
        df,
        actual_date=pd.Timestamp("2026-07-31").date(),
        shop_id=2,
    )

    assert calls == [(["new-1", "old-1"], pd.Timestamp("2026-07-31").date())]
    assert result.loc[0, "fake_grade"] == -2
    assert result.loc[0, "fake_proba"] == 0.81
    assert result.loc[1, "fake_proba"] == 0.81

    other_shop = WatchDbWriterService.add_fake_ml_fields(
        df,
        actual_date=pd.Timestamp("2026-07-31").date(),
        shop_id=1,
    )

    assert calls == [(["new-1", "old-1"], pd.Timestamp("2026-07-31").date())]
    assert other_shop["fake_proba"].isna().all()


def test_filter_avito_fake_price_rows_drops_warn_and_risk(monkeypatch):
    monkeypatch.setattr(
        db_writer,
        "load_thresholds",
        lambda: {"warn": 0.7659, "risk": 0.9476},
    )

    df = pd.DataFrame(
        [
            {"article": "ok", "fake_proba": 0.2},
            {"article": "warn", "fake_proba": 0.8},
            {"article": "risk", "fake_proba": 0.99},
            {"article": "missing", "fake_proba": None},
        ]
    )

    result = WatchDbWriterService.filter_avito_fake_price_rows(df, shop_id=2)

    assert result["article"].tolist() == ["ok", "missing"]


def test_filter_avito_fake_price_rows_keeps_other_shops(monkeypatch):
    monkeypatch.setattr(
        db_writer,
        "load_thresholds",
        lambda: {"warn": 0.7659, "risk": 0.9476},
    )

    df = pd.DataFrame([{"article": "risk", "fake_proba": 0.99}])

    result = WatchDbWriterService.filter_avito_fake_price_rows(df, shop_id=1)

    assert result["article"].tolist() == ["risk"]


def test_filter_avito_quarantined_price_rows_drops_low_premium_prices(monkeypatch):
    monkeypatch.setattr(
        db_writer,
        "load_thresholds",
        lambda: {"warn": 0.7659, "risk": 0.9476},
    )

    df = pd.DataFrame(
        [
            {"article": "apple-ok", "brand": "apple", "model": "watchseries11", "price": 50000, "fake_proba": 0.1},
            {"article": "apple-low", "brand": "apple", "model": "watchseries11", "price": 5000, "fake_proba": 0.1},
            {"article": "garmin-low", "brand": "garmin", "model": "tactix8", "price": 6000, "fake_proba": 0.1},
            {"article": "basic-low", "brand": "garmin", "model": "forerunner55", "price": 6000, "fake_proba": 0.1},
            {"article": "fake-like", "brand": "apple", "model": "watchseries8", "price": 12000, "fake_proba": 0.9},
        ]
    )

    result = WatchDbWriterService.filter_avito_quarantined_price_rows(df, shop_id=2)

    assert result["article"].tolist() == ["apple-ok", "basic-low"]


def test_cleanup_avito_quarantined_price_history_deletes_existing_prices(monkeypatch):
    monkeypatch.setattr(
        db_writer,
        "load_thresholds",
        lambda: {"warn": 0.7659, "risk": 0.9476},
    )

    captured = {}

    def fake_delete(shop_watch_ids, *, shop_id):
        captured["ids"] = shop_watch_ids
        captured["shop_id"] = shop_id
        return len(shop_watch_ids)

    monkeypatch.setattr(
        WatchDbWriterService,
        "delete_prices_for_shop_watch_ids",
        fake_delete,
    )

    df = pd.DataFrame(
        [
            {"article": "fake-like", "shop_watch_id": 11, "brand": "apple", "model": "watchseries8", "price": 12000, "fake_proba": 0.9},
            {"article": "apple-low", "shop_watch_id": 12, "brand": "apple", "model": "watchseries11", "price": 5000, "fake_proba": 0.1},
            {"article": "ok", "shop_watch_id": 13, "brand": "apple", "model": "watchseries11", "price": 50000, "fake_proba": 0.1},
        ]
    )

    deleted = WatchDbWriterService.cleanup_avito_quarantined_price_history(df, shop_id=2)

    assert deleted == 2
    assert sorted(captured["ids"]) == [11, 12]
    assert captured["shop_id"] == 2
