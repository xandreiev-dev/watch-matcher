from app.schemas.watch_preprocessed_row import WatchPreprocessedRow
from app.extractors.size_extractor import SizeExtractor
from app.extractors.brand_url_validator import BrandUrlValidator
from app.normalizers.watch_title_normalizer import WatchTitleNormalizer
from app.services.extraction_service import ExtractionService


ACCESSORY_KEYWORDS = {
    "ремешок", "ремень", "браслет", "strap", "band", "loop", "case", "glass", "стекло", "чехол"
}


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

        brand = ExtractionService.extract_brand(product_name, description)
        brand_from_url = BrandUrlValidator.extract_brand_from_url(product_url)

        if not brand or brand == "Unknown":
            brand = brand_from_url or "Unknown"

        brand_match = BrandUrlValidator.is_match(brand, brand_from_url)

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