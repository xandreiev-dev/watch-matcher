import re


class ModelCandidateBuilder:
    NOISE_PATTERNS = [
        r"\bновые\b",
        r"\bновый\b",
        r"\bсмарт ?часы\b",
        r"\bумные ?часы\b",
        r"\bsmart ?watch\b",
        r"\bwatches\b",
        r"\bчасы\b",
        r"\bhuawei\b",
        r"\bsamsung\b",
        r"\bapple\b",
        r"\bgarmin\b",
        r"\bgoogle\b",
        r"\bamazfit\b",
        r"\boneplus\b",
        r"\bhonor\b",
        r"\bxiaomi\b",
        r"\boppo\b",
        r"\bmotorola\b",
        r"\bрусский язык\b",
        r"\bрусский\b",
        r"\bрф\b",
        r"\bв наличии\b",
        r"\bоригинал\b",
        r"\bоригинальные\b",
        r"\bгарантия\b",
    ]

    MATERIAL_ALIASES = {
        "aluminum": ["aluminum", "aluminium", "алюминий", "алюминиевый"],
        "titanium": ["titanium", "титан", "титановый"],
        "stainless steel": ["stainless steel", "нержавеющая сталь", "сталь", "steel"],
        "ceramic": ["ceramic", "керамика", "ceramic edition"],
    }

    CONNECTIVITY_ALIASES = {
        "lte": ["lte", "cellular", "сотовая связь", "4g", "esim"],
        "wifi": ["wifi", "wi-fi", "bluetooth", "gps"],
    }

    @classmethod
    def normalize_text(cls, text: str) -> str:
        if not text:
            return ""

        text = text.lower().strip()
        text = text.replace("мм", "mm")
        text = text.replace("-", " ")
        text = text.replace("/", " ")
        text = re.sub(r"[(),]+", " ", text)

        for pattern in cls.NOISE_PATTERNS:
            text = re.sub(pattern, " ", text)

        text = re.sub(r"\s+", " ", text).strip()
        return text

    @classmethod
    def extract_material(cls, text: str) -> str | None:
        lowered = text.lower()
        for normalized, aliases in cls.MATERIAL_ALIASES.items():
            if any(alias in lowered for alias in aliases):
                return normalized
        return None

    @classmethod
    def extract_connectivity(cls, text: str) -> str | None:
        lowered = text.lower()

        if any(alias in lowered for alias in cls.CONNECTIVITY_ALIASES["lte"]):
            return "lte"

        if any(alias in lowered for alias in cls.CONNECTIVITY_ALIASES["wifi"]):
            return "wifi"

        return None

    @classmethod
    def build(cls, brand: str, normalized_title: str) -> list[str]:
        brand_lower = (brand or "").lower().strip()
        text = cls.normalize_text(normalized_title)

        if not text:
            return []

        if brand_lower == "huawei":
            return cls.build_huawei_candidates(text)

        if brand_lower == "samsung":
            return cls.build_samsung_candidates(text)

        if brand_lower == "apple":
            return cls.build_apple_candidates(text)

        if brand_lower == "garmin":
            return cls.build_garmin_candidates(text)

        if brand_lower == "google":
            return cls.build_google_candidates(text)

        return []

    @classmethod
    def unique(cls, values: list[str]) -> list[str]:
        result: list[str] = []
        for item in values:
            item = re.sub(r"\s+", " ", item).strip().lower()
            if item and item not in result:
                result.append(item)
        return result

    # ---------------- HUAWEI ----------------

    @classmethod
    def build_huawei_candidates(cls, text: str) -> list[str]:
        candidates: list[str] = []

        if m := re.search(r"\bwatch\s+d\s*(\d+)\b", text):
            candidates.append(f"watch d{m.group(1)}")

        elif re.search(r"\bwatch\s+d\b", text):
            candidates.append("watch d")

        if m := re.search(r"\bwatch\s+fit\s*(\d+)\s*(pro)?\b", text):
            number = m.group(1)
            pro = m.group(2)
            if pro:
                candidates.append(f"watch fit {number} pro")
            candidates.append(f"watch fit {number}")

        if m := re.search(r"\bwatch\s+gt\s*(\d+)\s*(pro)?\b", text):
            number = m.group(1)
            pro = m.group(2)
            if pro:
                candidates.append(f"watch gt {number} pro")
            candidates.append(f"watch gt {number}")

        if m := re.search(r"\bwatch\s+(\d+)\s*(pro|classic|ultimate)?\b", text):
            number = m.group(1)
            tail = m.group(2)
            if tail:
                candidates.append(f"watch {number} {tail}")
            candidates.append(f"watch {number}")

        return cls.unique(candidates)

    # ---------------- SAMSUNG ----------------

    @classmethod
    def build_samsung_candidates(cls, text: str) -> list[str]:
        candidates: list[str] = []

        if m := re.search(r"\bwatch\s*(\d+)\s*(classic|ultra|pro|fe)?\b", text):
            number = m.group(1)
            tail = m.group(2)
            if tail:
                candidates.append(f"galaxy watch {number} {tail}")
            candidates.append(f"galaxy watch {number}")

        elif m := re.search(r"\bwatch(\d+)\s*(classic|ultra|pro|fe)?\b", text):
            number = m.group(1)
            tail = m.group(2)
            if tail:
                candidates.append(f"galaxy watch {number} {tail}")
            candidates.append(f"galaxy watch {number}")

        if m := re.search(r"\bwatch\s+(ultra|fe)\b", text):
            candidates.append(f"galaxy watch {m.group(1)}")

        if m := re.search(r"\bfit\s*(\d+)\b", text):
            candidates.append(f"galaxy fit {m.group(1)}")

        if m := re.search(r"\bactive\s*(\d+)?\b", text):
            if m.group(1):
                candidates.append(f"galaxy watch active {m.group(1)}")
            candidates.append("galaxy watch active")

        return cls.unique(candidates)

    # ---------------- APPLE ----------------

    @classmethod
    def build_apple_candidates(cls, text: str) -> list[str]:
        candidates: list[str] = []

        if m := re.search(r"\bultra\s*(\d+)?\b", text):
            if m.group(1):
                candidates.append(f"watch ultra {m.group(1)}")
            candidates.append("watch ultra")

        if m := re.search(r"\bse\s*(\d+)?\b", text):
            if m.group(1):
                candidates.append(f"watch se {m.group(1)}")
            candidates.append("watch se")

        if m := re.search(r"\bseries\s*(\d+)\b", text):
            candidates.append(f"watch series {m.group(1)}")

        if m := re.search(r"\bs(\d{1,2})\b", text):
            candidates.append(f"watch series {m.group(1)}")

        if m := re.search(r"\bwatch\s+(\d{1,2})\b", text):
            candidates.append(f"watch series {m.group(1)}")

        return cls.unique(candidates)

    # ---------------- GARMIN ----------------

    @classmethod
    def build_garmin_candidates(cls, text: str) -> list[str]:
        candidates: list[str] = []

        patterns = [
            r"\b(fenix\s+\d+\w?)\b",
            r"\b(forerunner\s+\d+\w?)\b",
            r"\b(instinct\s+\d+\w?)\b",
            r"\b(epix\s+\d+\w?)\b",
            r"\b(venu\s+\d+\w?)\b",
            r"\b(vivoactive\s+\d+\w?)\b",
            r"\b(approach\s+[a-z]\d+)\b",
            r"\b(enduro\s+\d+\w?)\b",
            r"\b(tactix\s+\d+\w?)\b",
            r"\b(quatix\s+\d+\w?)\b",
            r"\b(descent\s+[a-z]\d+\w*)\b",
            r"\b(marq\s+[a-z0-9 ]+)\b",
        ]

        for pattern in patterns:
            if m := re.search(pattern, text):
                candidates.append(m.group(1).strip())

        return cls.unique(candidates)

    # ---------------- GOOGLE ----------------

    @classmethod
    def build_google_candidates(cls, text: str) -> list[str]:
        candidates: list[str] = []

        if m := re.search(r"\bpixel\s+watch\s*(\d+)?\b", text):
            if m.group(1):
                candidates.append(f"pixel watch {m.group(1)}")
            candidates.append("pixel watch")

        return cls.unique(candidates)