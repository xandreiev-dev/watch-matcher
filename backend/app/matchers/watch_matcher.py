from app.schemas.watch_match_result import WatchMatchResult
from app.schemas.watch_features import WatchFeatures


class WatchMatcher:
    @classmethod
    def match(cls, features: WatchFeatures, catalog: list[dict]) -> WatchMatchResult:
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

        brand_rows = [
            row for row in catalog
            if (row.get("brand") or "").lower() == features.brand.lower()
        ]

        if not brand_rows:
            return WatchMatchResult(
                match_status="unmatched",
                match_method="brand_not_found_in_catalog",
                confidence=0.0,
                needs_manual_review=True,
            )

        exact = cls.find_exact_match(features, brand_rows)
        if exact:
            return WatchMatchResult(
                match_status="matched",
                matched_model_id=exact.get("id"),
                matched_model_name=exact.get("model_name"),
                match_method="exact_family_generation_variant_size",
                confidence=1.0,
                needs_manual_review=False,
            )

        soft = cls.find_soft_match(features, brand_rows)
        if soft:
            return WatchMatchResult(
                match_status="matched",
                matched_model_id=soft.get("id"),
                matched_model_name=soft.get("model_name"),
                match_method="family_generation_variant_or_size",
                confidence=0.85,
                needs_manual_review=True,
            )

        family_variant = cls.find_family_variant_match(features, brand_rows)
        if family_variant:
            return WatchMatchResult(
                match_status="matched",
                matched_model_id=family_variant.get("id"),
                matched_model_name=family_variant.get("model_name"),
                match_method="family_variant_with_optional_size",
                confidence=0.82,
                needs_manual_review=True,
            )

        return WatchMatchResult(
            match_status="unmatched",
            match_method="no_reference_match",
            confidence=0.0,
            needs_manual_review=True,
        )

    @classmethod
    def find_exact_match(cls, features: WatchFeatures, rows: list[dict]) -> dict | None:
        if not features.family or not features.generation:
            return None

        for row in rows:
            if not row.get("family") or not row.get("generation"):
                continue
            if not cls.same_family(features.family, row.get("family")):
                continue
            if not cls.same_generation(features.generation, row.get("generation")):
                continue
            if not cls.same_variant(features.variant, row.get("variant")):
                continue
            if not cls.same_size(features.size_mm, row.get("case_size_mm")):
                continue
            return row
        return None

    @classmethod
    def find_soft_match(cls, features: WatchFeatures, rows: list[dict]) -> dict | None:
        if not features.family or not features.generation:
            return None

        candidates = []

        for row in rows:
            row_family = row.get("family")
            row_generation = row.get("generation")
            row_variant = row.get("variant")
            row_size = row.get("case_size_mm")

            if not row_family or not row_generation:
                continue

            if not cls.same_family(features.family, row_family):
                continue

            if not cls.same_generation(features.generation, row_generation):
                continue

            # ВАЖНО:
            # если у объявления variant указан, то soft-match без совпадения variant запрещаем
            if features.variant:
                if not cls.same_variant(features.variant, row_variant):
                    continue

            score = 0

            if cls.same_variant(features.variant, row_variant):
                score += 2

            if cls.same_size(features.size_mm, row_size):
                score += 2
            elif features.size_mm is None or row_size is None:
                score += 1

            candidates.append((score, row))

        if not candidates:
            return None

        candidates.sort(key=lambda x: x[0], reverse=True)
        best_score, best_row = candidates[0]

        if best_score >= 2:
            return best_row

        return None
    
    @classmethod
    def find_family_variant_match(cls, features: WatchFeatures, rows: list[dict]) -> dict | None:
        if not features.family or not features.variant:
            return None

        candidates = []

        for row in rows:
            if not row.get("family"):
                continue

            if not cls.same_family(features.family, row.get("family")):
                continue

            if not cls.same_variant(features.variant, row.get("variant")):
                continue

            score = 0

            # size — сильный сигнал
            if cls.same_size(features.size_mm, row.get("case_size_mm")):
                score += 2
            elif features.size_mm is None or row.get("case_size_mm") is None:
                score += 1

            candidates.append((score, row))

        if not candidates:
            return None

        candidates.sort(key=lambda x: x[0], reverse=True)
        best_score, best_row = candidates[0]

        # если есть size match — отлично
        if best_score >= 2:
            return best_row

        # если кандидат ровно один и family+variant уникальны — тоже можно брать
        if len(candidates) == 1:
            return best_row

        return None

    @classmethod
    def find_family_generation_match(cls, features: WatchFeatures, rows: list[dict]) -> dict | None:
        if not features.family or not features.generation:
            return None

        for row in rows:
            if not row.get("family") or not row.get("generation"):
                continue
            if cls.same_family(features.family, row.get("family")) and cls.same_generation(
                features.generation, row.get("generation")
            ):
                return row
        return None

    @classmethod
    def same_family(cls, left: str | None, right: str | None) -> bool:
        return (left or "").strip().lower() == (right or "").strip().lower()

    @classmethod
    def same_generation(cls, left: str | None, right: str | None) -> bool:
        return (left or "").strip().upper() == (right or "").strip().upper()

    @classmethod
    def same_variant(cls, left: str | None, right: str | None) -> bool:
        left_norm = (left or "").strip().lower()
        right_norm = (right or "").strip().lower()

        if left_norm == right_norm:
            return True

        if not left_norm and not right_norm:
            return True

        return False

    @classmethod
    def same_size(cls, left: int | None, right: int | None) -> bool:
        if left is None and right is None:
            return True
        if left is None or right is None:
            return False
        return int(left) == int(right)