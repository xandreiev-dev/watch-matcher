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
    def extract_family_generation_variant(cls, model_name: str) -> dict:
        text = cls.normalize_text(model_name)

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
            match = re.search(rf"\b{re.escape(family)}\s+([a-z]?\d+[a-z]?|[a-z]+\d+[a-z]?|\d+[a-z]?|[a-z])\b", text)
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