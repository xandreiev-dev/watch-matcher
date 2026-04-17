import re
from app.schemas.watch_features import WatchFeatures


class GoogleParser:
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
        "смартчасы",
        "часы",
        "google",
    ]

    MULTI_MODEL_PATTERNS = [
        r"\b\d{2}\s*mm\s*/\s*\d{2}\s*mm\b",
        r"\b\d{2}\s*mm\s*,\s*\d{2}\s*mm\b",
        r"\b\d{2}\s*/\s*\d{2}\s*mm\b",
    ]

    @classmethod
    def parse(cls, features: WatchFeatures) -> WatchFeatures:
        text = features.normalized_title or ""
        if not text:
            return features

        cleaned = cls.cleanup_text(text)

        if cls.is_multi_model(cleaned):
            features.is_multi_model = True
            return features

        parsed = cls.extract_model_fields(cleaned)

        if parsed["family"]:
            features.family = parsed["family"]

        if parsed["generation"]:
            features.generation = parsed["generation"]

        if parsed["variant"]:
            features.variant = parsed["variant"]

        model_candidates = cls.build_model_candidates(
            family=parsed["family"],
            generation=parsed["generation"],
            size_mm=features.size_mm,
        )
        if model_candidates:
            features.model_candidates = model_candidates

        variant_name = cls.build_variant_name(
            family=parsed["family"],
            generation=parsed["generation"],
            size_mm=features.size_mm,
        )
        if variant_name:
            features.extracted_variant_name = variant_name

        print("==== GOOGLE EXTRACT DEBUG ====")
        print("TITLE:", features.normalized_title)
        print("BRAND:", features.brand)
        print("FAMILY:", features.family)
        print("GENERATION:", features.generation)
        print("VARIANT:", features.variant)
        print("MODEL_CANDIDATES:", features.model_candidates)
        print("EXTRACTED_VARIANT_NAME:", features.extracted_variant_name)
        print("==============================")

        return features

    @classmethod
    def cleanup_text(cls, text: str) -> str:
        cleaned = text.lower().strip()
        cleaned = cleaned.replace("мм", "mm")
        cleaned = cleaned.replace("-", " ")
        cleaned = cleaned.replace("_", " ")
        cleaned = cleaned.replace(",", " ")
        cleaned = cleaned.replace("/", " / ")
        cleaned = cleaned.replace("(", " ")
        cleaned = cleaned.replace(")", " ")

        for noise in cls.NOISE_WORDS:
            cleaned = re.sub(rf"\b{re.escape(noise)}\b", " ", cleaned)

        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        return cleaned

    @classmethod
    def is_multi_model(cls, text: str) -> bool:
        if not text:
            return False

        for pattern in cls.MULTI_MODEL_PATTERNS:
            if re.search(pattern, text):
                return True

        sizes = re.findall(r"\b(41|45)\s*mm\b", text)
        if len(set(sizes)) > 1:
            return True

        generations = re.findall(r"\bpixel\s+watch\s*(\d{1,2})\b", text)
        if len(set(generations)) > 1:
            return True

        return False

    @classmethod
    def extract_model_fields(cls, text: str) -> dict:
        family = None
        generation = None
        variant = None

        if re.search(r"\bpixel\s+watch\b", text):
            family = "Watch"

            # Pixel Watch 2 / 3 / 4
            m = re.search(r"\bpixel\s+watch\s*(\d{1,2})\b", text)
            if m:
                generation = m.group(1)

        return {
            "family": family,
            "generation": generation,
            "variant": variant,
        }

    @classmethod
    def build_model_candidates(
        cls,
        family: str | None,
        generation: str | None,
        size_mm: int | None,
    ) -> list[str]:
        if not family:
            return []

        candidates: list[str] = []

        # Pixel Watch (1 поколение без цифры)
        if not generation:
            candidates.append("pixel watch")

        # Pixel Watch 2/3/4
        if generation:
            if size_mm:
                candidates.append(f"pixel watch {generation} {int(size_mm)}mm")
            candidates.append(f"pixel watch {generation}")

        result: list[str] = []
        seen = set()

        for item in candidates:
            item = re.sub(r"\s+", " ", item).strip()
            if item and item not in seen:
                seen.add(item)
                result.append(item)

        return result

    @classmethod
    def build_variant_name(
        cls,
        family: str | None,
        generation: str | None,
        size_mm: int | None,
    ) -> str | None:
        if not family:
            return None

        parts: list[str] = ["Pixel Watch"]

        if generation:
            parts.append(generation)

        if size_mm:
            parts.append(f"{int(size_mm)}mm")

        return " ".join(parts).strip()