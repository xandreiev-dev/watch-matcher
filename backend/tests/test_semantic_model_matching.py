import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.extractors.brand_parsers.amazfit_parser import AmazfitParser
from app.extractors.brand_parsers.apple_parser import AppleParser
from app.extractors.brand_parsers.garmin_parser import GarminParser
from app.extractors.brand_parsers.google_parser import GoogleParser
from app.extractors.brand_parsers.xiaomi_parser import XiaomiParser
from app.extractors.brand_parsers.honor_parser import HonorParser
from app.extractors.brand_parsers.huawei_parser import HuaweiParser
from app.extractors.brand_parsers.motorola_parser import MotorolaParser
from app.extractors.brand_parsers.oneplus_parser import OnePlusParser
from app.extractors.brand_parsers.oppo_parser import OppoParser
from app.extractors.brand_parsers.samsung_parser import SamsungParser
from app.extractors.brand_parsers.vivo_parser import VivoParser
from app.matchers.watch_matcher import WatchMatcher
from app.schemas.watch_features import WatchFeatures
from app.services.watch_preprocess_service import WatchPreprocessService


def features(title: str, brand: str, candidates: list[str], variant: str | None = None) -> WatchFeatures:
    normalized = title.lower().replace("-", " ")
    return WatchFeatures(
        product_name=title,
        normalized_title=normalized,
        brand=brand,
        model_candidates=candidates,
        variant=variant,
    )


def model(id_: int, brand: str, name: str) -> dict:
    return {
        "id": id_,
        "brand": brand,
        "model_name": name,
        "normalized_name": name.lower().replace("-", " "),
    }


def variant(
    id_: int,
    model_id: int,
    name: str,
    size: int | None,
    connectivity: str | None = None,
    quality_score: int = 0,
    is_canonical: int = 1,
) -> dict:
    return {
        "id": id_,
        "model_id": model_id,
        "variant_name": name,
        "case_size_mm": size,
        "connectivity_type": connectivity,
        "quality_score": quality_score,
        "is_canonical": is_canonical,
    }


def parse_title(parser_cls, title: str, brand: str) -> WatchFeatures:
    return parser_cls.parse(
        WatchFeatures(
            product_name=title,
            normalized_title=title.lower().replace("-", " "),
            brand=brand,
        )
    )


def test_xiaomi_watch_5_active_matches_active_not_base():
    result = WatchMatcher.find_model(
        features(
            "Xiaomi Watch 5 Active",
            "Xiaomi",
            ["watch 5 active", "watch 5"],
            variant="Active",
        ),
        [
            model(1, "Xiaomi", "Watch 5"),
            model(2, "Xiaomi", "Watch 5 Active"),
        ],
    )

    assert result["model_name"] == "Watch 5 Active"


def test_xiaomi_watch_5_active_does_not_fall_back_to_base():
    result = WatchMatcher.find_model(
        features(
            "Xiaomi Watch 5 Active",
            "Xiaomi",
            ["watch 5 active", "watch 5"],
            variant="Active",
        ),
        [model(1, "Xiaomi", "Watch 5")],
    )

    assert result is None


def test_xiaomi_watch_5_lite_does_not_fall_back_to_base():
    result = WatchMatcher.find_model(
        features(
            "Xiaomi Watch 5 Lite",
            "Xiaomi",
            ["watch 5 lite", "watch 5"],
            variant="Lite",
        ),
        [model(1, "Xiaomi", "Watch 5")],
    )

    assert result is None


def test_redmi_watch_5_lite_does_not_match_xiaomi_watch_5():
    result = WatchMatcher.find_model(
        features(
            "Redmi Watch 5 Lite",
            "Xiaomi",
            ["redmi watch 5 lite", "redmi watch 5", "watch 5"],
            variant="Lite",
        ),
        [
            model(1, "Xiaomi", "Watch 5"),
            model(2, "Xiaomi", "Redmi Watch 5 Lite"),
        ],
    )

    assert result["model_name"] == "Redmi Watch 5 Lite"


def test_xiaomi_base_watch_5_still_matches_base():
    result = WatchMatcher.find_model(
        features("Xiaomi Watch 5", "Xiaomi", ["watch 5"]),
        [model(1, "Xiaomi", "Watch 5")],
    )

    assert result["model_name"] == "Watch 5"


