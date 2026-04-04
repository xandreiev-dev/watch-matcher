import re
from typing import Optional


class SizeExtractor:
    PATTERNS = [
        r"\b(3[89]|4[0-9]|5[0-9])\s?mm\b",
        r"\b(3[89]|4[0-9]|5[0-9])\s?мм\b",
    ]

    @classmethod
    def extract_first_size_mm(cls, text: str) -> Optional[int]:
        if not text:
            return None

        lowered = text.lower()

        for pattern in cls.PATTERNS:
            match = re.search(pattern, lowered)
            if match:
                return int(match.group(1))

        return None

    @classmethod
    def extract_all_sizes_mm(cls, text: str) -> list[int]:
        if not text:
            return []

        lowered = text.lower()
        sizes: list[int] = []

        for pattern in cls.PATTERNS:
            for match in re.finditer(pattern, lowered):
                size = int(match.group(1))
                if size not in sizes:
                    sizes.append(size)

        return sizes