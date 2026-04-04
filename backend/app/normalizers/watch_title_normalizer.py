import re


class WatchTitleNormalizer:
    @classmethod
    def normalize(cls, text: str) -> str:
        if not text:
            return ""

        text = str(text).replace("\n", " ").replace("\r", " ").strip().lower()

        text = text.replace("мм", "mm")
        text = re.sub(r"(\d)\s*mm\b", r"\1mm", text)

        text = re.sub(r"[|]+", " / ", text)
        text = re.sub(r"\s+", " ", text)

        return text.strip()