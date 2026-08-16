import re

from app.schemas.watch_preprocessed_row import WatchPreprocessedRow
from app.extractors.size_extractor import SizeExtractor
from app.normalizers.watch_title_normalizer import WatchTitleNormalizer
from app.services.extraction_service import ExtractionService


ACCESSORY_KEYWORDS = {
    "ремешок", "ремень", "браслет", "strap", "band", "loop", "case", "glass", "стекло", "чехол"
}

OZON_SOFT_ACCESSORY_KEYWORDS = {"strap", "band", "loop", "case", "ремешок", "ремень", "браслет"}
STRONG_ACCESSORY_KEYWORDS = {"glass", "стекло", "чехол", "кабель", "зарядка", "charger", "dock"}
OZON_EXPLICIT_ACCESSORY_PATTERNS = [
    r"\b(?:защитн\w*\s+)?(?:glass|стекло)\s+(?:для|for)\b",
    r"\b(?:case|чехол)\s+(?:для|for)\b",
    r"\b(?:strap|band|loop|ремешок|ремень|браслет)\s+(?:для|for)\b",
    r"\b(?:кабель|charger|dock)\b",
    r"\bзарядн\w*\s+(?:устройство|кабель|станц\w*)\b",
]

WB_EXPLICIT_ACCESSORY_PATTERNS = [
    r"\b(?:адаптер|адаптеры|адаптер-коннектор|коннектор|коннекторы|переходник)\b",
    r"\b(?:чехол|чехол-бампер|бампер|накладка)\b",
    r"\b(?:защитн\w*\s+комплект|защитн\w*\s+чехол|защитн\w*\s+стекло|стекло)\b",
    r"\b(?:док-станц\w*|зарядн\w*|кабель|charger|dock)\b",
    r"\b(?:ремешок|ремешка|ремень|браслет)\s+(?:для|for)\b",
    r"\b(?:ремешок|ремешка|ремень|браслет)\b.*\b(?:на|для|for)\s+(?:часы|watch|band|fit)\b",
    r"^(?:для|for)\s+.*\b(?:watch|band|fit)\b",
    r"\b(?:для|for)\s+(?:apple|samsung|huawei|honor|google|pixel|oneplus|xiaomi|redmi|garmin|amazfit|vivo)\b.*\b(?:watch|band|fit)\b",
]

