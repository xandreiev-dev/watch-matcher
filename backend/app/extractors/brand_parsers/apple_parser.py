import re
from app.schemas.watch_features import WatchFeatures


class AppleParser:
    FAMILIES = [
        "ultra",
        "se",
        "series",
    ]

    FAMILY_DISPLAY = {
        "ultra": "Ultra",
        "se": "SE",
        "series": "Series",
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
        "apple",
        "gps",
        "lte",
        "cellular",
    ]

    SIMPLE_VARIANTS = [
        "nike",
        "hermes",
        "titanium",
        "stainless steel",
        "aluminium",
        "aluminum",
        "ceramic",
        "sport",
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
        cleaned = cleaned.replace("-", " ")

        for noise in cls.NOISE_WORDS:
            cleaned = re.sub(rf"\b{re.escape(noise)}\b", " ", cleaned)

        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        return cleaned

    @classmethod
    def is_multi_model(cls, text: str) -> bool:
        if not text:
            return False

        # разные family в одной строке
        if "/" in text:
            family_hits = 0
            for family in cls.FAMILIES:
                if re.search(rf"\b{re.escape(family)}\b", text):
                    family_hits += 1
            if family_hits >= 2:
                return True

        # ultra 1 / ultra 2
        if re.search(r"\bultra\s+\d+\s*/\s*(?:ultra\s+)?\d+\b", text):
            return True

        # se 1 / se 2
        if re.search(r"\bse\s+\d+\s*/\s*(?:se\s+)?\d+\b", text):
            return True

        # series 9 / 10 / 11
        if re.search(r"\bseries\s+\d+\s*/\s*(?:series\s+)?\d+\b", text):
            return True
        if re.search(r"\bseries\s+\d+\s*/\s*\d+\s*/\s*\d+\b", text):
            return True

        # s10 / s11
        if re.search(r"\bs\d+\s*/\s*s?\d+\b", text):
            return True

        # watch 11 / 10
        if re.search(r"\bwatch\s+\d+\s*/\s*\d+\b", text):
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
        # strict order: Ultra -> SE -> Series

        if re.search(r"\bultra\b", text):
            return "ultra"

        if re.search(r"\bse\b", text):
            return "se"

        if re.search(r"\bseries\b", text):
            return "series"

        # S11 / S10 / S9
        if re.search(r"\bs\d{1,2}\b", text):
            return "series"

        # Watch 11 / Watch 10
        if re.search(r"\bwatch\s+\d{1,2}\b", text):
            return "series"

        return None

    @classmethod
    def extract_generation(cls, text: str, family: str | None) -> str | None:
        if not family:
            return None

        if family == "ultra":
            match = re.search(r"\bultra\s*(\d{1,2})\b", text)
            if match:
                return match.group(1)
            return None

        if family == "se":
            match = re.search(r"\bse\s*(\d{1,2})\b", text)
            if match:
                return match.group(1)
            return None

        if family == "series":
            # Series 11
            match = re.search(r"\bseries\s*(\d{1,2})\b", text)
            if match:
                return match.group(1)

            # S11
            match = re.search(r"\bs(\d{1,2})\b", text)
            if match:
                return match.group(1)

            # Watch 11
            match = re.search(r"\bwatch\s+(\d{1,2})\b", text)
            if match:
                return match.group(1)

        return None

    @classmethod
    def extract_variant(cls, text: str) -> str | None:
        found: list[str] = []

        if re.search(r"\baluminium\b", text) or re.search(r"\baluminum\b", text):
            found.append("Aluminum")

        if re.search(r"\btitanium\b", text) or re.search(r"\btitanum\b", text):
            found.append("Titanium")

        if re.search(r"\bstainless steel\b", text):
            found.append("Stainless Steel")

        if re.search(r"\bceramic\b", text):
            found.append("Ceramic")

        if re.search(r"\bnike\b", text):
            found.append("Nike")

        if re.search(r"\bhermes\b", text):
            found.append("Hermes")

        if re.search(r"\bsport\b", text):
            found.append("Sport")

        unique = []
        for item in found:
            if item not in unique:
                unique.append(item)

        return " ".join(unique) if unique else None