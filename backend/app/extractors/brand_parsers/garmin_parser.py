import re
from app.schemas.watch_features import WatchFeatures


class GarminParser:
    FAMILIES = [
        "forerunner",
        "fenix",
        "enduro",
        "epix",
        "instinct",
        "venu",
        "vivoactive",
        "vivomove",
        "tactix",
        "marq",
        "descent",
        "quatix",
        "approach",
    ]

    FAMILY_DISPLAY = {
        "forerunner": "Forerunner",
        "fenix": "Fenix",
        "enduro": "Enduro",
        "epix": "Epix",
        "instinct": "Instinct",
        "venu": "Venu",
        "vivoactive": "Vivoactive",
        "vivomove": "Vivomove",
        "tactix": "Tactix",
        "marq": "Marq",
        "descent": "Descent",
        "quatix": "Quatix",
        "approach": "Approach",
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

        # 1. разные family в одной строке через /
        found_families = [
            family for family in cls.FAMILIES
            if re.search(rf"\b{re.escape(family)}\b", text)
        ]
        if "/" in text and len(found_families) >= 2:
            return True

        # 2. одна family, но несколько моделей:
        # forerunner 970 / forerunner 570
        for family in cls.FAMILIES:
            if re.search(
                rf"\b{re.escape(family)}\s+[a-z]?\d+[a-z]?\s*/\s*(?:{re.escape(family)}\s+)?[a-z]?\d+[a-z]?\b",
                text,
            ):
                return True

        # 3. одна family и 3 поколения:
        # forerunner 970 / 965 / 570
        for family in cls.FAMILIES:
            if re.search(
                rf"\b{re.escape(family)}\s+[a-z]?\d+[a-z]?\s*/\s*[a-z]?\d+[a-z]?\s*/\s*[a-z]?\d+[a-z]?\b",
                text,
            ):
                return True

        # 4. одна family + несколько размеров:
        # fenix 8 51mm / 47mm
        for family in cls.FAMILIES:
            if re.search(
                rf"\b{re.escape(family)}\s+[a-z]?\d+[a-z]?.*\b\d{{2}}mm\s*/\s*\d{{2}}mm\b",
                text,
            ):
                return True

        # 5. одна и та же family, но через / перечислены разные variant-конфигурации
        # tactix 8 amoled / tactix 8 solar ballistics
        # tactix 8 solar ballistics 51mm / amoled 47
        for family in cls.FAMILIES:
            if re.search(
                rf"\b{re.escape(family)}\s+[a-z]?\d+[a-z]?.*/.*(?:amoled|solar|sapphire|ballistics)",
                text
            ) and "/" in text:
                return True

        # 6. несколько размеров вообще
        size_hits = re.findall(r"\b\d{2}mm\b", text)
        if len(set(size_hits)) > 1:
            return True

        # 7. много слешей — почти всегда сборная строка
        if text.count("/") >= 2:
            return True

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

        # family + число: forerunner 970 / fenix 8 / enduro 3 / venu 4
        m = re.search(rf"\b{re.escape(family)}\s+(\d+[a-z]?)\b", text)
        if m:
            return m.group(1).upper()

        # family + X1 / S70
        m = re.search(rf"\b{re.escape(family)}\s+([a-z]\d+[a-z]?)\b", text)
        if m:
            return m.group(1).upper()

        return None

    @classmethod
    def extract_variant(cls, text: str) -> str | None:
        found: list[str] = []

        if re.search(r"\bsapphire\s+solar\b", text):
            found.append("Sapphire Solar")
            text = re.sub(r"\bsapphire\s+solar\b", " ", text)

        if re.search(r"\bamoled\s+sapphire\b", text):
            found.append("AMOLED Sapphire")
            text = re.sub(r"\bamoled\s+sapphire\b", " ", text)

        if re.search(r"\bsolar\b", text):
            found.append("Solar")

        if re.search(r"\bsapphire\b", text):
            found.append("Sapphire")

        if re.search(r"\bamoled\b", text):
            found.append("AMOLED")

        if re.search(r"\bpro\b", text):
            found.append("Pro")

        if re.search(r"\bmusic\b", text):
            found.append("Music")

        if re.search(r"\bballistics\b", text):
            found.append("Ballistics")

        if not found:
            return None

        unique = []
        for item in found:
            if item not in unique:
                unique.append(item)

        return " ".join(unique)