from pydoc import text
from pyexpat import features

from app.schemas.watch_features import WatchFeatures
from app.services.extraction_service import ExtractionService
from app.extractors.size_extractor import SizeExtractor
from app.normalizers.watch_title_normalizer import WatchTitleNormalizer
from app.extractors.model_candidate_builder import ModelCandidateBuilder

from app.extractors.brand_parsers.garmin_parser import GarminParser
from app.extractors.brand_parsers.apple_parser import AppleParser
from app.extractors.brand_parsers.samsung_parser import SamsungParser
from app.extractors.brand_parsers.huawei_parser import HuaweiParser
from app.extractors.brand_parsers.amazfit_parser import AmazfitParser
from app.extractors.brand_parsers.google_parser import GoogleParser
from app.extractors.brand_parsers.honor_parser import HonorParser
from app.extractors.brand_parsers.huawei_parser import HuaweiParser


ACCESSORY_KEYWORDS = {
    "ремешок",
    "ремень",
    "браслет",
    "strap",
    "band",
    "loop",
    "case",
    "glass",
    "стекло",
    "чехол",
    "защитное стекло",
    "кабель",
    "зарядка",
    "dock",
    "charger",
}


class WatchFeatureExtractor:
    @classmethod
    def extract(cls, title: str, description: str = "", brand: str = "Unknown") -> WatchFeatures:
        normalized_title = WatchTitleNormalizer.normalize(title)

        color = ExtractionService.extract_color(title, description)
        warranty = ExtractionService.extract_warranty(description)

        size_mm = SizeExtractor.extract_first_size_mm(title)
        all_sizes_mm = SizeExtractor.extract_all_sizes_mm(title)

        is_accessory = any(word in normalized_title for word in ACCESSORY_KEYWORDS)
        is_multi_model = len(all_sizes_mm) > 1

        features = WatchFeatures(
            product_name=title,
            normalized_title=normalized_title,
            brand=brand,
            size_mm=size_mm,
            all_sizes_mm=all_sizes_mm,
            color=color or None,
            warranty_period=warranty or None,
            is_accessory=is_accessory,
            is_multi_model=is_multi_model,
        )

        # 1. Сначала брендовый parser
        features = cls.apply_brand_parser(features)

        # 2. Если брендовый parser НЕ заполнил model_candidates,
        #    только тогда fallback через общий builder
        if not features.model_candidates:
            features.model_candidates = ModelCandidateBuilder.build(
                features.brand,
                features.normalized_title,
            )

        # 3. Если брендовый parser НЕ заполнил material/connectivity,
        #    только тогда fallback через общий builder
        if not features.extracted_material:
            features.extracted_material = ModelCandidateBuilder.extract_material(
                features.normalized_title,
            )

        if not features.extracted_connectivity:
            features.extracted_connectivity = ModelCandidateBuilder.extract_connectivity(
                features.normalized_title,
            )

        # 4. Если брендовый parser НЕ собрал extracted_variant_name,
        #    только тогда строим общий fallback
        if not features.extracted_variant_name:
            features.extracted_variant_name = cls.build_variant_name(
                size_mm=features.size_mm,
                material=features.extracted_material,
                connectivity=features.extracted_connectivity,
            )

        return features

    @classmethod
    def apply_brand_parser(cls, features: WatchFeatures) -> WatchFeatures:
        brand = (features.brand or "").strip().lower()

        if brand == "garmin":
            return GarminParser.parse(features)

        if brand == "apple":
            return AppleParser.parse(features)

        if brand == "samsung":
            return SamsungParser.parse(features)

        if brand == "huawei":
            return HuaweiParser.parse(features)
        
        if brand == "amazfit":
            return AmazfitParser.parse(features)
        
        if brand == "google" or brand == "pixel":
            return GoogleParser.parse(features)
        
        if brand == "honor":
            return HonorParser.parse(features)
        
        if brand == "huawei":
            return HuaweiParser.parse(features)

        return features

    @classmethod
    def build_variant_name(
        cls,
        size_mm: int | None,
        material: str | None,
        connectivity: str | None,
    ) -> str | None:
        parts: list[str] = []

        if size_mm:
            parts.append(f"{size_mm}mm")

        if material:
            parts.append(material)

        if connectivity:
            parts.append(connectivity)

        return " ".join(parts) if parts else None