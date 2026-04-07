import re


class WatchReferenceNormalizer:
    @classmethod
    def normalize_text(cls, text: str) -> str:
        if not text:
            return ""

        text = text.lower().strip()
        text = text.replace("мм", "mm")
        text = text.replace("-", " ")
        text = re.sub(r"\s+", " ", text)
        return text.strip()

    @classmethod
    def extract_family_generation_variant(cls, model_name: str, brand: str | None = None) -> dict:
        text = cls.normalize_text(model_name)
        brand_lower = (brand or "").lower().strip()

        if brand_lower == "apple":
            return cls.extract_apple(text)

        if brand_lower == "garmin":
            return cls.extract_garmin(text)
        
        if brand_lower == "samsung":
            return cls.extract_samsung(text)
        
        if brand_lower == "huawei":
            print("GOING TO HUAWEI EXTRACT")
            return cls.extract_huawei(text)

        return {
            "family": None,
            "generation": None,
            "variant": None,
        }

    @classmethod
    def extract_garmin(cls, text: str) -> dict:
        families = [
            "forerunner",
            "fenix",
            "enduro",
            "epix",
            "instinct",
            "venu",
            "vivoactive",
            "vivomove",
            "tactix",
            "marq",
            "descent",
            "quatix",
            "approach",
            "lily",
        ]

        family = None
        for item in families:
            if re.search(rf"\b{re.escape(item)}\b", text):
                family = item
                break

        generation = None
        if family:
            match = re.search(
                rf"\b{re.escape(family)}\s+([a-z]?\d+[a-z]?|[a-z]+\d+[a-z]?|\d+[a-z]?|[a-z])\b",
                text,
            )
            if match:
                generation = match.group(1).upper()

        found_variants = []

        if re.search(r"\bsapphire\s+solar\b", text):
            found_variants.append("Sapphire Solar")
            text = re.sub(r"\bsapphire\s+solar\b", " ", text)

        if re.search(r"\bamoled\s+sapphire\b", text):
            found_variants.append("AMOLED Sapphire")
            text = re.sub(r"\bamoled\s+sapphire\b", " ", text)

        if re.search(r"\bsolar\b", text):
            found_variants.append("Solar")

        if re.search(r"\bsapphire\b", text):
            found_variants.append("Sapphire")

        if re.search(r"\bamoled\b", text):
            found_variants.append("AMOLED")

        if re.search(r"\bpro\b", text):
            found_variants.append("Pro")

        if re.search(r"\bmusic\b", text):
            found_variants.append("Music")

        if re.search(r"\bballistics\b", text):
            found_variants.append("Ballistics")

        if re.search(r"\btactical\b", text):
            found_variants.append("Tactical")

        if re.search(r"\bactive\b", text):
            found_variants.append("Active")

        if re.search(r"\btitanium\b", text):
            found_variants.append("Titanium")

        unique_variants = []
        for item in found_variants:
            if item not in unique_variants:
                unique_variants.append(item)

        variant = " ".join(unique_variants) if unique_variants else None

        return {
            "family": family.title() if family else None,
            "generation": generation,
            "variant": variant,
        }

    @classmethod
    def extract_apple(cls, text: str) -> dict:
        family = None
        generation = None

        # Ultra
        if re.search(r"\bultra\b", text):
            family = "Ultra"
            match = re.search(r"\bultra\s*(\d{1,2})\b", text)
            if match:
                generation = match.group(1)

        # SE
        elif re.search(r"\bse\b", text):
            family = "SE"
            match = re.search(r"\bse\s*(\d{1,2})\b", text)
            if match:
                generation = match.group(1)

        # Series 11
        elif re.search(r"\bseries\s*(\d{1,2})\b", text):
            family = "Series"
            match = re.search(r"\bseries\s*(\d{1,2})\b", text)
            if match:
                generation = match.group(1)

        # S11
        elif re.search(r"\bs(\d{1,2})\b", text):
            family = "Series"
            match = re.search(r"\bs(\d{1,2})\b", text)
            if match:
                generation = match.group(1)

        # Watch 11
        elif re.search(r"\bwatch\s+(\d{1,2})\b", text):
            family = "Series"
            match = re.search(r"\bwatch\s+(\d{1,2})\b", text)
            if match:
                generation = match.group(1)

        found_variants = []

        if re.search(r"\baluminium\b", text) or re.search(r"\baluminum\b", text):
            found_variants.append("Aluminum")

        if re.search(r"\btitanium\b", text):
            found_variants.append("Titanium")

        if re.search(r"\bstainless steel\b", text):
            found_variants.append("Stainless Steel")

        if re.search(r"\bceramic\b", text):
            found_variants.append("Ceramic")

        if re.search(r"\bnike\b", text):
            found_variants.append("Nike")

        if re.search(r"\bhermes\b", text):
            found_variants.append("Hermes")

        if re.search(r"\bsport\b", text):
            found_variants.append("Sport")

        unique_variants = []
        for item in found_variants:
            if item not in unique_variants:
                unique_variants.append(item)

        variant = " ".join(unique_variants) if unique_variants else None

        return {
            "family": family,
            "generation": generation,
            "variant": variant,
        }
    
    @classmethod
    def extract_samsung(cls, text: str) -> dict:
        family = None
        generation = None

        # Galaxy Fit
        if re.search(r"\bfit\b", text):
            family = "Fit"
            match = re.search(r"\bfit\s*(\d{1,2})\b", text)
            if match:
                generation = match.group(1)

        # Galaxy Watch Active
        elif re.search(r"\bactive\b", text):
            family = "Active"
            match = re.search(r"\bactive\s*(\d{1,2})\b", text)
            if match:
                generation = match.group(1)

        # Базовая линейка Galaxy Watch
        elif re.search(r"\bwatch\b", text) or re.search(r"\bwatch\d+\b", text):
            family = "Watch"

            # watch 7
            match = re.search(r"\bwatch\s*(\d{1,2})\b", text)
            if match:
                generation = match.group(1)
            else:
                # watch7
                match = re.search(r"\bwatch(\d{1,2})\b", text)
                if match:
                    generation = match.group(1)

        found_variants = []

        if re.search(r"\bclassic\b", text):
            found_variants.append("Classic")

        if re.search(r"\bultra\b", text):
            found_variants.append("Ultra")

        if re.search(r"\bpro\b", text):
            found_variants.append("Pro")

        if re.search(r"\bfe\b", text):
            found_variants.append("FE")

        unique_variants = []
        for item in found_variants:
            if item not in unique_variants:
                unique_variants.append(item)

        variant = " ".join(unique_variants) if unique_variants else None

        # ВАЖНО:
        # если это Watch Ultra / Watch FE / Watch Pro / Watch Classic без поколения,
        # family всё равно должно быть Watch, variant должен сохраниться как есть
        return {
            "family": family,
            "generation": generation,
            "variant": variant,
        }
    
    @classmethod
    def extract_huawei(cls, text: str) -> dict:
        
        family = None
        generation = None

        # Watch D / D2
        m = re.search(r"\bwatch\s+d\s*(\d+)?\b", text)
        if m:
            family = "D"
            if m.group(1):
                generation = m.group(1)

        # Watch Fit / Fit 3 / Fit 4 Pro
        elif re.search(r"\bwatch\s+fit\b", text) or re.search(r"\bfit\b", text):
            family = "Fit"
            m = re.search(r"\b(?:watch\s+)?fit\s*(\d+)\b", text)
            if m:
                generation = m.group(1)

        # Watch GT / GT 5 / GT 6
        elif re.search(r"\bwatch\s+gt\b", text) or re.search(r"\bgt\b", text):
            family = "GT"
            m = re.search(r"\b(?:watch\s+)?gt\s*(\d+)\b", text)
            if m:
                generation = m.group(1)

        # Band
        elif re.search(r"\bband\b", text):
            family = "Band"
            m = re.search(r"\bband\s*(\d+)\b", text)
            if m:
                generation = m.group(1)

        # Kids
        elif re.search(r"\bkids\b", text):
            family = "Kids"
            m = re.search(r"\bkids\s*(?:watch\s*)?(\d+)\b", text)
            if m:
                generation = m.group(1)

        # Regular Watch 3 / 4 / 5
        elif re.search(r"\bwatch\b", text):
            family = "Watch"
            m = re.search(r"\bwatch\s*(\d+)\b", text)
            if m:
                generation = m.group(1)

        found_variants = []

        if re.search(r"\bultimate\b", text):
            found_variants.append("Ultimate")
        if re.search(r"\bpro\b", text):
            found_variants.append("Pro")
        if re.search(r"\bclassic\b", text):
            found_variants.append("Classic")
        if re.search(r"\bactive\b", text):
            found_variants.append("Active")
        if re.search(r"\belite\b", text):
            found_variants.append("Elite")
        if re.search(r"\bceramic\b", text):
            found_variants.append("Ceramic")
        if re.search(r"\btitanium\b", text):
            found_variants.append("Titanium")
        if re.search(r"\bstainless steel\b", text):
            found_variants.append("Stainless Steel")

        unique = []
        for v in found_variants:
            if v not in unique:
                unique.append(v)

        variant = " ".join(unique) if unique else None

        return {
            "family": family,
            "generation": generation,
            "variant": variant,
        }
    