def test_xiaomi_parser_builds_active_and_lite_candidates():
    active = XiaomiParser.parse(
        WatchFeatures(
            product_name="Xiaomi Watch 5 Active",
            normalized_title="xiaomi watch 5 active",
            brand="Xiaomi",
        )
    )
    lite = XiaomiParser.parse(
        WatchFeatures(
            product_name="Xiaomi Watch 5 Lite",
            normalized_title="xiaomi watch 5 lite",
            brand="Xiaomi",
        )
    )

    assert "watch 5 active" in active.model_candidates
    assert "watch 5 lite" in lite.model_candidates


@pytest.mark.parametrize(
    ("parser_cls", "brand", "title", "expected_candidates", "generation", "variant"),
    [
        (AppleParser, "Apple", "Apple Watch SE 2 44mm", ["watch se 2"], "2", None),
        (AppleParser, "Apple", "Apple Watch Series SE Gen 2 2024 44mm", ["watch se 2"], "2", None),
        (AppleParser, "Apple", "Apple Watch Series SE3 44mm", ["watch se 3"], "3", None),
        (AppleParser, "Apple", "Apple Watch Series 9 45mm", ["watch series 9"], "9", None),
        (AppleParser, "Apple", "Apple Watch Ultra 2", ["watch ultra 2"], "2", None),
        (SamsungParser, "Samsung", "Samsung Galaxy Watch 6 Classic 47mm", ["galaxy watch 6 classic"], "6", "Classic"),
        (SamsungParser, "Samsung", "Samsung Galaxy Watch Ultra LTE", ["galaxy watch ultra"], None, "Ultra"),
        (HuaweiParser, "Huawei", "Huawei Watch GT 5 Pro", ["watch gt 5 pro"], "5", "Pro"),
        (HuaweiParser, "Huawei", "Huawei Watch Fit 4 Pro", ["watch fit 4 pro"], "4", "Pro"),
        (HuaweiParser, "Huawei", "Huawei Watch D2 Pro", ["watch d2 pro"], "2", "Pro"),
        (GarminParser, "Garmin", "Garmin Fenix 7S Sapphire Solar", ["fenix 7s sapphire solar"], "7S", "Sapphire Solar"),
        (GarminParser, "Garmin", "Garmin Vivoactive6", ["vivoactive 6"], "6", None),
        (GarminParser, "Garmin", "Garmin Forerunner745", ["forerunner 745"], "745", None),
        (GarminParser, "Garmin", "Garmin Instinct 2X", ["instinct 2x solar"], "2X", None),
        (GarminParser, "Garmin", "Garmin Forerunner 265S Music", ["forerunner 265s music"], "265S", "Music"),
        (AmazfitParser, "Amazfit", "Amazfit GTS 4 Mini", ["gts 4 mini"], "4", "Mini"),
        (AmazfitParser, "Amazfit", "Amazfit Bip Max", ["bip max"], None, "Max"),
        (AmazfitParser, "Amazfit", "Amazfit T-Rex 3 Pro", ["t rex 3 pro", "t-rex 3 pro"], "3", "Pro"),
        (GoogleParser, "Google", "Google Pixel Watch 2 41mm", ["pixel watch 2"], "2", None),
        (GoogleParser, "Google", "Google Watch 4 Wi-Fi 41mm", ["pixel watch 4"], "4", None),
        (HonorParser, "Honor", "Honor Choice Watch 2 Pro", ["choice watch 2 pro"], "2", "Pro"),
        (HonorParser, "Honor", "Honor Watch X5i", ["watch x5i"], "5i", None),
        (MotorolaParser, "Motorola", "Moto Watch Fit", ["moto watch fit"], None, "Fit"),
        (OnePlusParser, "OnePlus", "OnePlus Watch 2R", ["watch 2r"], "2R", None),
        (OnePlusParser, "OnePlus", "OnePlus Watch 3 Lite", ["watch 3 lite"], "3", "Lite"),
        (OppoParser, "Oppo", "Oppo Watch X2 Mini", ["watch x2 mini"], "2", "X Mini"),
        (VivoParser, "Vivo", "Vivo Watch GT 2", ["watch gt 2"], "2", "GT"),
        (VivoParser, "Vivo", "iQOO Watch GT", ["iqoo watch gt"], None, "GT"),
        (XiaomiParser, "Xiaomi", "Xiaomi Redmi Watch 5 Lite", ["redmi watch 5 lite"], "5", "Lite"),
        (XiaomiParser, "Xiaomi", "Xiaomi Watch S4 Sport", ["watch s4 sport"], "S4", "Sport"),
    ],
)
def test_brand_parsers_emit_specific_candidates_first(
    parser_cls,
    brand: str,
    title: str,
    expected_candidates: list[str],
    generation: str | None,
    variant: str | None,
):
    parsed = parse_title(parser_cls, title, brand)

    for expected in expected_candidates:
        assert expected in parsed.model_candidates
    if generation is not None:
        assert parsed.generation == generation
    if variant is not None:
        assert parsed.variant == variant


