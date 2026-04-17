import re
from app.schemas.watch_features import WatchFeatures


class HuaweiParser:
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
        "huawei",
    ]

    MULTI_MODEL_PATTERNS = [
        r"\bwatch\s*\d+\s*/\s*\d+\b",
        r"\bgt\s*\d+\s*/\s*\d+\b",
        r"\bfit\s*\d+\s*/\s*\d+\b",
        r"\bband\s*\d+\s*/\s*\d+\b",
        r"\bwatch\s*\d+\b.*\/.*\bwatch\s*\d+\b",
        r"\bgt\s*\d+\b.*\/.*\bgt\s*\d+\b",
        r"\bfit\s*\d+\b.*\/.*\bfit\s*\d+\b",
        r"\bband\s*\d+\b.*\/.*\bband\s*\d+\b",
        r"\b\d{2}\s*mm\s*/\s*\d{2}\s*mm\b",
        r"\b\d{2}\s*mm\s*,\s*\d{2}\s*mm\b",
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
            variant=parsed["variant"],
            size_mm=features.size_mm,
        )
        if model_candidates:
            features.model_candidates = model_candidates

        variant_name = cls.build_variant_name(
            family=parsed["family"],
            generation=parsed["generation"],
            variant=parsed["variant"],
            size_mm=features.size_mm,
        )
        if variant_name:
            features.extracted_variant_name = variant_name

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

        cleaned = re.sub(r"\bgt(\d+)\b", r"gt \1", cleaned)
        cleaned = re.sub(r"\bfit(\d+)\b", r"fit \1", cleaned)
        cleaned = re.sub(r"\bd(\d+)\b", r"d \1", cleaned)

        # кривые записи типа "watch 6gt pro" -> "watch gt 6 pro"
        cleaned = re.sub(r"\bwatch\s+(\d+)\s*gt\b", r"watch gt \1", cleaned)
        cleaned = re.sub(r"\bwatch\s+(\d+)\s*fit\b", r"watch fit \1", cleaned)

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

        size_hits = re.findall(r"\b\d{2}\s*mm\b", text)
        if len(set(size_hits)) > 1:
            return True

        if text.count("/") >= 2:
            return True

        return False

    @classmethod
    def extract_model_fields(cls, text: str) -> dict:
        family = None
        generation = None
        found_variants: list[str] = []

        normalized = f" {text} "

        # подстраховка под кривые записи типа "watch 6gt pro"
        normalized = re.sub(r"\bwatch\s+(\d+)\s*gt\b", r"watch gt \1", normalized)
        normalized = re.sub(r"\bwatch\s+gt\s*(\d+)gt\b", r"watch gt \1", normalized)
        normalized = re.sub(r"\bgt(\d+)\b", r"gt \1", normalized)
        normalized = re.sub(r"\bfit(\d+)\b", r"fit \1", normalized)
        normalized = re.sub(r"\bd(\d+)\b", r"d \1", normalized)
        normalized = re.sub(r"\s+", " ", normalized).strip()

        # 1. Watch D / D2
        if re.search(r"\bwatch\s+d\b", normalized) or re.search(r"\bwatch\s+d\s*\d+\b", normalized):
            family = "D"
            m = re.search(r"\bwatch\s+d\s*(\d+)\b", normalized)
            if m:
                generation = m.group(1)

        # 2. Watch Fit
        elif re.search(r"\bwatch\s+fit\b", normalized) or re.search(r"\bfit\b", normalized):
            family = "Fit"

            m = re.search(r"\b(?:watch\s+)?fit\s*(\d+)\b", normalized)
            if m:
                generation = m.group(1)

            if re.search(r"\bmini\b", normalized):
                found_variants.append("Mini")

            if re.search(r"\bspecial edition\b", normalized):
                found_variants.append("Special Edition")

            if re.search(r"\belegant\b", normalized):
                found_variants.append("Elegant")

            if re.search(r"\bpro\b", normalized):
                found_variants.append("Pro")

        # 3. Watch GT
        elif re.search(r"\bwatch\s+gt\b", normalized) or re.search(r"\bgt\b", normalized):
            family = "GT"

            m = re.search(r"\b(?:watch\s+)?gt\s*(\d+)\b", normalized)
            if m:
                generation = m.group(1)

            if re.search(r"\b2e\b", normalized):
                found_variants.append("2e")

            if re.search(r"\bpro\b", normalized):
                found_variants.append("Pro")

            if re.search(r"\bse\b", normalized):
                found_variants.append("SE")

            if re.search(r"\brunner\b", normalized):
                found_variants.append("Runner")
                m2 = re.search(r"\brunner\s*(\d+)\b", normalized)
                if m2:
                    found_variants.append(m2.group(1))

            if re.search(r"\bcyber\b", normalized):
                found_variants.append("Cyber")

            if re.search(r"\bporsche design\b", normalized):
                found_variants.append("Porsche Design")

        # 4. Watch Ultimate
        elif re.search(r"\bwatch\s+ultimate\b", normalized):
            family = "Watch"
            found_variants.append("Ultimate")

            m = re.search(r"\bultimate\s*(\d+)\b", normalized)
            if m:
                generation = m.group(1)

            if re.search(r"\bdesign\b", normalized):
                found_variants.append("Design")

        # 5. Watch Buds
        elif re.search(r"\bwatch\s+buds\b", normalized):
            family = "Watch"
            found_variants.append("Buds")

        # 6. Watch Magic
        elif re.search(r"\bwatch\s+magic\b", normalized):
            family = "Watch"
            found_variants.append("Magic")

        # 7. Kids / Children's Watch
        elif re.search(r"\bchildren'?s\s+watch\b", normalized) or re.search(r"\bkids\b", normalized):
            family = "Kids"
            m = re.search(r"\b(?:children'?s\s+watch|kids(?:\s+watch)?)\s*(\d+[a-z]?)\b", normalized)
            if m:
                generation = m.group(1).upper()

        # 8. Только теперь обычный Watch 2/3/4/5
        elif re.search(r"\bwatch\b", normalized):
            family = "Watch"

            m = re.search(r"\bwatch\s*(\d+)\b", normalized)
            if m:
                generation = m.group(1)

            if re.search(r"\bclassic\b", normalized):
                found_variants.append("Classic")

            if re.search(r"\bpro\b", normalized):
                found_variants.append("Pro")

        unique = []
        for item in found_variants:
            if item not in unique:
                unique.append(item)

        variant = " ".join(unique) if unique else None

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
        variant: str | None,
        size_mm: int | None,
    ) -> list[str]:
        if not family:
            return []

        candidates: list[str] = []

        if family == "D":
            if generation:
                if size_mm:
                    candidates.append(f"watch d{generation} {int(size_mm)}mm")
                    candidates.append(f"watch d {generation} {int(size_mm)}mm")
                candidates.append(f"watch d{generation}")
                candidates.append(f"watch d {generation}")
            candidates.append("watch d")

        elif family == "Fit":
            if generation and variant:
                if size_mm:
                    candidates.append(f"watch fit {generation} {variant.lower()} {int(size_mm)}mm")
                candidates.append(f"watch fit {generation} {variant.lower()}")
            if generation:
                if size_mm:
                    candidates.append(f"watch fit {generation} {int(size_mm)}mm")
                candidates.append(f"watch fit {generation}")
            if variant and not generation:
                if size_mm:
                    candidates.append(f"watch fit {variant.lower()} {int(size_mm)}mm")
                candidates.append(f"watch fit {variant.lower()}")
            if size_mm and not generation and not variant:
                candidates.append(f"watch fit {int(size_mm)}mm")
            candidates.append("watch fit")

        elif family == "GT":
            if generation and variant:
                if size_mm:
                    candidates.append(f"watch gt {generation} {variant.lower()} {int(size_mm)}mm")
                candidates.append(f"watch gt {generation} {variant.lower()}")

            if generation:
                if size_mm:
                    candidates.append(f"watch gt {generation} {int(size_mm)}mm")
                candidates.append(f"watch gt {generation}")

            if variant and not generation:
                if size_mm:
                    candidates.append(f"watch gt {variant.lower()} {int(size_mm)}mm")
                candidates.append(f"watch gt {variant.lower()}")

            candidates.append("watch gt")

        elif family == "Kids":
            if generation:
                candidates.append(f"children's watch {generation.lower()}")
                candidates.append(f"kids watch {generation.lower()}")
            candidates.append("children's watch")
            candidates.append("kids watch")

        elif family == "Watch":
            if generation and variant:
                if size_mm:
                    candidates.append(f"watch {generation} {variant.lower()} {int(size_mm)}mm")
                candidates.append(f"watch {generation} {variant.lower()}")

            if generation:
                if size_mm:
                    candidates.append(f"watch {generation} {int(size_mm)}mm")
                candidates.append(f"watch {generation}")

            if variant and not generation:
                if size_mm:
                    candidates.append(f"watch {variant.lower()} {int(size_mm)}mm")
                candidates.append(f"watch {variant.lower()}")

            candidates.append("watch")

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
        variant: str | None,
        size_mm: int | None,
    ) -> str | None:
        if not family:
            return None

        if family == "GT":
            parts = ["Watch GT"]
        elif family == "Fit":
            parts = ["Watch Fit"]
        elif family == "D":
            parts = ["Watch D"]
        elif family == "Kids":
            parts = ["Children's Watch"]
        else:
            parts = ["Watch"]

        if generation:
            if family == "D":
                parts[-1] = f"{parts[-1]}{generation}"
            else:
                parts.append(str(generation))

        if variant:
            parts.append(variant)

        if size_mm:
            parts.append(f"{int(size_mm)}mm")

        return " ".join(parts).strip()