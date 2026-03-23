import re


BAD_MODEL_KEYWORDS = [
    "ремешок",
    "браслет",
    "strap",
    "band for",
    "loop",
    "case",
    "защитное стекло",
    "стекло",
    "зарядка",
    "charger",
    "clip",
    "клипса",
]

NOISE_WORDS = {
    "mm", "lte", "wifi", "gps", "bluetooth", "cellular",
    "new", "новые", "новый", "оригинал", "original", "global", "eu",
    "black", "white", "silver", "gray", "grey", "green", "pink",
    "purple", "blue", "beige", "gold", "rose", "midnight",
    "starlight", "jet", "slate", "natural", "titanium", "aluminum",
    "aluminium", "sport", "loop", "case", "rostest",
    "ростест", "доставка", "гарантия", "проверка", "запечатанные",
    "смарт", "смарт-часы", "умные", "часы", "watches",
    "s/m", "m/l", "sm", "ml",
    "2024", "2025", "2026"
}


class MatchingService:
    """
    Service responsible for matching extracted models with vendor catalog.

    Core idea:
    - Normalize text
    - Build structured signatures (brand, family, generation, variant)
    - Perform strict signature comparison instead of fuzzy matching
    """
    @staticmethod
    def normalize(text: str) -> str:
        """
        Normalizes raw text:
        - lowercase
        - remove punctuation
        - split letters and digits (watch5 → watch 5)
        - unify spacing

        This ensures consistent tokenization for matching.
        """
        if not text:
            return ""

        text = text.lower().strip()
        text = text.replace(",", " ").replace(".", " ")
        text = text.replace("-", " ").replace("_", " ")
        text = text.replace("/", " ")
        text = text.replace("«", " ").replace("»", " ")
        text = text.replace("(", " ").replace(")", " ")
        text = text.replace("2r", "2r")
        text = text.replace("magicwatch", "magic watch")
        text = text.replace("watchfit", "watch fit")
        text = text.replace("whatch", "watch")
        text = text.replace("motorola moto", "moto")

        # watch5 -> watch 5, se3 -> se 3, s11 -> s 11, watch8 -> watch 8
        text = re.sub(r"([a-zа-я]+)(\d+)", r"\1 \2", text)
        text = re.sub(r"(\d+)([a-zа-я]+)", r"\1 \2", text)

        text = re.sub(r"\s+", " ", text).strip()
        return text

    @staticmethod
    def has_bad_keywords(text: str) -> bool:
        normalized = MatchingService.normalize(text)
        return any(word in normalized for word in BAD_MODEL_KEYWORDS)

    @staticmethod
    def clean_tokens(text: str) -> list[str]:
        """
        Normalizes raw text:
        - lowercase
        - remove punctuation
        - split letters and digits (watch5 → watch 5)
        - unify spacing

        This ensures consistent tokenization for matching.
        """
        normalized = MatchingService.normalize(text)
        tokens = []

        for token in normalized.split():
            if token in NOISE_WORDS:
                continue
            if token in {"40", "41", "42", "44", "45", "46", "47", "49"}:
                continue
            if re.fullmatch(r"\d{2,4}", token) and token in {"2024", "2025", "2026"}:
                continue
            if re.fullmatch(r"sm\s*r?\d+", token):
                continue
            if re.fullmatch(r"[a-z]{1,3}\d+[a-z0-9\-]*", token):
                # Артикулы типа r910, b29, kan-b19 и т.д.
                continue
            tokens.append(token)

        return tokens

    @staticmethod
    def get_brand_candidates(extracted_brand: str, vendor_models: list[dict]) -> list[dict]:
        brand_norm = MatchingService.normalize(extracted_brand)
        return [
            model for model in vendor_models
            if MatchingService.normalize(model.get("brand", "")) == brand_norm
        ]

    @staticmethod
    def parse_apple_signature(text: str) -> tuple | None:
        tokens = MatchingService.clean_tokens(text)
        joined = " ".join(tokens)

        if MatchingService.has_bad_keywords(joined):
            return None

        match = re.search(r"\bultra\s+(\d{1,2})\b", joined)
        if match:
            return ("apple", "ultra", match.group(1))

        if "ultra" in tokens:
            return ("apple", "ultra", None)

        match = re.search(r"\bse\s+(\d{1,2})\b", joined)
        if match:
            return ("apple", "se", match.group(1))

        if "se" in tokens:
            return ("apple", "se", None)

        match = re.search(r"\bseries\s+(\d{1,2})\b", joined)
        if match:
            return ("apple", "series", match.group(1))

        match = re.search(r"\bwatch\s+(\d{1,2})\b", joined)
        if match:
            return ("apple", "series", match.group(1))

        match = re.search(r"\bs\s+(\d{1,2})\b", joined)
        if match:
            return ("apple", "series", match.group(1))

        return None

    @staticmethod
    def parse_samsung_signature(text: str) -> tuple | None:
        tokens = MatchingService.clean_tokens(text)
        joined = " ".join(tokens)

        if MatchingService.has_bad_keywords(joined):
            return None

        match = re.search(r"\bactive\s+(\d{1,2})\b", joined)
        if match:
            return ("samsung", "active", match.group(1), None)

        if "fit" in tokens:
            match = re.search(r"\bfit\s+(\d{1,2})\b", joined)
            generation = match.group(1) if match else None
            return ("samsung", "fit", generation, None)

        if "ultra" in tokens:
            match = re.search(r"\bwatch\s+(\d{1,2})\b", joined)
            generation = match.group(1) if match else None
            return ("samsung", "watch", generation, "ultra")

        if "classic" in tokens:
            match = re.search(r"\bwatch\s+(\d{1,2})\b", joined)
            generation = match.group(1) if match else None
            return ("samsung", "watch", generation, "classic")

        if "pro" in tokens:
            match = re.search(r"\bwatch\s+(\d{1,2})\b", joined)
            generation = match.group(1) if match else None
            return ("samsung", "watch", generation, "pro")

        if "fe" in tokens:
            return ("samsung", "watch", None, "fe")

        match = re.search(r"\bwatch\s+(\d{1,2})\b", joined)
        if match:
            return ("samsung", "watch", match.group(1), "base")

        if "watch" in tokens:
            return ("samsung", "watch", None, "base")

        return None

    @staticmethod
    def parse_huawei_signature(text: str) -> tuple | None:
        tokens = MatchingService.clean_tokens(text)
        joined = " ".join(tokens)

        if MatchingService.has_bad_keywords(joined):
            return None

        # Band 9 / Band 10
        if "band" in tokens:
            match = re.search(r"\bband\s+(\d{1,2})\b", joined)
            generation = match.group(1) if match else None
            return ("huawei", "band", generation, None)

        # Watch Fit / Fit 2 / Fit 3 / Fit 4 / Fit 4 Pro / Fit SE
        if "fit" in tokens:
            match = re.search(r"\bfit\s+(\d{1,2})\b", joined)
            generation = match.group(1) if match else None

            if "pro" in tokens:
                return ("huawei", "fit", generation, "pro")
            if "se" in tokens:
                return ("huawei", "fit", generation, "se")

            return ("huawei", "fit", generation, "base")

        # Kids 4 Plus / Kids 4 Pro
        if "kids" in tokens:
            match = re.search(r"\bkids\s+(\d{1,2})\b", joined)
            generation = match.group(1) if match else None

            if "pro" in tokens:
                return ("huawei", "kids", generation, "pro")
            if "plus" in tokens:
                return ("huawei", "kids", generation, "plus")

            return ("huawei", "kids", generation, "base")

        # GT 5 / GT 5 Pro / GT 6 / GT 6 Pro
        if "gt" in tokens:
            match = re.search(r"\bgt\s+(\d{1,2})\b", joined)
            generation = match.group(1) if match else None
            variant = "pro" if "pro" in tokens else "base"
            return ("huawei", "gt", generation, variant)

        # Watch D / D2
        if "watch" in tokens and "d" in tokens:
            match = re.search(r"\bd\s+(\d{1,2})\b", joined)
            generation = match.group(1) if match else None
            return ("huawei", "watch_d", generation, None)

        # Watch Ultimate
        if "ultimate" in tokens:
            return ("huawei", "ultimate", None, None)

        # Watch 4 / Watch 4 Pro / Watch 5 / Watch 5 Pro
        if "watch" in tokens:
            match = re.search(r"\bwatch\s+(\d{1,2})\b", joined)
            generation = match.group(1) if match else None

            if "pro" in tokens:
                return ("huawei", "watch", generation, "pro")

            return ("huawei", "watch", generation, "base")

        return None

    @staticmethod
    def parse_honor_signature(text: str) -> tuple | None:
        tokens = MatchingService.clean_tokens(text)
        joined = " ".join(tokens)

        if MatchingService.has_bad_keywords(joined):
            return None

        if "choice" in tokens and "kids" in tokens:
            return ("honor", "choice_kids", None, None)

        if "choice" in tokens and "watch" in tokens:
            match = re.search(r"\bwatch\s+(\d{1,2}[a-z]?)\b", joined)
            generation = match.group(1) if match else None
            return ("honor", "choice_watch", generation, None)

        if "choice" in tokens:
            return ("honor", "choice", None, None)

        if "magic" in tokens and "watch" in tokens:
            match = re.search(r"\bwatch\s+(\d{1,2})\b", joined)
            generation = match.group(1) if match else None
            return ("honor", "magicwatch", generation, None)

        if "watch" in tokens and "es" in tokens:
            return ("honor", "watch_es", None, None)

        if "watch" in tokens and "gs" in tokens and "pro" in tokens:
            return ("honor", "watch_gs_pro", None, None)

        if "watch" in tokens:
            match = re.search(r"\bwatch\s+(\d{1,2})\b", joined)
            generation = match.group(1) if match else None
            if generation is None:
                return None
            return ("honor", "watch", generation, None)

        return None
    
    @staticmethod
    def parse_motorola_signature(text: str) -> tuple | None:
        tokens = MatchingService.clean_tokens(text)
        joined = " ".join(tokens)

        if MatchingService.has_bad_keywords(joined):
            return None

        if ("moto" in tokens or "motorola" in tokens) and "watch" in tokens and "fit" in tokens:
            return ("motorola", "watch", "fit", None)

        if ("moto" in tokens or "motorola" in tokens) and "watch" in tokens and "100" in tokens:
            return ("motorola", "watch", "100", None)

        if ("moto" in tokens or "motorola" in tokens) and "watch" in tokens and "40" in tokens:
            return ("motorola", "watch", "40", None)

        if ("moto" in tokens or "motorola" in tokens) and "watch" in tokens:
            return ("motorola", "watch", None, None)

        return None

    @staticmethod
    def parse_generic_signature(brand: str, text: str) -> tuple | None:
        tokens = MatchingService.clean_tokens(text)
        joined = " ".join(tokens)

        if MatchingService.has_bad_keywords(joined):
            return None

        if "watch" in tokens:
            # Watch 2R
            match = re.search(r"\bwatch\s+(\d+[a-z])\b", joined)
            if match:
                return (brand.lower(), "watch", match.group(1), None)

            # Watch 2
            match = re.search(r"\bwatch\s+(\d{1,2})\b", joined)
            if match:
                return (brand.lower(), "watch", match.group(1), None)

            if "lite" in tokens:
                return (brand.lower(), "watch_lite", None, None)

            return (brand.lower(), "watch", None, None)

        if "band" in tokens:
            match = re.search(r"\bband\s+(\d{1,2}[a-z]?)\b", joined)
            if match:
                return (brand.lower(), "band", match.group(1), None)

        return None

    @staticmethod
    def build_signature(brand: str, text: str) -> tuple | None:
        """
        Builds structured signature depending on brand.

        Signature format varies by brand but typically includes:
        (brand, family, generation, variant)

        Example:
        ("samsung", "watch", "6", "classic")

        This is the core abstraction used for matching.
        """
        brand_norm = MatchingService.normalize(brand)

        if brand_norm == "apple":
            return MatchingService.parse_apple_signature(text)
        if brand_norm == "samsung":
            return MatchingService.parse_samsung_signature(text)
        if brand_norm == "huawei":
            return MatchingService.parse_huawei_signature(text)
        if brand_norm == "honor":
            return MatchingService.parse_honor_signature(text)
        if brand_norm == "motorola":
            return MatchingService.parse_motorola_signature(text)

        return MatchingService.parse_generic_signature(brand, text)

    @staticmethod
    def exact_normalized_match(extracted_model: str, candidates: list[dict]) -> dict | None:
        extracted_norm = MatchingService.normalize(extracted_model)

        for candidate in candidates:
            vendor_norm = MatchingService.normalize(candidate.get("model", ""))
            if extracted_norm and extracted_norm == vendor_norm:
                return {
                    "model": candidate.get("model"),
                    "image_url": candidate.get("image_url"),
                    "score": 1.0,
                    "match_type": "exact",
                }

        return None

    @staticmethod
    def signature_match(brand: str, extracted_model: str, candidates: list[dict]) -> dict | None:
        """
        Matches extracted model against vendor models using signature comparison.

        Strategy:
        1. Build signature for extracted model
        2. Compare with vendor signatures
        3. Prefer exact signature match
        4. Allow limited fallback only for weak (generic) signatures

        Important:
        - Does NOT allow incorrect variant matching (e.g. Pro vs base)
        - Does NOT allow incorrect generation matching

        This avoids false positives typical for fuzzy matching.
        """
        extracted_signature = MatchingService.build_signature(brand, extracted_model)

        if not extracted_signature:
            return None

        exact_candidates = []
        family_candidates = []

        for candidate in candidates:
            vendor_model = candidate.get("model", "")
            vendor_signature = MatchingService.build_signature(brand, vendor_model)

            if not vendor_signature:
                continue

            if vendor_signature == extracted_signature:
                exact_candidates.append(candidate)
                continue

            if len(extracted_signature) >= 4 and len(vendor_signature) >= 4:
                extracted_variant = extracted_signature[3]
                vendor_variant = vendor_signature[3]

                if extracted_variant not in (None, "base") and vendor_variant != extracted_variant:
                    continue

            if len(extracted_signature) >= 3 and len(vendor_signature) >= 3:
                extracted_generation = extracted_signature[2]
                vendor_generation = vendor_signature[2]

                if extracted_generation is not None and vendor_generation is not None:
                    if extracted_generation != vendor_generation:
                        continue

            if (
                len(vendor_signature) >= 2
                and len(extracted_signature) >= 2
                and vendor_signature[0] == extracted_signature[0]
                and vendor_signature[1] == extracted_signature[1]
            ):
                family_candidates.append((vendor_signature, candidate))

        if exact_candidates:
            candidate = exact_candidates[0]
            return {
                "model": candidate.get("model"),
                "image_url": candidate.get("image_url"),
                "score": 1.0,
                "match_type": "signature_exact",
            }

        # Only allow family fallback when extracted signature is weak
        # Example: "Galaxy Watch" without generation
        # Family fallback allowed only for truly generic extracted signatures
        if family_candidates:
            filtered = []

            for vendor_signature, candidate in family_candidates:
                # if extracted has a strong variant, vendor must have the same variant
                if len(extracted_signature) >= 4 and len(vendor_signature) >= 4:
                    extracted_variant = extracted_signature[3]
                    vendor_variant = vendor_signature[3]

                    if extracted_variant not in (None, "base") and vendor_variant != extracted_variant:
                        continue

                # if extracted has a concrete generation, vendor must have same generation
                if len(extracted_signature) >= 3 and len(vendor_signature) >= 3:
                    extracted_generation = extracted_signature[2]
                    vendor_generation = vendor_signature[2]

                    if extracted_generation is not None and vendor_generation is not None and extracted_generation != vendor_generation:
                        continue

                filtered.append((vendor_signature, candidate))

            # allow fallback only when extracted model is weak / generic
            weak_signature = False
            if len(extracted_signature) >= 4:
                weak_signature = extracted_signature[2] is None and extracted_signature[3] in (None, "base")
            elif len(extracted_signature) >= 3:
                weak_signature = extracted_signature[2] is None

            if weak_signature and filtered:
                candidate = filtered[0][1]
                return {
                    "model": candidate.get("model"),
                    "image_url": candidate.get("image_url"),
                    "score": 0.9,
                    "match_type": "signature_family",
                }
            
        return None

    @staticmethod
    def match_model(extracted_brand: str, extracted_model: str, vendor_models: list[dict]) -> dict | None:
        """
        Main entry point for model matching.

        Pipeline:
        1. Validate inputs
        2. Filter vendor models by brand
        3. Try exact normalized match
        4. Try signature-based match

        Returns:
        - matched model + metadata
        - or None if no reliable match found

        Important:
        - Skips matching for Unknown brand
        - Skips accessories
        """
        if not extracted_model:
            return None

        if not extracted_brand or MatchingService.normalize(extracted_brand) == "unknown":
            return None

        if MatchingService.has_bad_keywords(extracted_model):
            return None

        candidates = MatchingService.get_brand_candidates(extracted_brand, vendor_models)

        if not candidates:
            return None

        # 1. exact normalized
        exact_match = MatchingService.exact_normalized_match(extracted_model, candidates)
        if exact_match:
            return exact_match

        # 2. signature-based match
        signature_match = MatchingService.signature_match(extracted_brand, extracted_model, candidates)
        if signature_match:
            return signature_match

        return None