WATCH_MODEL_PATTERNS = [
    r"\bapple watch\b",
    r"\bwatch\s*(?:series\s*\d+|se\s*\d*|ultra)\b",
    r"\bwatch\s*s?\s*\d{1,2}\b",
    r"\bwatchs\d{1,2}\b",
    r"\bapple\b.*\b(?:series\s*\d+|se\s*\d*|ultra)\b",
    r"\bapple\b.*\bs\s*\d{1,2}\b",
    r"\bseries\s+\d+\b",
    r"\bgalaxy watch\b",
    r"\bpixel watch\b",
    r"\boneplus watch\b",
    r"\bhuawei watch\b",
    r"\bhuawei band\b",
    r"\bhonor watch\b",
    r"\bhonor band\b",
    r"\bamazfit\b",
    r"\bgarmin\b",
    r"\bforerunner\b",
    r"\bfenix\b",
    r"\bvenu\b",
    r"\binstinct\b",
    r"\bepix\b",
    r"\bvivoactive\b",
    r"\bsmart band\b",
    r"\bmi band\b",
    r"\bredmi band\b",
    r"\bgalaxy fit\b",
    r"\bfitbit\b",
    r"\bсмарт\s*часы\b",
    r"\bфитнес\s*браслет\b",
    r"\bумн\w*\s*браслет\b",
    r"\bумные\s*часы\b",
]


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
    def preprocess_row(cls, row: dict, source: str = "avito") -> WatchPreprocessedRow:
        product_name = str(cls.first_present(row, "Название", "product_name", "title", "title / product name") or "")
        description = str(cls.first_present(row, "Описание", "description", "specs_json") or "")
        product_url = str(cls.first_present(row, "URL", "product_url") or "")
        image_url = cls.first_present(row, "Изображения", "image_url")
        shop_rating = cls.first_present(row, "Рейтинг продавца", "shop_rating", "Звезды")
        price = cls.first_present(row, "Цена", "price", "Discount Price", "Price")

        normalized_title = WatchTitleNormalizer.normalize(product_name)
        brand_from_url = cls.extract_brand_from_url_for_debug(product_url)

        # Ozon иногда отдает неверный brand, а в названии при этом явно написан другой бренд.
        # Для матчинга безопаснее верить явному бренду из title, чем склеить товар с чужим каталогом.
        declared_brand = cls.first_present(row, "brand", "source_brand", "Бренд")
        title_brands = cls.extract_brands_from_title(product_name)
        if brand_from_url and brand_from_url in title_brands:
            brand = brand_from_url
        elif len(title_brands) == 1:
            brand = title_brands[0]
        elif len(title_brands) > 1:
            brand = "Unknown"
        else:
            brand = declared_brand or "Unknown"
        brand = str(brand).strip() if brand else "Unknown"

        # brand_from_url оставляем только как справочную диагностику,
        # но он НЕ влияет на brand
        brand_match = cls.compare_brands(brand, brand_from_url)

        article_value = cls.first_present(row, "Article", "article") or ExtractionService.extract_article(product_url)
        article = str(article_value).strip() if article_value is not None else None
        all_sizes = SizeExtractor.extract_all_sizes_mm(product_name)
        size_mm = SizeExtractor.extract_first_size_mm(product_name)
        if size_mm is None:
            size_mm = SizeExtractor.extract_first_size_mm(
                str(cls.first_present(row, "size", "case_size", "case_size_mm") or "")
            )

        is_accessory = cls.is_accessory(product_name, source=source)
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
    def first_present(cls, row: dict, *keys: str):
        for key in keys:
            value = row.get(key)
            if value is None:
                continue
            text = str(value).strip()
            if not text or text.lower() in {"nan", "none", "<na>", "nat"}:
                continue
            return value
        return None

    @classmethod
    def is_accessory(cls, title: str, source: str = "avito") -> bool:
        normalized_title = WatchTitleNormalizer.normalize(title)

        if source not in {"ozon", "dns", "wb"}:
            return any(word in normalized_title for word in ACCESSORY_KEYWORDS)

        if source == "wb" and any(re.search(pattern, normalized_title) for pattern in WB_EXPLICIT_ACCESSORY_PATTERNS):
            return True

        has_watch_model = any(re.search(pattern, normalized_title) for pattern in WATCH_MODEL_PATTERNS)
        has_explicit_accessory = any(re.search(pattern, normalized_title) for pattern in OZON_EXPLICIT_ACCESSORY_PATTERNS)
        has_soft_keyword = any(word in normalized_title for word in OZON_SOFT_ACCESSORY_KEYWORDS)
        has_strong_keyword = any(word in normalized_title for word in STRONG_ACCESSORY_KEYWORDS)

        if has_watch_model and not has_explicit_accessory:
            return False

        return has_explicit_accessory or has_soft_keyword or has_strong_keyword

    @classmethod
    def extract_brand_once(cls, title: str) -> str:
        brands = cls.extract_brands_from_title(title)
        return brands[0] if brands else "Unknown"

    @classmethod
    def extract_brands_from_title(cls, title: str) -> list[str]:
        text = cls.normalize_for_brand_check(title)
        found: list[tuple[int, str]] = []

        if match := re.search(r"\b(?:honor\s+choice|choice\s+watch|honor\s+watch)\b", text):
            found.append((match.start(), "Honor"))

        if match := re.search(r"\bhuawei\s+watch\b", text):
            found.append((match.start(), "Huawei"))

        # согласованное спец-правило
        if match := re.search(r"\bforerunner\b", text):
            found.append((match.start(), "Garmin"))

        for brand, aliases in COMMON_BRANDS:
            for alias in aliases:
                if match := re.search(rf"\b{re.escape(alias)}\b", text):
                    found.append((match.start(), brand))
                    break

        result: list[str] = []
        for _position, brand in sorted(found, key=lambda item: item[0]):
            if brand not in result:
                result.append(brand)

        return result

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

        # В Ozon slug иногда начинается с чужого бренда, но дальше содержит реальную линейку.
        if any(value in lowered for value in ["honor-choice", "choice-watch", "honor-watch"]):
            return "Honor"
        if "huawei-watch" in lowered:
            return "Huawei"

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
