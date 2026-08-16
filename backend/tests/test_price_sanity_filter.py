import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.watch_db_writer_service import WatchDbWriterService


def test_prepare_matched_rows_skips_zero_and_extreme_prices():
    brand_column = "\u0411\u0440\u0435\u043d\u0434"

    df = pd.DataFrame(
        [
            {
                "match_status": "matched",
                "matched_model_name": "Watch 5",
                "size_mm": 46,
                brand_column: "Huawei",
                "article": "good-1",
                "URL": "https://example.test/product/good-1/",
                "image_url": "https://example.test/good.jpg",
                "price": 34_999,
            },
            {
                "match_status": "matched",
                "matched_model_name": "Watch 5",
                "size_mm": 46,
                brand_column: "Huawei",
                "article": "zero-1",
                "URL": "https://example.test/product/zero-1/",
                "image_url": "https://example.test/zero.jpg",
                "price": 0,
            },
            {
                "match_status": "matched",
                "matched_model_name": "Watch 5",
                "size_mm": 46,
                brand_column: "Huawei",
                "article": "bad-1",
                "URL": "https://example.test/product/bad-1/",
                "image_url": "https://example.test/bad.jpg",
                "price": 2_899_934_499,
            },
        ]
    )

    result = WatchDbWriterService.prepare_matched_rows(df)

    assert result["article"].tolist() == ["good-1"]
    assert result.iloc[0]["price"] == 34_999
