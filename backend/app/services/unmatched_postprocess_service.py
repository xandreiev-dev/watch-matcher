import re


class UnmatchedPostprocessService:
    @classmethod
    def apply(cls, title: str, brand: str | None) -> dict:
        normalized = cls.normalize_text(title)

        forced_brand = brand

        if re.search(r"\bforerunner\b", normalized):
            forced_brand = "Garmin"
        
        reordered_title = cls.reorder_number_model_patterns(normalized)

        changed = (
            forced_brand != (brand or "Unknown")
            or reordered_title != normalized
        )

        return {
            "brand": forced_brand,
            "normalized_title": reordered_title,
            "changed": changed,
        }

    @classmethod
    def detect_forced_brand(cls, text: str, current_brand: str | None) -> str:
        current = current_brand or "Unknown"

        # ЕДИНСТВЕННОЕ спец-правило по бренду:
        # if title contains "forerunner", force Garmin
        if re.search(r"\bforerunner\b", text):
            return "Garmin"

        return current

    @classmethod
    def reorder_number_model_patterns(cls, text: str) -> str:
        result = text

        patterns = [
            # 265 forerunner -> forerunner 265
            (r"\b(\d+[a-z]?)\s+(forerunner)\b", r"\2 \1"),

            # общие watch-кейсы, но без брендовых подмен:
            (r"\b(\d+[a-z]?)\s+(watch)\b", r"\2 \1"),
            (r"\b(\d+[a-z]?)\s+(fit)\b", r"\2 \1"),
            (r"\b(\d+[a-z]?)\s+(active)\b", r"\2 \1"),
            (r"\b(\d+[a-z]?)\s+(classic)\b", r"\2 \1"),
            (r"\b(\d+[a-z]?)\s+(ultra)\b", r"\2 \1"),
            (r"\b(\d+[a-z]?)\s+(pro)\b", r"\2 \1"),
            (r"\b(\d+[a-z]?)\s+(lite)\b", r"\2 \1"),
            (r"\b(\d+[a-z]?)\s+(mini)\b", r"\2 \1"),
            (r"\b(\d+[a-z]?)\s+(gt)\b", r"\2 \1"),
            (r"\b(\d+[a-z]?)\s+(se)\b", r"\2 \1"),
        ]

        for pattern, replacement in patterns:
            result = re.sub(pattern, replacement, result)

        result = re.sub(r"\s+", " ", result).strip()
        return result

    @classmethod
    def normalize_text(cls, text: str) -> str:
        text = (text or "").lower().strip()
        text = text.replace("-", " ")
        text = text.replace("_", " ")
        text = text.replace("ё", "е")
        text = re.sub(r"\s+", " ", text)
        return text