def test_preprocess_prefers_explicit_title_brand_over_bad_source_brand():
    row = {
        "Название": "HUAWEI Смарт-часы Honor Choice Watch 2i Глобальное издание",
        "brand": "Huawei",
        "URL": "https://www.ozon.ru/product/honor-choice-watch-2i-123",
        "Цена": 3039,
    }

    preprocessed = WatchPreprocessService.preprocess_row(row, source="ozon")

    assert preprocessed.brand == "Honor"


def test_samsung_classic_does_not_fall_back_to_base_watch():
    result = WatchMatcher.find_model(
        features(
            "Samsung Galaxy Watch 6 Classic",
            "Samsung",
            ["galaxy watch 6 classic", "galaxy watch 6"],
            variant="Classic",
        ),
        [model(1, "Samsung", "Galaxy Watch 6")],
    )

    assert result is None


def test_apple_series_se_gen_2_matches_watch_se_2():
    parsed = AppleParser.parse(
        WatchFeatures(
            product_name="Apple Watch Series SE Gen 2 2024 44mm",
            normalized_title="apple watch series se gen 2 2024 44mm",
            brand="Apple",
        )
    )

    result = WatchMatcher.find_model(
        parsed,
        [
            model(19, "Apple", "Watch SE"),
            model(20, "Apple", "Watch SE 2"),
            model(31, "Apple", "Watch Series 8"),
        ],
    )

    assert result["model_name"] == "Watch SE 2"


def test_apple_watch_se_size_is_not_treated_as_generation():
    parsed = AppleParser.parse(
        WatchFeatures(
            product_name="Apple Watch SE 44",
            normalized_title="apple watch se 44",
            brand="Apple",
        )
    )

    assert parsed.generation is None
    assert parsed.model_candidates == ["watch se"]


def test_google_parser_ignores_other_brands_using_wear_os_by_google():
    parsed = GoogleParser.parse(
        WatchFeatures(
            product_name="OnePlus Watch 3 Wear OS by Google",
            normalized_title="oneplus watch 3 wear os by google",
            brand="Google",
        )
    )

    assert parsed.model_candidates == []


def test_huawei_d2_pro_does_not_fall_back_to_d2():
    result = WatchMatcher.find_model(
        features(
            "Huawei Watch D2 Pro",
            "Huawei",
            ["watch d2 pro", "watch d2"],
            variant="Pro",
        ),
        [model(1, "Huawei", "Watch D2")],
    )

    assert result is None


def test_huawei_parser_keeps_d2_pro_as_specific_candidate():
    parsed = HuaweiParser.parse(
        WatchFeatures(
            product_name="Huawei Watch D2 Pro",
            normalized_title="huawei watch d2 pro",
            brand="Huawei",
        )
    )

    assert parsed.generation == "2"
    assert parsed.variant == "Pro"
    assert "watch d2 pro" in parsed.model_candidates


def test_honor_parser_keeps_watch_x5i_generation():
    parsed = HonorParser.parse(
        WatchFeatures(
            product_name="Honor Watch X5i",
            normalized_title="honor watch x5i",
            brand="Honor",
        )
    )

    assert parsed.generation == "5i"
    assert "watch x5i" in parsed.model_candidates


def test_apple_se_does_not_match_series_when_bad_candidate_exists():
    result = WatchMatcher.find_model(
        features(
            "Apple Watch SE 2",
            "Apple",
            ["watch se 2", "watch series 2"],
            variant="SE",
        ),
        [
            model(1, "Apple", "Watch Series 2"),
            model(2, "Apple", "Watch SE 2"),
        ],
    )

    assert result["model_name"] == "Watch SE 2"


