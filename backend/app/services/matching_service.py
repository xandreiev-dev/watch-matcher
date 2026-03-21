import re

from rapidfuzz import fuzz


GENERIC_MODEL_TOKENS = {
    "ultra",
    "watch",
    "smart watch",
    "series",
}

DISALLOWED_COMBINATIONS = [
    ("band", "watch"),
    ("watch", "band"),
]

BAD_MODEL_KEYWORDS = [
    "ремешок",
    "браслет",
    "strap",
    "band for",
]



class MatchingService:
    @staticmethod
    def normalize(text: str) -> str:
        text = text.lower().strip().replace(",", "").replace(".", "")
        text = text.replace("-", " ").replace("_", " ")

        text = re.sub(r"([a-zа-я])\s+(\d)", r"\1\2", text)
        text = re.sub(r"(\d)\s+([a-zа-я])", r"\1\2", text)

        text = re.sub(r"\s+", " ", text).strip()
        return text
    
    @staticmethod
    def is_invalid_pair(extracted_model: str, vendor_model: str) -> bool:
        em = extracted_model.lower()
        vm = vendor_model.lower()

        for a, b in DISALLOWED_COMBINATIONS:
            if a in em and b in vm:
                return True
            if b in em and a in vm:
                return True

        return False

    @staticmethod
    def clean_model(text: str) -> str:
        return text.replace("plus", "").strip()

    @staticmethod
    def match_model(extracted_brand: str, extracted_model: str, vendor_models: list[dict]) -> dict | None:
        if not extracted_model:
            return None
        
        extracted_model_norm = MatchingService.normalize(extracted_model)

        if any(word in extracted_model_norm for word in BAD_MODEL_KEYWORDS):
            return None

        if extracted_brand.lower() == "unknown" and extracted_model_norm in GENERIC_MODEL_TOKENS:
            return None

        candidates = [
            m for m in vendor_models
            if MatchingService.normalize(m.get("brand", "")) == MatchingService.normalize(extracted_brand)
        ]

        if not candidates:
            candidates = vendor_models

        # EXACT MATCH
        for model in candidates:
            vendor_model = model.get("model", "")
            if MatchingService.is_invalid_pair(extracted_model_norm, vendor_model):
                continue
            if MatchingService.normalize(vendor_model) == extracted_model_norm:
                return {
                    "model": model.get("model"),
                    "image_url": model.get("image_url"),
                    "score": 1.0,
                    "match_type": "exact"
                }

        # CONTAINS MATCH
        for model in candidates:
            vendor_model_norm = MatchingService.normalize(model.get("model", ""))
            if MatchingService.is_invalid_pair(extracted_model_norm, vendor_model_norm):
                continue
            if extracted_model_norm in vendor_model_norm:
                return {
                    "model": model.get("model"),
                    "image_url": model.get("image_url"),
                    "score": 0.95,
                    "match_type": "contains"
                }

        # FUZZY MATCH
        best_score = 0
        best_match = None

        for model in candidates:
            vendor_model = model.get("model", "")
            if MatchingService.is_invalid_pair(extracted_model_norm, vendor_model):
                continue
            score = fuzz.token_set_ratio(
                MatchingService.clean_model(extracted_model_norm),
                MatchingService.clean_model(MatchingService.normalize(vendor_model))
            )

            if extracted_brand.lower() == "unknown":
                score -= 5

            if score > best_score:
                best_score = score
                best_match = model

        if best_match and best_match.get("model", "").lower() == "watch":
            return None

        if best_score >= 85:
            fuzzy_score = min(best_score / 100, 0.99)

            return {
                "model": best_match.get("model"),
                "image_url": best_match.get("image_url"),
                "score": fuzzy_score,
                "match_type": "fuzzy"
            }

        return None