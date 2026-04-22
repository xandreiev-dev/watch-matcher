import re
from typing import Optional

from app.core.constants import COLOR_MAP
from app.utils.text_normalizer import normalize_text


class ExtractionService:
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
    def extract_article(url: str) -> Optional[str]:
        if not url:
            return None

        match = re.search(r"(?:_|/)(\d{6,})(?:[/?#]|$)", str(url))
        if match:
            return match.group(1)

        return None