def test_numbered_watch_does_not_fall_back_to_plain_watch():
    watch_features = features(
        "Vivo Watch 2",
        "Vivo",
        ["watch 2", "watch"],
    )
    watch_features.generation = "2"

    result = WatchMatcher.find_model(
        watch_features,
        [model(1, "Vivo", "Watch")],
    )

    assert result is None


def test_numbered_watch_does_not_match_other_number():
    watch_features = features(
        "Google Pixel Watch 2",
        "Google",
        ["pixel watch 2", "pixel watch"],
    )
    watch_features.generation = "2"

    result = WatchMatcher.find_model(
        watch_features,
        [model(1, "Google", "Pixel Watch 20")],
    )

    assert result is None


def test_variant_match_falls_back_to_best_same_size_row():
    watch_features = features(
        "Samsung Galaxy Watch8 44mm",
        "Samsung",
        ["galaxy watch 8", "galaxy watch8"],
        variant="Watch 8 44mm",
    )
    watch_features.size_mm = 44
    watch_features.extracted_variant_name = "Watch 8 44mm"

    result = WatchMatcher.find_variant(
        watch_features,
        model(1, "Samsung", "Galaxy Watch8"),
        [
            variant(10, 1, "Galaxy Watch8 44mm", 44, "lte", quality_score=69),
            variant(11, 1, "LTE 44mm", 44, "gps+lte", quality_score=80),
        ],
    )

    assert result["id"] == 11


def test_variant_match_prefers_gps_only_when_gps_is_explicit():
    watch_features = features(
        "Apple Watch Series 11 GPS 46mm",
        "Apple",
        ["watch series 11"],
    )
    watch_features.size_mm = 46
    watch_features.extracted_connectivity = "gps"
    watch_features.extracted_variant_name = "Watch Series 11 46mm GPS"

    result = WatchMatcher.find_variant(
        watch_features,
        model(1, "Apple", "Watch Series 11"),
        [
            variant(20, 1, "Watch Series 11 46mm", 46, "gps+lte", quality_score=90),
            variant(21, 1, "Watch Series 11 Aluminum 46mm", 46, "gps+bluetooth", quality_score=80),
        ],
    )

    assert result["id"] == 21


def test_garmin_parser_adds_short_pro_alias_for_extended_fenix_title():
    parsed = GarminParser.parse(
        WatchFeatures(
            product_name="Garmin Fenix 8 Pro AMOLED Sapphire 51mm",
            normalized_title="garmin fenix 8 pro amoled sapphire 51mm",
            brand="Garmin",
            size_mm=51,
        )
    )

    assert "fenix 8 pro" in parsed.model_candidates


@pytest.mark.parametrize(
    ("brand", "title", "candidates", "base_name", "correct_name"),
    [
        ("Oppo", "Oppo Watch SE", ["watch se", "watch"], "Watch", "Watch SE"),
        ("OnePlus", "OnePlus Watch 2R", ["watch 2r", "watch 2"], "Watch 2", "Watch 2R"),
        ("Vivo", "Vivo Watch GT", ["watch gt", "watch"], "Watch", "Watch GT"),
        ("Motorola", "Moto Watch Fit", ["moto watch fit", "watch fit", "watch"], "Moto Watch", "Moto Watch Fit"),
        ("Garmin", "Garmin Fenix 7 Sapphire Solar", ["fenix 7 sapphire solar", "fenix 7"], "Fenix 7", "Fenix 7 Sapphire Solar"),
        (
            "Honor",
            "Honor Choice Watch 2 Pro",
            ["choice watch 2 pro", "choice watch 2"],
            "Choice Watch 2",
            "Choice Watch 2 Pro",
        ),
        ("Amazfit", "Amazfit GTR 4", ["gtr 4", "gtr"], "GTR", "GTR 4"),
    ],
)
def test_protected_brand_modifiers_prefer_specific_model(
    brand: str,
    title: str,
    candidates: list[str],
    base_name: str,
    correct_name: str,
):
    result = WatchMatcher.find_model(
        features(title, brand, candidates),
        [
            model(1, brand, base_name),
            model(2, brand, correct_name),
        ],
    )

    assert result["model_name"] == correct_name
