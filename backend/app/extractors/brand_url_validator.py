from typing import Optional


class BrandUrlValidator:
    BRAND_URL_KEYWORDS = {
        "Garmin": ["garmin"],
        "Apple": ["apple-watch", "apple_watch", "apple"],
        "Samsung": ["samsung", "galaxy-watch", "galaxy_watch"],
        "Huawei": ["huawei"],
        "Xiaomi": ["xiaomi", "redmi-watch", "redmi_watch", "redmi"],
        "Oppo": ["oppo"],
        "Honor": ["honor"],
        "Google": ["google", "pixel-watch", "pixel_watch"],
        "OnePlus": ["oneplus", "one-plus"],
        "Amazfit": ["amazfit"],
        "Motorola": ["motorola", "moto-watch", "moto_watch"],
    }

    @classmethod
    def extract_brand_from_url(cls, url: str) -> Optional[str]:
        if not url:
            return None

        lowered = url.lower()

        for brand, keywords in cls.BRAND_URL_KEYWORDS.items():
            if any(keyword in lowered for keyword in keywords):
                return brand

        return None

    @classmethod
    def is_match(cls, title_brand: str, url_brand: Optional[str]) -> Optional[bool]:
        if not title_brand or not url_brand or title_brand == "Unknown":
            return None
        return title_brand.lower() == url_brand.lower()