import re

from app.schemas.watch_preprocessed_row import WatchPreprocessedRow
from app.extractors.size_extractor import SizeExtractor
from app.normalizers.watch_title_normalizer import WatchTitleNormalizer
from app.services.extraction_service import ExtractionService


ACCESSORY_KEYWORDS = {
    "ремешок", "ремень", "браслет", "strap", "band", "loop", "case", "glass", "стекло", "чехол"
}


COMMON_BRANDS = [
    ("Amazfit", ["amazfit"]),
    ("Garmin", ["garmin"]),
    ("Apple", ["apple"]),
    ("Samsung", ["samsung"]),
    ("Huawei", ["huawei"]),
    ("Xiaomi", ["xiaomi", "redmi", "poco"]),
    ("Oppo", ["oppo"]),
    ("Honor", ["honor"]),
    ("Google", ["google", "pixel"]),
    ("OnePlus", ["oneplus"]),
    ("Motorola", ["motorola", "moto"]),
    ("Vivo", ["vivo", "iqoo"]),
]


class WatchPreprocessService:
    @classmethod
    def preprocess_row(cls, row: dict) -> WatchPreprocessedRow:
        product_name = str(row.get("Название") or row.get("product_name") or "")
        description = str(row.get("Описание") or row.get("description") or "")
        product_url = str(row.get("URL") or row.get("product_url") or "")
        image_url = row.get("Изображения") or row.get("image_url")
        shop_rating = row.get("Рейтинг продавца") or row.get("shop_rating")
        price = row.get("Цена") or row.get("price")

        normalized_title = WatchTitleNormalizer.normalize(product_name)

        # Бренд определяется ОДИН раз и дальше не меняется
        brand = cls.extract_brand_once(product_name)

        # brand_from_url оставляем только как справочную диагностику,
        # но он НЕ влияет на brand
        brand_from_url = cls.extract_brand_from_url_for_debug(product_url)
        brand_match = cls.compare_brands(brand, brand_from_url)

        article = ExtractionService.extract_article(product_url)
        all_sizes = SizeExtractor.extract_all_sizes_mm(product_name)
        size_mm = SizeExtractor.extract_first_size_mm(product_name)

        is_accessory = any(word in normalized_title for word in ACCESSORY_KEYWORDS)
        is_multi_model = len(all_sizes) > 1

        return WatchPreprocessedRow(
            product_name=product_name,
            description=description,
            product_url=product_url,
            image_url=image_url,
            brand=brand,
            brand_from_url=brand_from_url,
            brand_match=brand_match,
            article=article,
            shop_rating=shop_rating,
            price=price,
            normalized_title=normalized_title,
            size_mm=size_mm,
            is_accessory=is_accessory,
            is_multi_model=is_multi_model,
            all_sizes_mm=all_sizes,
        )

    @classmethod
    def extract_brand_once(cls, title: str) -> str:
        text = cls.normalize_for_brand_check(title)

        # согласованное спец-правило
        if re.search(r"\bforerunner\b", text):
            return "Garmin"

        for brand, aliases in COMMON_BRANDS:
            for alias in aliases:
                if re.search(rf"\b{re.escape(alias)}\b", text):
                    return brand

        return "Unknown"

    @classmethod
    def normalize_for_brand_check(cls, text: str) -> str:
        normalized = (text or "").lower().strip()
        normalized = normalized.replace("ё", "е")
        normalized = normalized.replace("-", " ")
        normalized = normalized.replace("_", " ")
        normalized = re.sub(r"\s+", " ", normalized)
        return normalized

    @classmethod
    def extract_brand_from_url_for_debug(cls, url: str) -> str | None:
        if not url:
            return None

        lowered = url.lower()

        debug_map = {
            "Garmin": ["garmin"],
            "Apple": ["apple"],
            "Samsung": ["samsung", "galaxy-watch", "galaxy_watch"],
            "Huawei": ["huawei"],
            "Xiaomi": ["xiaomi", "redmi-watch", "redmi_watch", "redmi", "poco"],
            "Oppo": ["oppo"],
            "Honor": ["honor"],
            "Google": ["google", "pixel-watch", "pixel_watch", "pixel"],
            "OnePlus": ["oneplus", "one-plus"],
            "Amazfit": ["amazfit"],
            "Motorola": ["motorola", "moto-watch", "moto_watch", "moto"],
            "Vivo": ["vivo", "iqoo"],
        }

        for brand, keywords in debug_map.items():
            if any(keyword in lowered for keyword in keywords):
                return brand

        return None

    @classmethod
    def compare_brands(cls, title_brand: str, url_brand: str | None) -> bool | None:
        if not title_brand or title_brand == "Unknown" or not url_brand:
            return None
        return title_brand.lower() == url_brand.lower()