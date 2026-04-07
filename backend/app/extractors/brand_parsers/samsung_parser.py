import re
from app.schemas.watch_features import WatchFeatures


class SamsungParser:
    FAMILY_DISPLAY = {
        "watch": "Watch",
        "active": "Active",
        "fit": "Fit",
    }

    NOISE_WORDS = [
        "новые",
        "новый",
        "новая",
        "новое",
        "русский",
        "русский язык",
        "рф",
        "все цвета",
        "в наличии",
        "оригинал",
        "оригинальные",
        "ориг",
        "гарантия",
        "умные часы",
        "смарт часы",
        "смарт-часы",
        "часы",
        "samsung",
        "galaxy",
        "gps",
        "lte",
        "cellular",
        "bluetooth",
    ]

    SIMPLE_VARIANTS = [
        "classic",
        "ultra",
        "pro",
        "fe",
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
        variant = cls.extract_variant(cleaned, family, generation)

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
        cleaned = cleaned.replace("-", " ")

        for noise in cls.NOISE_WORDS:
            cleaned = re.sub(rf"\b{re.escape(noise)}\b", " ", cleaned)

        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        return cleaned

    @classmethod
    def is_multi_model(cls, text: str) -> bool:
        if not text:
            return False

        # watch 6 / 7
        if re.search(r"\bwatch\s+\d+\s*/\s*(?:watch\s+)?\d+\b", text):
            return True

        # watch 6 / 7 / ultra
        if re.search(r"\bwatch\s+\d+\s*/\s*\d+\s*/\s*(classic|ultra|pro|fe)\b", text):
            return True

        # active 2 / active 3
        if re.search(r"\bactive\s+\d+\s*/\s*(?:active\s+)?\d+\b", text):
            return True

        # fit 2 / fit 3
        if re.search(r"\bfit\s+\d+\s*/\s*(?:fit\s+)?\d+\b", text):
            return True

        # watch7 / watch6
        if re.search(r"\bwatch\d+\s*/\s*watch?\d+\b", text):
            return True

        # classic / ultra / pro в одной строке через /
        if "/" in text:
            variant_hits = 0
            for variant in ["classic", "ultra", "pro", "fe"]:
                if re.search(rf"\b{re.escape(variant)}\b", text):
                    variant_hits += 1
            if variant_hits >= 2:
                return True

        # несколько размеров
        size_hits = re.findall(r"\b\d{2}mm\b", text)
        if len(set(size_hits)) > 1:
            return True

        if text.count("/") >= 2:
            return True

        return False

    @classmethod
    def extract_family(cls, text: str) -> str | None:
        # Galaxy Fit
        if re.search(r"\bfit\b", text):
            return "fit"

        # Galaxy Watch Active
        if re.search(r"\bactive\b", text):
            return "active"

        # Базовая линейка Galaxy Watch
        if re.search(r"\bwatch\b", text) or re.search(r"\bwatch\d+\b", text):
            return "watch"

        return None

    @classmethod
    def extract_generation(cls, text: str, family: str | None) -> str | None:
        if not family:
            return None

        if family == "fit":
            match = re.search(r"\bfit\s*(\d{1,2})\b", text)
            if match:
                return match.group(1)
            return None

        if family == "active":
            match = re.search(r"\bactive\s*(\d{1,2})\b", text)
            if match:
                return match.group(1)
            return None

        if family == "watch":
            # watch 7
            match = re.search(r"\bwatch\s*(\d{1,2})\b", text)
            if match:
                return match.group(1)

            # watch7
            match = re.search(r"\bwatch(\d{1,2})\b", text)
            if match:
                return match.group(1)

        return None

    @classmethod
    def extract_variant(
        cls,
        text: str,
        family: str | None = None,
        generation: str | None = None,
    ) -> str | None:
        found: list[str] = []

        # Для Galaxy Watch
        if family == "watch":
            if re.search(r"\bclassic\b", text):
                found.append("Classic")

            if re.search(r"\bultra\b", text):
                found.append("Ultra")

            if re.search(r"\bpro\b", text):
                found.append("Pro")

            if re.search(r"\bfe\b", text):
                found.append("FE")

        unique = []
        for item in found:
            if item not in unique:
                unique.append(item)

        return " ".join(unique) if unique else None