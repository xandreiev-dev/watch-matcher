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
        r"\bredmi\b",
        r"\bpoco\b",
        r"\boppo\b",
        r"\bmotorola\b",
        r"\bmoto\b",
        r"\bvivo\b",
        r"\biqoo\b",
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
        lowered = (text or "").lower()
        for normalized, aliases in cls.MATERIAL_ALIASES.items():
            if any(alias in lowered for alias in aliases):
                return normalized
        return None

    @classmethod
    def extract_connectivity(cls, text: str) -> str | None:
        lowered = (text or "").lower()

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

        if brand_lower == "amazfit":
            return cls.build_amazfit_candidates(text)

        if brand_lower == "xiaomi":
            return cls.build_xiaomi_candidates(text)

        if brand_lower == "oppo":
            return cls.build_oppo_candidates(text)

        if brand_lower == "oneplus":
            return cls.build_oneplus_candidates(text)

        if brand_lower == "vivo":
            return cls.build_vivo_candidates(text)

        if brand_lower == "motorola":
            return cls.build_motorola_candidates(text)

        if brand_lower == "honor":
            return cls.build_honor_candidates(text)

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

        # postprocess fallback: 265 forerunner -> forerunner 265
        if m := re.search(r"\b(\d+\w?)\s+(forerunner)\b", text):
            candidates.append(f"{m.group(2)} {m.group(1)}")

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

    # ---------------- AMAZFIT ----------------

    @classmethod
    def build_amazfit_candidates(cls, text: str) -> list[str]:
        candidates: list[str] = []

        amazfit_patterns = [
            r"\b(active\s+\d+\s+square)\b",
            r"\b(active\s+edge)\b",
            r"\b(active\s+\d+)\b",
            r"\b(active)\b",

            r"\b(balance\s+\d+)\b",
            r"\b(balance)\b",

            r"\b(bip\s+\d+\s+pro)\b",
            r"\b(bip\s+\d+\s+lite)\b",
            r"\b(bip\s+\d+)\b",
            r"\b(bip)\b",

            r"\b(cheetah\s+pro)\b",
            r"\b(cheetah\s+square)\b",
            r"\b(cheetah)\b",

            r"\b(falcon)\b",

            r"\b(gtr\s+\d+\s+limited edition)\b",
            r"\b(gtr\s+mini)\b",
            r"\b(gtr\s+\d+)\b",
            r"\b(gtr)\b",

            r"\b(gts\s+\d+\s+mini)\b",
            r"\b(gts\s+\d+)\b",
            r"\b(gts)\b",

            r"\b(t\s?rex\s+ultra)\b",
            r"\b(t\s?rex\s+\d+\s+pro)\b",
            r"\b(t\s?rex\s+\d+)\b",
            r"\b(t\s?rex)\b",
        ]

        for pattern in amazfit_patterns:
            if m := re.search(pattern, text):
                value = m.group(1).replace("t rex", "t-rex").replace("t  rex", "t-rex")
                candidates.append(value.strip())

        return cls.unique(candidates)

    # ---------------- XIAOMI ----------------

    @classmethod
    def build_xiaomi_candidates(cls, text: str) -> list[str]:
        candidates: list[str] = []

        patterns = [
            r"\b(mi\s+watch\s+color\s+sports)\b",
            r"\b(mi\s+watch\s+lite)\b",
            r"\b(mi\s+watch\s+revolve\s+active)\b",
            r"\b(mi\s+watch\s+revolve)\b",
            r"\b(mi\s+watch)\b",

            r"\b(poco\s+watch)\b",

            r"\b(redmi\s+watch\s+move)\b",
            r"\b(redmi\s+watch\s+\d+\s+active)\b",
            r"\b(redmi\s+watch\s+\d+\s+esim)\b",
            r"\b(redmi\s+watch\s+\d+\s+lite)\b",
            r"\b(redmi\s+watch\s+\d+)\b",
            r"\b(redmi\s+watch)\b",

            r"\b(watch\s+color\s+2)\b",
            r"\b(watch\s+color)\b",
            r"\b(watch\s+h1\s+e)\b",
            r"\b(watch\s+h1)\b",
            r"\b(watch\s+s1\s+active)\b",
            r"\b(watch\s+s1\s+pro)\b",
            r"\b(watch\s+s1)\b",
            r"\b(watch\s+s2)\b",
            r"\b(watch\s+s3)\b",
            r"\b(watch\s+s4\s+sport)\b",
            r"\b(watch\s+s4)\b",
            r"\b(watch\s+\d+\s+pro)\b",
            r"\b(watch\s+\d+)\b",
        ]

        for pattern in patterns:
            if m := re.search(pattern, text):
                candidates.append(m.group(1).strip())

        return cls.unique(candidates)

    # ---------------- OPPO ----------------

    @classmethod
    def build_oppo_candidates(cls, text: str) -> list[str]:
        candidates: list[str] = []

        patterns = [
            r"\b(watch\s+free)\b",
            r"\b(watch\s+se)\b",
            r"\b(watch\s+s)\b",
            r"\b(watch\s+x\d+\s+mini)\b",
            r"\b(watch\s+x\d+)\b",
            r"\b(watch\s+x)\b",
            r"\b(watch\s+\d+\s+pro)\b",
            r"\b(watch\s+\d+)\b",
            r"\b(watch)\b",
        ]

        for pattern in patterns:
            if m := re.search(pattern, text):
                candidates.append(m.group(1).strip())

        return cls.unique(candidates)

    # ---------------- ONEPLUS ----------------

    @classmethod
    def build_oneplus_candidates(cls, text: str) -> list[str]:
        candidates: list[str] = []

        patterns = [
            r"\b(nord\s+watch)\b",
            r"\b(watch\s+\d+r)\b",
            r"\b(watch\s+\d+\s+lite)\b",
            r"\b(watch\s+\d+)\b",
            r"\b(watch\s+lite)\b",
            r"\b(watch)\b",
        ]

        for pattern in patterns:
            if m := re.search(pattern, text):
                candidates.append(m.group(1).strip())

        return cls.unique(candidates)

    # ---------------- VIVO ----------------

    @classmethod
    def build_vivo_candidates(cls, text: str) -> list[str]:
        candidates: list[str] = []

        patterns = [
            r"\b(iqoo\s+watch\s+gt\s+\d+)\b",
            r"\b(iqoo\s+watch\s+gt)\b",
            r"\b(iqoo\s+watch)\b",
            r"\b(watch\s+gt\s+\d+)\b",
            r"\b(watch\s+gt)\b",
            r"\b(watch\s+\d+)\b",
            r"\b(watch)\b",
        ]

        for pattern in patterns:
            if m := re.search(pattern, text):
                candidates.append(m.group(1).strip())

        return cls.unique(candidates)

    # ---------------- MOTOROLA ----------------

    @classmethod
    def build_motorola_candidates(cls, text: str) -> list[str]:
        candidates: list[str] = []

        patterns = [
            r"\b(moto\s+watch\s+fit)\b",
            r"\b(moto\s+watch\s+\d+)\b",
            r"\b(moto\s+watch)\b",
        ]

        for pattern in patterns:
            if m := re.search(pattern, text):
                candidates.append(m.group(1).strip())

        return cls.unique(candidates)

    # ---------------- HONOR ----------------

    @classmethod
    def build_honor_candidates(cls, text: str) -> list[str]:
        candidates: list[str] = []

        patterns = [
            r"\b(choice\s+watch\s+\d+i)\b",
            r"\b(choice\s+watch\s+\d+\s+pro)\b",
            r"\b(choice\s+watch)\b",
            r"\b(magicwatch\s+\d+)\b",
            r"\b(watch\s+gs\s+pro)\b",
            r"\b(watch\s+gs\s+\d+)\b",
            r"\b(watch\s+fit)\b",
            r"\b(watch\s+es)\b",
            r"\b(watch\s+x\d+i)\b",
            r"\b(watch\s+x\d+)\b",
            r"\b(watch\s+\d+\s+ultra)\b",
            r"\b(watch\s+\d+\s+pro)\b",
            r"\b(watch\s+\d+)\b",
        ]

        for pattern in patterns:
            if m := re.search(pattern, text):
                candidates.append(m.group(1).strip())

        return cls.unique(candidates)