import re
from app.schemas.watch_features import WatchFeatures


class GoogleParser:
    FAMILIES = [
    ]

    FAMILY_DISPLAY = {
    }

    NOISE_WORDS = [
        "новые",
        "новый",
        "русский",
        "русский язык",
        "рф",
        "все цвета",
        "в наличии",
        "оригинал",
        "оригинальные",
        "гарантия",
        "умные часы",
        "смарт часы",
        "смарт-часы",
        "часы",
    ]

    @classmethod
    def parse(cls, features: WatchFeatures) -> WatchFeatures:
        text = features.normalized_title
        if not text:
            return features

        cleaned = cls.cleanup_text(text)

        if cls.is_multi_model(cleaned):
            features.is_multi_model = True
            return features

        family = cls.extract_family(cleaned)
        generation = cls.extract_generation(cleaned, family)
        variant = cls.extract_variant(cleaned)

        if family:
            features.family = cls.FAMILY_DISPLAY.get(family, family.title())

        if generation:
            features.generation = generation

        if variant:
            features.variant = variant

        return features

    @classmethod
    def cleanup_text(cls, text: str) -> str:
        cleaned = text.lower().strip()
        cleaned = cleaned.replace("мм", "mm")

        for noise in cls.NOISE_WORDS:
            cleaned = re.sub(rf"\b{re.escape(noise)}\b", " ", cleaned)

        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        return cleaned

    @classmethod
    def is_multi_model(cls, text: str) -> bool:
        if not text:
            return False


    @classmethod
    def extract_family(cls, text: str) -> str | None:
        for family in cls.FAMILIES:
            if re.search(rf"\b{re.escape(family)}\b", text):
                return family
        return None

    @classmethod
    def extract_generation(cls, text: str, family: str | None) -> str | None:
        if not family:
            return None

    @classmethod
    def extract_variant(cls, text: str) -> str | None:
        found: list[str] = []