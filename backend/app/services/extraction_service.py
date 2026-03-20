import re
from turtle import title
from xml.parsers.expat import model

from matplotlib import text


from app.core.constants import BRAND_ALIASES, COLOR_MAP, COMMON_BRANDS, MODEL_NOISE_TOKENS
from app.utils.text_normalizer import normalize_text, cleanup_model_text

class ExtractionService:
    @staticmethod
    def extract_brand(title: str, description: str = "") -> str:
        title_text = normalize_text(title)
        combined_text = normalize_text(f"{title} {description}")

        for alias, canonical in BRAND_ALIASES.items():
            pattern = rf"\b{re.escape(normalize_text(alias))}\b"

            if re.search(pattern, title_text):
                return canonical

        for alias, canonical in BRAND_ALIASES.items():
            pattern = rf"\b{re.escape(normalize_text(alias))}\b"

            if re.search(pattern, combined_text):
                return canonical

        return "Unknown"
    
    @staticmethod
    def extract_color(title: str, description: str = "") -> str:
        title_text = normalize_text(title)
        description_text = normalize_text(description)

        sorted_colors = sorted(COLOR_MAP.items(), key=lambda item: len(item[0]), reverse=True)

        for raw_color, normalized_color in sorted_colors:
            if re.search(rf"\b{re.escape(raw_color)}\b", title_text):
                return normalized_color

        for raw_color, normalized_color in sorted_colors:
            if re.search(rf"\bцвет\b.*\b{re.escape(raw_color)}\b", description_text):
                return normalized_color
            if re.search(rf"\b{re.escape(raw_color)}\b.*\bцвет\b", description_text):
                return normalized_color
        return ""
    
    @staticmethod
    def extract_warranty(description: str) -> str:
        text = normalize_text(description)

        forward_match = re.search(
            r"(?:гарант(?:ия)?|warranty)\s*[:\-]?\s*(\d+)\s*(дн(?:ей|я)?|day|days|мес(?:яц(?:ев|а)?)?|month|months|год|года|лет|year|years)",
            text
        )

        reverse_match = re.search(
            r"(\d+)\s*(дн(?:ей|я)?|day|days|мес(?:яц(?:ев|а)?)?|month|months|год|года|лет|year|years)\s*(?:гарант(?:ия)?|warranty)",
            text
        )

        match = forward_match or reverse_match

        if match:
            value = int(match.group(1))
            unit = match.group(2)

            if unit.startswith("дн") or unit in {"day", "days"}:
                return f"{value} days"

            if unit.startswith("мес") or unit in {"month", "months"}:
                return f"{value} months"

            if unit.startswith("год") or unit == "лет" or unit in {"year", "years"}:
                return f"{value * 12} months"

        if "гарант" in text or "warranty" in text:
            return "Warranty mentioned"

        return ""
    
    @staticmethod
    def extract_model(title: str, brand: str) -> str:
        text = normalize_text(title)
        ACCESSORY_KEYWORDS = [
            "ремешок",
            "браслет",
            "strap",
            "band for",
            "loop",
        ]

        if any(keyword in text for keyword in ACCESSORY_KEYWORDS):
            return ""

        if brand != "Unknown":
            text = re.sub(rf"\b{re.escape(brand.lower())}\b", " ", text)

        text = cleanup_model_text(text)

        WATCH_PATTERN = r"(watch\s?(?:gt\s?)?\d+[a-z]?\s?(?:pro)?)"
        BAND_PATTERN = r"(band\s?\d+)"
        GT_PATTERN = r"(gt\s?\d+[a-z]?)"
        ULTRA_PATTERN = r"(watch\s?ultra|ultra)"
        SE_PATTERN = r"(watch\s?se)"
        SERIES_PATTERN = r"(series\s?\d+)"

        patterns = [
            WATCH_PATTERN,
            BAND_PATTERN,
            GT_PATTERN,
            ULTRA_PATTERN,
            SE_PATTERN,
            SERIES_PATTERN,
        ]

        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(1).strip().title()

        color_words = {normalize_text(key) for key in COLOR_MAP.keys()}
        tokens = []

        for token in text.split():
            if token in color_words:
                continue
            if token in MODEL_NOISE_TOKENS:
                continue
            tokens.append(token)

        model = " ".join(tokens).strip()

        if model.isdigit():
            return ""

        return model.title() if model else ""