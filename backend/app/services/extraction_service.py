import re

from typing import Optional

from app.core.constants import BRAND_ALIASES, COLOR_MAP, COMMON_BRANDS, MODEL_NOISE_TOKENS
from app.utils.text_normalizer import normalize_text, cleanup_model_text

class ExtractionService:
    """
    Service responsible for extracting structured data (brand, model, color, warranty)
    from raw listing text (title + description).

    The goal is to normalize noisy marketplace data into consistent fields
    for further matching with vendor models.
    """
    @staticmethod
    def extract_brand(title: str, description: str = "") -> str:
        """
        Extracts brand using alias dictionary.

        Priority:
        1. Exact match in title
        2. Match in title + description

        Returns canonical brand name or "Unknown".
        """
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
        """
        Extracts brand using alias dictionary.

        Priority:
        1. Exact match in title
        2. Match in title + description

        Returns canonical brand name or "Unknown".
        """
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

        match = re.search(r'(?:_|/)(\d{6,})(?:[/?#]|$)', str(url))
        if match:
            return match.group(1)

        return None
    
    @staticmethod
    def extract_model(title: str, brand: str) -> str:
        """
        Extracts product model from title.

        Strategy:
        - Remove brand and noise
        - Handle brand-specific patterns (Apple, Samsung, Huawei, etc.)
        - Apply regex-based fallback patterns

        Also filters out accessories (straps, cases, etc.).

        Returns normalized model or empty string.
        """
        text = normalize_text(title)

        accessory_keywords = [
            "ремешок",
            "браслет",
            "strap",
            "band for",
            "loop",
            "клипса",
            "clip",
        ]

        if any(keyword in text for keyword in accessory_keywords):
            return ""

        if brand != "Unknown":
            text = re.sub(rf"\b{re.escape(brand.lower())}\b", " ", text)

        text = cleanup_model_text(text)

        # Apple strict handling before generic regex
        if "series" in text:
            match = re.search(r"series\s?(\d{1,2})", text)
            if match:
                return f"Watch Series {match.group(1)}"

        if re.search(r"\bwatch\s?s\s?(\d{1,2})\b", text):
            match = re.search(r"\bwatch\s?s\s?(\d{1,2})\b", text)
            return f"Watch S{match.group(1)}"

        if re.search(r"\bse\s?(\d{1,2})\b", text):
            match = re.search(r"\bse\s?(\d{1,2})\b", text)
            return f"Watch Se {match.group(1)}"

        if re.search(r"\bwatch\s+se\b", text):
            if re.search(r"\bse\s?(\d{1,2})\b", text):
                m = re.search(r"\bse\s?(\d{1,2})\b", text)
                return f"Watch Se {m.group(1)}"
            return "Watch Se"
        
        # Samsung strict handling
        if re.search(r"galaxy\s+watch\s*(\d+)\s*classic", text):
            m = re.search(r"galaxy\s+watch\s*(\d+)\s*classic", text)
            return f"Watch {m.group(1)} Classic"

        if re.search(r"galaxy\s+watch\s*(\d+)\s*pro", text):
            m = re.search(r"galaxy\s+watch\s*(\d+)\s*pro", text)
            return f"Watch {m.group(1)} Pro"

        if re.search(r"galaxy\s+watch\s*(\d+)\s*ultra", text):
            m = re.search(r"galaxy\s+watch\s*(\d+)\s*ultra", text)
            return f"Watch {m.group(1)} Ultra"

        if re.search(r"watch\s*(\d+)\s*classic", text):
            m = re.search(r"watch\s*(\d+)\s*classic", text)
            return f"Watch {m.group(1)} Classic"

        if re.search(r"watch\s*(\d+)\s*pro", text):
            m = re.search(r"watch\s*(\d+)\s*pro", text)
            return f"Watch {m.group(1)} Pro"

        if re.search(r"watch\s*(\d+)\s*ultra", text):
            m = re.search(r"watch\s*(\d+)\s*ultra", text)
            return f"Watch {m.group(1)} Ultra"
        
        # Huawei Fit strict handling
        if re.search(r"watch\s+fit\s+(\d+)\s*pro", text):
            m = re.search(r"watch\s+fit\s+(\d+)\s*pro", text)
            return f"Watch Fit {m.group(1)} Pro"

        if re.search(r"watch\s+fit\s+(\d+)\s*se", text):
            m = re.search(r"watch\s+fit\s+(\d+)\s*se", text)
            return f"Watch Fit {m.group(1)} SE"

        if re.search(r"watch\s+fit\s+(\d+)", text):
            m = re.search(r"watch\s+fit\s+(\d+)", text)
            return f"Watch Fit {m.group(1)}"

        if re.search(r"watch\s+fit\s+se", text):
            return "Watch Fit SE"

        if re.search(r"\bfit\s+(\d+)\s*pro", text):
            m = re.search(r"\bfit\s+(\d+)\s*pro", text)
            return f"Watch Fit {m.group(1)} Pro"

        if re.search(r"\bfit\s+(\d+)", text):
            m = re.search(r"\bfit\s+(\d+)", text)
            return f"Watch Fit {m.group(1)}"
        
        if re.search(r"watch\s+se\s*\(?2\s*gen\)?", text):
            return "Watch SE 2"

        if re.search(r"watch\s+se\s*\(?3\s*gen\)?", text):
            return "Watch SE 3"
        
        # Honor MagicWatch strict handling
        if re.search(r"magic\s?watch\s?(\d+)", text):
            m = re.search(r"magic\s?watch\s?(\d+)", text)
            return f"MagicWatch {m.group(1)}"

        if re.search(r"magicwatch\s?(\d+)", text):
            m = re.search(r"magicwatch\s?(\d+)", text)
            return f"MagicWatch {m.group(1)}"
        
        # Moto Watch strict handling
        if re.search(r"(moto|motorola)\s+watch\s+fit", text):
            return "Moto Watch Fit"

        if re.search(r"(moto|motorola)\s+watch\s+100", text):
            return "Moto Watch 100"

        if re.search(r"(moto|motorola)\s+watch\s+40", text):
            return "Moto Watch 40"
        
        # OnePlus Watch strict handling
        if re.search(r"\bwatch\s?2r\b", text):
            return "Watch 2R"
        
        if re.search(r"\boneplus\s?2r\b", text):
            return "Watch 2R"

        patterns = [
            # Apple
            r"(watch\s?ultra\s?\d+|ultra\s?\d+)",
            r"(watch\s?se\s?\d+|se\s?\d+)",
            r"(watch\s?se)",
            r"(watch\s?series\s?\d+|series\s?\d+)",
            r"(watch\s?s\s?\d{1,2})",
            r"(watch\s?\d{1,2})",

            # Samsung
            r"(galaxy\s?watch\s?active\s?\d+)",
            r"(galaxy\s?watch\s?\d+\s?classic)",
            r"(galaxy\s?watch\s?\d+\s?pro)",
            r"(galaxy\s?watch\s?\d+\s?ultra)",
            r"(galaxy\s?watch\s?ultra)",
            r"(galaxy\s?watch\s?fe)",
            r"(galaxy\s?watch\s?\d+)",
            r"(galaxy\s?fit\s?\d+)",

            r"(watch\s?\d+\s?classic)",
            r"(watch\s?\d+\s?pro)",
            r"(watch\s?\d+\s?ultra)",
            r"(watch\s?ultra)",
            r"(watch\s?\d+)",
            r"(fit\s?\d+)",
            r"(active\s?\d+)",

            # Huawei / Honor
            r"(watch\s?gt\s?\d+\s?(?:pro)?)",
            r"(fit\s?\d+\s?(?:pro|se)?)",
            r"(band\s?\d+)",
            r"(watch\s?fit\s?\d+\s?(?:pro|se)?)",
            r"(watch\s?fit)",
            r"(fit\s?\d+\s?(?:pro|se)?)",
            r"(fit\s?\d+)",
            r"(fit\s?se)",
            r"(gt\s?\d+\s?(?:pro)?)",
            r"(watch\s?d\s?\d*)",
            r"(watch\s?ultimate)",
            r"(watch\s?\d+\s?(?:pro)?)",
            r"(kids\s?\d+\s?(?:plus|pro)?)",
            r"(magic\s?watch\s?\d+)",
            r"(magicwatch\s?\d+)",
            r"(watch\s?gs\s?pro)",
            r"(watch\s?es)",
            r"(choice\s?kids\s?watch\s?plus)",
            r"(choice\s?watch)",
            r"(choice\s?plus)",

            # Generic
            r"(watch\s?\d+[a-z]?)",
            r"(watch\s?lite)",
]
        
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                model = re.sub(r"\s+", " ", match.group(1)).strip()
                return model.title()

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