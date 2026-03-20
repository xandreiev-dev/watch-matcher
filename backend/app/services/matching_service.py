from rapidfuzz import fuzz


GENERIC_MODEL_TOKENS = {
    "ultra",
    "watch",
    "smart watch",
    "series",
}


class MatchingService:
    @staticmethod
    def normalize(text: str) -> str:
        return text.lower().strip()

    @staticmethod
    def clean_model(text: str) -> str:
        return text.replace("plus", "").strip()

    @staticmethod
    def match_model(extracted_brand: str, extracted_model: str, vendor_models: list[dict]) -> dict | None:
        if not extracted_model:
            return None

        extracted_model_norm = MatchingService.normalize(extracted_model)

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

            score = fuzz.token_set_ratio(
                MatchingService.clean_model(extracted_model_norm),
                MatchingService.clean_model(MatchingService.normalize(vendor_model))
            )

            if extracted_brand.lower() == "unknown":
                score -= 5

            if score > best_score:
                best_score = score
                best_match = model

        if best_score >= 85:
            fuzzy_score = min(best_score / 100, 0.99)

            return {
                "model": best_match.get("model"),
                "image_url": best_match.get("image_url"),
                "score": fuzzy_score,
                "match_type": "fuzzy"
            }

        return None