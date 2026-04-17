import re
from app.schemas.watch_match_result import WatchMatchResult
from app.schemas.watch_features import WatchFeatures


class WatchMatcher:
    @classmethod
    def match(
        cls,
        features: WatchFeatures,
        models_catalog: list[dict],
        variants_catalog: list[dict],
    ) -> WatchMatchResult:
        if features.is_accessory:
            return WatchMatchResult(
                match_status="accessory_skip",
                match_method="skip_accessory",
                confidence=1.0,
                needs_manual_review=False,
            )

        if features.is_multi_model:
            return WatchMatchResult(
                match_status="ambiguous_multi_model",
                match_method="multi_model_detected",
                confidence=0.0,
                needs_manual_review=True,
            )

        if not features.brand or features.brand == "Unknown":
            return WatchMatchResult(
                match_status="unmatched",
                match_method="brand_missing",
                confidence=0.0,
                needs_manual_review=True,
            )

        model_row = cls.find_model(features, models_catalog)
        if not model_row:
            return WatchMatchResult(
                match_status="unmatched",
                match_method="model_not_found",
                confidence=0.0,
                needs_manual_review=True,
            )

        variant_row = cls.find_variant(features, model_row, variants_catalog)
        if not variant_row:
            return WatchMatchResult(
                match_status="matched",
                matched_variant_id=None,
                matched_variant_name=None,
                matched_model_id=model_row.get("id"),
                matched_model_name=model_row.get("model_name"),
                match_method="strict_model_match_variant_not_found",
                confidence=0.9,
                needs_manual_review=True,
            )

        return WatchMatchResult(
            match_status="matched",
            matched_model_id=model_row.get("id"),
            matched_model_name=model_row.get("model_name"),
            matched_variant_id=variant_row.get("id"),
            matched_variant_name=variant_row.get("variant_name"),
            match_method="strict_model_variant_match",
            confidence=1.0,
            needs_manual_review=False,
        )

    @classmethod
    def find_model(cls, features: WatchFeatures, models_catalog: list[dict]) -> dict | None:
        brand_rows = [
            row for row in models_catalog
            if cls.same_brand(features.brand, row.get("brand"))
        ]

        if not brand_rows:
            print("==== FIND_MODEL DEBUG ====")
            print("NO BRAND ROWS FOR:", features.brand)
            print("==========================")
            return None

        print("==== FIND_MODEL DEBUG ====")
        print("BRAND:", features.brand)
        print("MODEL_CANDIDATES:", features.model_candidates)

        matches: list[tuple[int, int, dict, str, set[str]]] = []

        for candidate in features.model_candidates:
            candidate_keys = cls.build_model_key_variants(candidate)
            print("CANDIDATE:", candidate)
            print("CANDIDATE_KEYS:", candidate_keys)

            candidate_norm = cls.normalize_model_key(candidate)

            for row in brand_rows:
                model_text = row.get("normalized_name") or row.get("model_name") or row.get("name") or ""
                model_keys = cls.build_model_key_variants(model_text)
                model_norm = cls.normalize_model_key(model_text)

                intersection = candidate_keys & model_keys
                if not intersection:
                    continue

                score = 0

                # 1. Полное точное совпадение — самый высокий приоритет
                if candidate_norm == model_norm:
                    score += 1000

                # 2. Совпадение по одному из ключей
                longest_key = max((len(x) for x in intersection), default=0)
                score += longest_key * 10

                # 3. Чем длиннее сама модель, тем она специфичнее
                score += len(model_norm)

                # 4. Штраф за слишком общие модели
                if model_norm in {"watch", "watch gt", "watch fit"}:
                    score -= 200

                if model_norm == "watch d":
                    score -= 100

                matches.append((score, len(model_norm), row, model_text, intersection))

        if not matches:
            print("NO MODEL MATCH FOUND")
            print("==========================")
            return None

        matches.sort(key=lambda x: (x[0], x[1]), reverse=True)

        best_score, _, best_row, best_model_text, best_intersection = matches[0]

        print("BEST MATCH:", best_model_text)
        print("BEST SCORE:", best_score)
        print("BEST INTERSECTION:", best_intersection)
        print("==========================")

        return best_row

    @classmethod
    def find_variant(
        cls,
        features: WatchFeatures,
        model_row: dict,
        variants_catalog: list[dict],
    ) -> dict | None:
        model_id = model_row.get("id")

        rows = [
            row for row in variants_catalog
            if str(row.get("model_id")) == str(model_id)
        ]

        if not rows:
            return None

        # 1. strict size match if ad has size
        if features.size_mm is not None:
            sized_rows = [
                row for row in rows
                if cls.same_size(features.size_mm, row.get("case_size_mm"))
            ]

            if len(sized_rows) == 1:
                return sized_rows[0]

            if len(sized_rows) > 1:
                strict_named = cls.find_by_variant_name(features, sized_rows)
                if strict_named:
                    return strict_named
                return None

        # 2. exact by variant_name
        strict_named = cls.find_by_variant_name(features, rows)
        if strict_named:
            return strict_named

        # 3. only one variant in DB -> safe fallback
        if len(rows) == 1:
            return rows[0]

        # 4. one variant with case_size NULL and ad has no size
        if features.size_mm is None:
            null_size_rows = [row for row in rows if row.get("case_size_mm") is None]
            if len(null_size_rows) == 1:
                return null_size_rows[0]

        return None

    @classmethod
    def find_by_variant_name(cls, features: WatchFeatures, rows: list[dict]) -> dict | None:
        if not features.extracted_variant_name:
            return None

        target = cls.normalize_variant_name(features.extracted_variant_name)
        if not target:
            return None

        matches = []
        for row in rows:
            row_name = cls.normalize_variant_name(row.get("variant_name") or row.get("name"))
            if row_name == target:
                matches.append(row)

        if len(matches) == 1:
            return matches[0]

        return None

    @classmethod
    def same_brand(cls, left: str | None, right: str | None) -> bool:
        return (left or "").strip().lower() == (right or "").strip().lower()

    @classmethod
    def same_size(cls, left: int | None, right: int | None) -> bool:
        if left is None or right is None:
            return False
        return int(left) == int(right)

    @classmethod
    def normalize_model_name(cls, value: str | None) -> str:
        if not value:
            return ""
        return " ".join(str(value).strip().lower().replace("-", " ").split())

    @classmethod
    def normalize_variant_name(cls, value: str | None) -> str:
        if not value:
            return ""
        value = str(value).strip().lower().replace("-", " ")
        value = value.replace("мм", "mm")
        return " ".join(value.split())
    
    @classmethod
    def normalize_model_key(cls, text: str | None) -> str:
        if not text:
            return ""

        text = text.lower().strip()
        text = text.replace("мм", "mm")
        text = text.replace("-", " ")
        text = text.replace(",", " ")
        text = text.replace("/", " ")
        text = re.sub(r"[()]+", " ", text)
        text = re.sub(r"\s+", " ", text).strip()
        return text

    @classmethod
    def build_model_key_variants(cls, text: str | None) -> set[str]:
        base = cls.normalize_model_key(text)
        if not base:
            return set()

        variants = {base}

        # базовые склейки/разделения
        replacements = [
            ("vivo active", "vivoactive"),
            ("vivo move", "vivomove"),
            ("vivo smart", "vivosmart"),
            ("t rex", "t-rex"),
            ("t-rex", "t rex"),
            ("gen 2", "gen2"),
            ("gen2", "gen 2"),
            ("gen 1", "gen1"),
            ("gen1", "gen 1"),
        ]

        current = list(variants)
        for value in current:
            for old, new in replacements:
                if old in value:
                    variants.add(value.replace(old, new))

        expanded = set()

        for value in variants:
            expanded.add(value)

            # family255s -> family 255s
            step1 = re.sub(
                r"\b("
                r"forerunner|fenix|epix|venu|instinct|approach|descent|quatix|tactix|"
                r"enduro|vivoactive|vivomove|vivosmart|lily|swim|marq|d2|gtr|gts|bip|pop|active|balance|falcon|cheetah|stratos|verge"
                r")(\d+[a-z]*)\b",
                r"\1 \2",
                value,
            )
            step1 = re.sub(r"\s+", " ", step1).strip()
            expanded.add(step1)

            # family 255s -> family255s
            step2 = re.sub(
                r"\b("
                r"forerunner|fenix|epix|venu|instinct|approach|descent|quatix|tactix|"
                r"enduro|vivoactive|vivomove|vivosmart|lily|swim|marq|d2|gtr|gts|bip|pop|active|balance|falcon|cheetah|stratos|verge"
                r")\s+(\d+[a-z]*)\b",
                r"\1\2",
                value,
            )
            step2 = re.sub(r"\s+", " ", step2).strip()
            expanded.add(step2)

            # epix gen 2 -> epix gen2
            step3 = re.sub(r"\bgen\s+(\d+)\b", r"gen\1", value)
            step3 = re.sub(r"\s+", " ", step3).strip()
            expanded.add(step3)

            # epix gen2 -> epix gen 2
            step4 = re.sub(r"\bgen(\d+)\b", r"gen \1", value)
            step4 = re.sub(r"\s+", " ", step4).strip()
            expanded.add(step4)

            # 3s / 7x / 2x / mk3i / mk2s оставляем как есть, но даем и раздельный вариант
            step5 = re.sub(r"\b(\d+)([a-z])\b", r"\1 \2", value)
            step5 = re.sub(r"\s+", " ", step5).strip()
            expanded.add(step5)

            # и обратную склейку: 3 s -> 3s
            step6 = re.sub(r"\b(\d+)\s+([a-z])\b", r"\1\2", value)
            step6 = re.sub(r"\s+", " ", step6).strip()
            expanded.add(step6)

        return {v.strip() for v in expanded if v.strip()}