import re
from typing import Optional

from app.core.constants import COLOR_MAP
from app.utils.text_normalizer import normalize_text


MAX_WARRANTY_YEARS = 5
MAX_WARRANTY_MONTHS = MAX_WARRANTY_YEARS * 12
MAX_WARRANTY_DAYS = MAX_WARRANTY_YEARS * 365


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
    def extract_warranty(description: object = "", title: object = "") -> Optional[str]:
        raw_parts = []
        for value in (title, description):
            if value is None:
                continue

            raw = str(value).strip()
            if not raw or raw.lower() in {"nan", "none", "<na>", "nat"}:
                continue

            raw_parts.append(raw)

        text = normalize_text(" ".join(raw_parts))
        if not text:
            return None

        unit_pattern = (
            r"дн(?:ей|я)?|день|дня|дней|day|days|"
            r"мес(?:яц(?:ев|а)?)?|month|months|"
            r"год|года|лет|year|years"
        )
        warranty_word = r"(?:гарант\w*|warranty)"

        # Only durations tied to warranty are exported; delivery/review periods must not leak in.
        forward_match = re.search(
            rf"\b{warranty_word}\b(?:\s+(?:до|на|от|срок|период))*\s*(\d+)\s*({unit_pattern})\b",
            text,
        )
        reverse_match = re.search(
            rf"\b(\d+)\s*({unit_pattern})\b(?:\s+\w+){{0,3}}\s+\b{warranty_word}\b",
            text,
        )
        bare_duration_match = re.fullmatch(
            rf"(?:до|на|от)?\s*(\d+)\s*({unit_pattern})",
            text,
        )

        match = forward_match or reverse_match or bare_duration_match

        if match:
            value = int(match.group(1))
            unit = match.group(2)

            if value <= 0:
                return None

            if unit.startswith("дн") or unit in {"день", "дня", "дней", "day", "days"}:
                if value > MAX_WARRANTY_DAYS:
                    return None
                return f"{value} days"

            if unit.startswith("мес") or unit in {"month", "months"}:
                if value > MAX_WARRANTY_MONTHS:
                    return None
                return f"{value} months"

            if unit.startswith("год") or unit == "лет" or unit in {"year", "years"}:
                if value > MAX_WARRANTY_YEARS:
                    return None
                return f"{value} years"

        return None

    @staticmethod
    def extract_article(url: str) -> Optional[str]:
        if not url:
            return None

        match = re.search(r"(?:_|/)(\d{6,})(?:[/?#]|$)", str(url))
        if match:
            return match.group(1)

        return None
