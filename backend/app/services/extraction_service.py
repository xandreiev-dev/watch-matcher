import re
from turtle import title
from xml.parsers.expat import model

from matplotlib import text


from app.core.constants import COLOR_MAP, COMMON_BRANDS, MODEL_NOISE_TOKENS
from app.utils.text_normalizer import normalize_text, cleanup_model_text

class ExtractionService:
    @staticmethod
    def extract_brand(text: str, description: str = "") -> str:
        combined = normalize_text(f"{title} {description}")
        for brand in COMMON_BRANDS:
            if re.search(rf"\b{re.escape(brand)}\b", combined):
                return brand.capitalize()
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
    def extract_warranty(description: str = "") -> str:
        text = normalize_text(description)
        
        month_match = re.search(r"(\d+)\s*(месяц|месяцев|мес|month|months)", text)
        if month_match:
            return f"{month_match.group(1)} months"
        
        year_match = re.search(r"(\d+)\s*(год|года|лет|year|years)", text)
        if year_match:
            return f"{int(year_match.group(1)) * 12} months"
        
        if "гарантия" in text or "warranty" in text:
            return "Warranty mentioned"
        return ""
    
    @staticmethod
    def extract_model(title: str, brand: str) -> str:
        text = normalize_text(title)

        if brand != "Unknown":
            text = re.sub(rf"\b{re.escape(brand.lower())}\b", " ", text)

        text = cleanup_model_text(text)

        color_words = {normalize_text(key) for key in COLOR_MAP.keys()}
        tokens = []

        for token in text.split():
            if token in color_words:
                continue
            if token in MODEL_NOISE_TOKENS:
                continue
            tokens.append(token)

        model = " ".join(tokens).strip()
        return model.title() if model else ""