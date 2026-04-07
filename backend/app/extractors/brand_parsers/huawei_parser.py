import re
from app.schemas.watch_features import WatchFeatures


class HuaweiParser:
    FAMILIES = [
        "gt",
        "fit",
        "band",
        "kids",
        "d",
        "watch",
    ]

    FAMILY_DISPLAY = {
        "gt": "GT",
        "fit": "Fit",
        "band": "Band",
        "kids": "Kids",
        "d": "D",
        "watch": "Watch",
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
            print("AD PARSED FEATURES:", {
                "family": features.family,
                "generation": features.generation,
                "variant": features.variant,
            })
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

        # 1. Явные перечисления через /
        if re.search(r"\bwatch\s*\d+\s*/\s*\d+\b", text):
            return True

        if re.search(r"\bgt\s*\d+\s*/\s*\d+\b", text):
            return True

        if re.search(r"\bfit\s*\d+\s*/\s*\d+\b", text):
            return True

        if re.search(r"\bband\s*\d+\s*/\s*\d+\b", text):
            return True

        # 2. Полные перечисления моделей
        if re.search(r"\bwatch\s*\d+\b.*\/.*\bwatch\s*\d+\b", text):
            return True

        if re.search(r"\bgt\s*\d+\b.*\/.*\bgt\s*\d+\b", text):
            return True

        if re.search(r"\bfit\s*\d+\b.*\/.*\bfit\s*\d+\b", text):
            return True

        if re.search(r"\bband\s*\d+\b.*\/.*\bband\s*\d+\b", text):
            return True

        # 3. Несколько размеров
        size_hits = re.findall(r"\b\d{2}mm\b", text)
        if len(set(size_hits)) > 1:
            return True

        # 4. Много слешей
        if text.count("/") >= 2:
            return True

        return False

    @classmethod
    def extract_family(cls, text: str) -> str | None:
        if re.search(r"\bwatch\s+d\d*\b", text) or re.search(r"\bwatch\s+d\b", text):
            return "d"

        if re.search(r"\bwatch\s+fit\b", text) or re.search(r"\bfit\b", text):
            return "fit"

        if re.search(r"\bwatch\s+gt\b", text) or re.search(r"\bgt\b", text):
            return "gt"

        if re.search(r"\bband\b", text):
            return "band"

        if re.search(r"\bkids\b", text):
            return "kids"

        if re.search(r"\bwatch\b", text):
            return "watch"

        return None

    @classmethod
    def extract_generation(cls, text: str, family: str | None) -> str | None:
        if not family:
            return None

        if family == "d":
            match = re.search(r"\bwatch\s+d\s*(\d+)\b", text)
            if match:
                return match.group(1)
            return None

        if family == "fit":
            match = re.search(r"\b(?:watch\s+)?fit\s*(\d+)\b", text)
            if match:
                return match.group(1)
            return None

        if family == "gt":
            match = re.search(r"\b(?:watch\s+)?gt\s*(\d+)\b", text)
            if match:
                return match.group(1)
            return None

        if family == "band":
            match = re.search(r"\bband\s*(\d+)\b", text)
            if match:
                return match.group(1)
            return None

        if family == "kids":
            match = re.search(r"\bkids\s*(?:watch\s*)?(\d+)\b", text)
            if match:
                return match.group(1)
            return None

        if family == "watch":
            match = re.search(r"\bwatch\s*(\d+)\b", text)
            if match:
                return match.group(1)
            return None

        return None

    @classmethod
    def extract_variant(cls, text: str) -> str | None:
        found: list[str] = []

        if re.search(r"\bultimate\b", text):
            found.append("Ultimate")
        if re.search(r"\bpro\b", text):
            found.append("Pro")
        if re.search(r"\bclassic\b", text):
            found.append("Classic")
        if re.search(r"\bactive\b", text):
            found.append("Active")
        if re.search(r"\belite\b", text):
            found.append("Elite")
        if re.search(r"\bceramic\b", text):
            found.append("Ceramic")
        if re.search(r"\btitanium\b", text):
            found.append("Titanium")
        if re.search(r"\bstainless steel\b", text):
            found.append("Stainless Steel")

        unique: list[str] = []
        for item in found:
            if item not in unique:
                unique.append(item)

        return " ".join(unique) if unique else None