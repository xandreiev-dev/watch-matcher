from email.mime import text
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
            return cls.extract_huawei(text)
        
        if brand_lower == "amazfit":
            return cls.extract_amazfit(text)
        
        if brand_lower == "google":
            return cls.extract_google(text)

        if brand_lower == "pixel":
            return cls.extract_google(text)
        
        if brand_lower == "honor":
            return cls.extract_honor(text)

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
            "vivosmart",
            "tactix",
            "marq",
            "descent",
            "quatix",
            "approach",
            "lily",
            "swim",
            "d2",
        ]

        family = None
        for item in families:
            if re.search(rf"\b{re.escape(item)}\b", text):
                family = item
                break

        generation = None

        if family == "marq":
            m = re.search(r"\bmarq\s+(adventurer|athlete|aviator|captain|commander|golfer)\b", text)
            if m:
                role = m.group(1).title()
                g = re.search(r"\bgen\s*(\d+)\b", text)
                generation = f"{role} Gen {g.group(1)}" if g else role

        elif family == "d2":
            m = re.search(r"\bd2\s+(air\s*x10|mach\s*1(?:\s*pro)?)\b", text)
            if m:
                generation = re.sub(r"\s+", " ", m.group(1)).title()

        elif family == "descent":
            m = re.search(r"\bdescent\s+(mk\d+i?|g\d|x\d+i?)\b", text)
            if m:
                generation = m.group(1).upper()

        elif family == "approach":
            m = re.search(r"\bapproach\s+([sgx]?\d+[a-z]?)\b", text)
            if m:
                generation = m.group(1).upper()

        elif family == "quatix":
            m = re.search(r"\bquatix\s+(\d+[a-z]?)\b", text)
            if m:
                generation = m.group(1).upper()

        elif family == "tactix":
            m = re.search(r"\btactix\s+(\d+[a-z]?)\b", text)
            if m:
                generation = m.group(1).upper()

        elif family == "fenix":
            if re.search(r"\bfenix\s+e\b", text):
                generation = "E"
            else:
                m = re.search(r"\bfenix\s+(\d+[a-z]?)\b", text)
                if m:
                    generation = m.group(1).upper()

        elif family == "epix":
            if re.search(r"\bgen\s*2\b", text):
                generation = "Gen 2"

        elif family == "instinct":
            if re.search(r"\bcrossover\b", text):
                generation = "Crossover"
            elif re.search(r"\binstinct\s+e\b", text):
                generation = "E"
            else:
                m = re.search(r"\binstinct\s+(\d+[a-z]?)\b", text)
                if m:
                    generation = m.group(1).upper()

        elif family == "forerunner":
            m = re.search(r"\bforerunner\s+(\d+[a-z]*|x1)\b", text)
            if m:
                generation = m.group(1).upper()

        elif family == "venu":
            if re.search(r"\bvenu\s+sq\b", text):
                generation = "SQ"
            elif re.search(r"\bvenu\s+x1\b", text):
                generation = "X1"
            else:
                m = re.search(r"\bvenu\s+(\d+[a-z]?)\b", text)
                if m:
                    generation = m.group(1).upper()

        elif family == "vivoactive":
            m = re.search(r"\bvivoactive\s+(\d+[a-z]?)\b", text)
            if m:
                generation = m.group(1).upper()

        elif family == "vivomove":
            m = re.search(r"\bvivomove\s+(hr|luxe|sport|style|trend)\b", text)
            if m:
                generation = m.group(1).title()

        elif family == "vivosmart":
            m = re.search(r"\bvivosmart\s+(\d+[a-z]?)\b", text)
            if m:
                generation = m.group(1).upper()

        elif family == "lily":
            m = re.search(r"\blily\s+(\d+)\b", text)
            if m:
                generation = m.group(1)

        elif family == "swim":
            m = re.search(r"\bswim\s+(\d+)\b", text)
            if m:
                generation = m.group(1)

        elif family == "enduro":
            m = re.search(r"\benduro\s+(\d+)\b", text)
            if m:
                generation = m.group(1)

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

        if re.search(r"\bclassic\b", text):
            found_variants.append("Classic")

        if re.search(r"\bactive\b", text) and family == "lily":
            found_variants.append("Active")

        if re.search(r"\bsport\b", text) and family in {"lily", "vivomove"}:
            found_variants.append("Sport")

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
        found_variants = []

        text = text.replace("magicwatch", "magic watch")

        if re.search(r"\bwatch\s+d\b", text) or re.search(r"\bwatch\s+d\s*\d+\b", text):
            family = "D"
            m = re.search(r"\bwatch\s+d\s*(\d+)\b", text)
            if m:
                generation = m.group(1)

        elif re.search(r"\bwatch\s+fit\b", text) or re.search(r"\bfit\b", text):
            family = "Fit"
            m = re.search(r"\b(?:watch\s+)?fit\s*(\d+)\b", text)
            if m:
                generation = m.group(1)

            if re.search(r"\bmini\b", text):
                found_variants.append("Mini")
            if re.search(r"\bspecial edition\b", text):
                found_variants.append("Special Edition")
            if re.search(r"\belegant\b", text):
                found_variants.append("Elegant")
            if re.search(r"\bpro\b", text):
                found_variants.append("Pro")

        elif re.search(r"\bwatch\s+gt\b", text) or re.search(r"\bgt\b", text):
            family = "GT"
            m = re.search(r"\b(?:watch\s+)?gt\s*(\d+)\b", text)
            if m:
                generation = m.group(1)

            if re.search(r"\b2e\b", text):
                found_variants.append("2e")
            if re.search(r"\bpro\b", text):
                found_variants.append("Pro")
            if re.search(r"\bse\b", text):
                found_variants.append("SE")
            if re.search(r"\brunner\b", text):
                found_variants.append("Runner")
                m2 = re.search(r"\brunner\s*(\d+)\b", text)
                if m2:
                    found_variants.append(m2.group(1))
            if re.search(r"\bcyber\b", text):
                found_variants.append("Cyber")
            if re.search(r"\bporsche design\b", text):
                found_variants.append("Porsche Design")

        elif re.search(r"\bwatch\s+ultimate\b", text):
            family = "Watch"
            found_variants.append("Ultimate")
            m = re.search(r"\bultimate\s*(\d+)\b", text)
            if m:
                generation = m.group(1)
            if re.search(r"\bdesign\b", text):
                found_variants.append("Design")

        elif re.search(r"\bwatch\s+buds\b", text):
            family = "Watch"
            found_variants.append("Buds")

        elif re.search(r"\bwatch\s+magic\b", text):
            family = "Watch"
            found_variants.append("Magic")

        elif re.search(r"\bchildren'?s\s+watch\b", text) or re.search(r"\bkids\b", text):
            family = "Kids"
            m = re.search(r"\b(?:children'?s\s+watch|kids(?:\s+watch)?)\s*(\d+[a-z]?)\b", text)
            if m:
                generation = m.group(1).upper()

        elif re.search(r"\bwatch\b", text):
            family = "Watch"
            m = re.search(r"\bwatch\s*(\d+)\b", text)
            if m:
                generation = m.group(1)
            if re.search(r"\bclassic\b", text):
                found_variants.append("Classic")
            if re.search(r"\bpro\b", text):
                found_variants.append("Pro")

        unique = []
        for item in found_variants:
            if item not in unique:
                unique.append(item)

        variant = " ".join(unique) if unique else None

        return {
            "family": family,
            "generation": generation,
            "variant": variant,
        }
    
    @classmethod
    def extract_amazfit(cls, text: str) -> dict:
        family = None
        generation = None
        found_variants = []

        normalized = text.lower().strip()
        normalized = normalized.replace("-", " ")
        normalized = re.sub(r"\s+", " ", normalized).strip()

        # Active / Active 2 / Active 2 Square / Active Edge
        if re.search(r"\bactive\b", normalized):
            family = "Active"

            match = re.search(r"\bactive\s*(\d{1,2})\b", normalized)
            if match:
                generation = match.group(1)

            if re.search(r"\bsquare\b", normalized):
                found_variants.append("Square")

            if re.search(r"\bedge\b", normalized):
                found_variants.append("Edge")

        # Balance / Balance 2
        elif re.search(r"\bbalance\b", normalized):
            family = "Balance"

            match = re.search(r"\bbalance\s*(\d{1,2})\b", normalized)
            if match:
                generation = match.group(1)

        # Bip 6
        elif re.search(r"\bbip\b", normalized):
            family = "Bip"

            match = re.search(r"\bbip\s*(\d{1,2})\b", normalized)
            if match:
                generation = match.group(1)

        # Cheetah / Cheetah Pro / Cheetah Square / Cheetah Round
        elif re.search(r"\bcheetah\b", normalized):
            family = "Cheetah"

            if re.search(r"\bpro\b", normalized):
                found_variants.append("Pro")

            if re.search(r"\bsquare\b", normalized):
                found_variants.append("Square")

            if re.search(r"\bround\b", normalized):
                found_variants.append("Round")

        # Falcon
        elif re.search(r"\bfalcon\b", normalized):
            family = "Falcon"

        # GTR / GTR 4 Limited Edition / GTR Mini
        elif re.search(r"\bgtr\b", normalized):
            family = "GTR"

            match = re.search(r"\bgtr\s*(\d{1,2})\b", normalized)
            if match:
                generation = match.group(1)

            if re.search(r"\blimited edition\b", normalized):
                found_variants.append("Limited Edition")

            if re.search(r"\bmini\b", normalized):
                found_variants.append("Mini")

        # GTS / GTS 4 Mini
        elif re.search(r"\bgts\b", normalized):
            family = "GTS"

            match = re.search(r"\bgts\s*(\d{1,2})\b", normalized)
            if match:
                generation = match.group(1)

            if re.search(r"\bmini\b", normalized):
                found_variants.append("Mini")

        # T-Rex / T-Rex 3 / T-Rex 3 Pro / T-Rex Ultra
        elif re.search(r"\bt rex\b", normalized):
            family = "T-Rex"

            match = re.search(r"\bt rex\s*(\d{1,2})\b", normalized)
            if match:
                generation = match.group(1)

            if re.search(r"\bpro\b", normalized):
                found_variants.append("Pro")

            if re.search(r"\bultra\b", normalized):
                found_variants.append("Ultra")

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
    def extract_google(cls, text: str) -> dict:
        family = None
        generation = None
        variant = None

        if re.search(r"\bpixel\s+watch\b", text):
            family = "Watch"
            m = re.search(r"\bpixel\s+watch\s*(\d{1,2})\b", text)
            if m:
                generation = m.group(1)

        return {
            "family": family,
            "generation": generation,
            "variant": variant,
        }
    

    @classmethod
    def extract_honor(cls, text: str) -> dict:
        family = None
        generation = None
        found_variants = []

        text = text.replace("magicwatch", "magic watch")

        if re.search(r"\bchoice\s+watch\b", text):
            family = "Choice"
            m = re.search(r"\bchoice\s+watch\s*(\d+)\b", text)
            if m:
                generation = m.group(1)

            if re.search(r"\b2i\b", text):
                generation = "2i"

            if re.search(r"\bpro\b", text):
                found_variants.append("Pro")

        elif re.search(r"\bmagic\s+watch\b", text):
            family = "MagicWatch"
            m = re.search(r"\bmagic\s+watch\s*(\d+)\b", text)
            if m:
                generation = m.group(1)

        elif re.search(r"\bwatch\s+gs\b", text):
            family = "GS"
            m = re.search(r"\bwatch\s+gs\s*(\d+)\b", text)
            if m:
                generation = m.group(1)

            if re.search(r"\bpro\b", text):
                found_variants.append("Pro")

        elif re.search(r"\bwatch\s+fit\b", text):
            family = "Fit"

        elif re.search(r"\bwatch\s+es\b", text):
            family = "ES"

        elif re.search(r"\bwatch\s+x\b", text) or re.search(r"\bwatch\s+x5i\b", text):
            family = "X"

            if re.search(r"\bx5i\b", text):
                generation = "5i"
            else:
                m = re.search(r"\bwatch\s+x\s*(\d+)\b", text)
                if m:
                    generation = m.group(1)
                else:
                    m2 = re.search(r"\bwatch\s+x(\d+)\b", text)
                    if m2:
                        generation = m2.group(1)

        elif re.search(r"\bwatch\b", text):
            family = "Watch"
            m = re.search(r"\bwatch\s*(\d+)\b", text)
            if m:
                generation = m.group(1)

            if re.search(r"\bpro\b", text):
                found_variants.append("Pro")

            if re.search(r"\bultra\b", text):
                found_variants.append("Ultra")

        unique = []
        for item in found_variants:
            if item not in unique:
                unique.append(item)

        variant = " ".join(unique) if unique else None

        return {
            "family": family,
            "generation": generation,
            "variant": variant,
        }
                