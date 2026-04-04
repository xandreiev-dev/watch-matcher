from app.schemas.watch_features import WatchFeatures
from app.services.extraction_service import ExtractionService
from app.extractors.size_extractor import SizeExtractor
from app.normalizers.watch_title_normalizer import WatchTitleNormalizer
from app.extractors.brand_parsers.garmin_parser import GarminParser


ACCESSORY_KEYWORDS = {
    "ремешок", "ремень", "браслет", "strap", "band", "loop", "case", "glass", "стекло", "чехол"
}


class WatchFeatureExtractor:
    @classmethod
    def extract(cls, title: str, description: str = "", brand: str = "Unknown") -> WatchFeatures:
        normalized_title = WatchTitleNormalizer.normalize(title)

        color = ExtractionService.extract_color(title, description)
        warranty = ExtractionService.extract_warranty(description)
        size_mm = SizeExtractor.extract_first_size_mm(title)

        is_accessory = any(word in normalized_title for word in ACCESSORY_KEYWORDS)

        features = WatchFeatures(
            product_name=title,
            normalized_title=normalized_title,
            brand=brand,
            size_mm=size_mm,
            color=color or None,
            warranty_period=warranty or None,
            is_accessory=is_accessory,
            is_multi_model=False,
        )

        if features.brand == "Garmin":
            features = GarminParser.parse(features)

        return features