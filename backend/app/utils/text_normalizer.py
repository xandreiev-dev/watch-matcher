import re

def normalize_text(text: str) -> str:
    if not text:
        return ""
    
    text = str(text).lower().strip()
    text = text.replace('ё', 'е')
    text = text.replace('/', ' ')
    text = text.replace('_', ' ')
    text = re.sub(r"[^\w\s\-]", ' ', text)
    text = re.sub(r"\s+", ' ', text)

    return text.strip()

def cleanup_model_text(text: str) -> str:
    if not text:
        return ""
    
    text = normalize_text(text)

    text = re.sub(r"\baw\s+(\d+)\b", r"aw\1", text)
    text = re.sub(r"\b\d{2,3}mm\b", ' ', text)
    text = re.sub(r"\b(s/m|m/l|sm|ml)\b", ' ', text)
    text = re.sub(r"\b(lte|wifi|gps|nfc)\b", ' ', text)
    text = re.sub(r"\b(2024|2025|2026)\b", ' ', text)
    text = re.sub(r"\s+", ' ', text)

    return text.strip()