import re
from app.schemas.watch_match_result import WatchMatchResult
from app.schemas.watch_features import WatchFeatures


class WatchMatcher:
    # Эти слова меняют саму модель, поэтому короткий fallback не должен склеивать
    # Watch 5 Active с обычным Watch 5 или Watch 6 Classic с обычным Watch 6.
    PROTECTED_MODEL_TOKENS_BY_BRAND = {
        "apple": {"series", "se", "ultra"},
        "samsung": {"active", "classic", "fe", "fit", "pro", "ultra"},
        "xiaomi": {"active", "lite", "mi_watch", "poco", "pro", "redmi"},
        "huawei": {"buds", "d", "fit", "gt", "kids", "pro", "se", "ultimate"},
        "honor": {"choice", "es", "fit", "gs", "magicwatch", "pro", "ultra"},
        "oppo": {"free", "lite", "se", "x"},
        "oneplus": {"lite", "nord", "r"},
        "vivo": {"gt", "iqoo"},
        "amazfit": {"active", "balance", "bip", "cheetah", "falcon", "gtr", "gts", "t_rex"},
        "garmin": {
            "approach", "crossover", "d2", "descent", "enduro", "epix",
            "fenix", "forerunner", "instinct", "lily", "marq", "pro",
            "quatix", "swim", "tactix", "venu",
            "vivoactive", "vivomove", "vivosmart",
        },
        "google": {"pixel"},
        "motorola": {"fit"},
    }

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
            return None

        candidates = [candidate for candidate in features.model_candidates or [] if candidate]
        if not candidates:
            return None

        exact_matches = []

        for candidate in candidates:
            candidate_keys = cls.build_model_key_variants(candidate)
            if not candidate_keys:
                continue

            for row in brand_rows:
                model_text = row.get("normalized_name") or row.get("model_name") or row.get("name")
                model_keys = cls.build_model_key_variants(model_text)

                if candidate_keys & model_keys and cls.is_semantically_safe_model_match(features, candidate, row):
                    exact_matches.append((row, candidate))

        unique_matches: dict[str, tuple[dict, str]] = {}
        for row, candidate in exact_matches:
            key = str(row.get("id") or row.get("model_name") or row.get("normalized_name"))
            current = unique_matches.get(key)
            if current is None or len(cls.normalize_model_key(candidate)) > len(cls.normalize_model_key(current[1])):
                unique_matches[key] = (row, candidate)

        exact_rows = [row for row, _candidate in unique_matches.values()]

        if len(exact_rows) == 1:
            return exact_rows[0]

        # если совпадений несколько — берем самую длинную нормализованную модель
        if len(exact_rows) > 1:
            exact_rows.sort(
                key=lambda x: len(cls.normalize_model_key(
                    x.get("normalized_name") or x.get("model_name") or x.get("name")
                )),
                reverse=True
            )
            return exact_rows[0]

        return None

    @classmethod
    def is_semantically_safe_model_match(
        cls,
        features: WatchFeatures,
        candidate: str | None,
        model_row: dict,
    ) -> bool:
        brand = (features.brand or "").strip().lower()
        protected_tokens = cls.PROTECTED_MODEL_TOKENS_BY_BRAND.get(brand, set())
        if not protected_tokens:
            return True

        model_text = model_row.get("normalized_name") or model_row.get("model_name") or model_row.get("name")
        source_text = " ".join(
            str(value)
            for value in [
                features.product_name,
                features.normalized_title,
                features.family,
                features.generation,
                features.variant,
                features.extracted_variant_name,
                candidate,
            ]
            if value
        )

        source_tokens = cls.extract_protected_model_tokens(source_text, brand) & protected_tokens
        if brand == "apple" and str(features.family or "").strip().lower() == "se":
            source_tokens.discard("series")
        if not source_tokens:
            return cls.generation_is_compatible(features, model_text)

        model_tokens = cls.extract_protected_model_tokens(model_text, brand) & protected_tokens
        return source_tokens.issubset(model_tokens) and cls.generation_is_compatible(features, model_text)

    @classmethod
    def generation_is_compatible(cls, features: WatchFeatures, model_text: str | None) -> bool:
        generation = str(features.generation or "").strip()
        if not generation:
            return True

        model_key = cls.normalize_model_key(model_text)
        if not model_key:
            return False

        gen_key = cls.normalize_model_key(generation)
        if not gen_key:
            return True

        model_compact = re.sub(r"[^a-z0-9]+", "", model_key)
        gen_compact = re.sub(r"[^a-z0-9]+", "", gen_key)

        if not gen_compact:
            return True

        if gen_key in model_key.split():
            return True

        if len(gen_compact) == 1 and gen_compact.isalpha():
            return bool(re.search(rf"\b{re.escape(gen_compact)}\b", model_key))

        if gen_compact.isdigit():
            return bool(re.search(rf"(?<!\d){re.escape(gen_compact)}(?!\d)", model_compact))

        return bool(re.search(rf"(?<![a-z0-9]){re.escape(gen_compact)}(?![a-z0-9])", model_compact)) or gen_compact in model_compact

    @classmethod
    def extract_protected_model_tokens(cls, text: str | None, brand: str | None = None) -> set[str]:
        normalized = cls.normalize_model_key(text)
        if not normalized:
            return set()

        compact = re.sub(r"[^a-z0-9]+", "", normalized)
        tokens: set[str] = set()

        def has_word(word: str) -> bool:
            return bool(re.search(rf"\b{re.escape(word)}\b", normalized))

        def has_small_token(word: str) -> bool:
            return has_word(word) or bool(re.search(rf"(?<=\d){re.escape(word)}\b", compact))

        long_tokens = {
            "active", "amoled", "approach", "balance", "bip", "buds", "cheetah",
            "choice", "classic", "crossover", "descent", "enduro", "epix",
            "falcon", "fenix", "fit", "forerunner", "free", "gtr", "gts",
            "instinct", "iqoo", "kids", "lily", "lite", "magicwatch", "marq",
            "music", "nord", "pixel", "poco", "quatix", "redmi", "sapphire",
            "series", "solar", "swim", "tactix", "ultra", "ultimate", "venu",
            "vivoactive", "vivomove", "vivosmart",
        }
        for token in long_tokens:
            if has_word(token) or token in compact:
                tokens.add(token)

        if re.search(r"\bt\s*rex\b", normalized) or "trex" in compact:
            tokens.add("t_rex")

        if re.search(r"\bd\s*2\b", normalized) or compact.startswith("d2"):
            tokens.add("d2")

        if re.search(r"\bmi\s+watch\b", normalized) or compact.startswith("miwatch"):
            tokens.add("mi_watch")

        if has_small_token("pro"):
            tokens.add("pro")

        if has_small_token("se") or re.search(r"watchse(?:\d|$)", compact):
            tokens.add("se")

        if has_small_token("fe") or "watchfe" in compact:
            tokens.add("fe")

        if has_word("gt") or re.search(r"\bwatch\s+gt\b", normalized) or "watchgt" in compact:
            tokens.add("gt")

        if has_word("gs") or re.search(r"\bwatch\s+gs\b", normalized) or "watchgs" in compact:
            tokens.add("gs")

        if re.search(r"\bwatch\s+d\s*\d*\b", normalized) or re.search(r"\bd\s*\d+\b", normalized) or "watchd" in compact:
            tokens.add("d")

        if re.search(r"\bwatch\s+\d+r\b", normalized) or re.search(r"watch\d+r\b", compact):
            tokens.add("r")

        return tokens

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
                return cls.select_best_variant(features, sized_rows)

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
    def select_best_variant(cls, features: WatchFeatures, rows: list[dict]) -> dict | None:
        if not rows:
            return None

        ranked = sorted(
            rows,
            key=lambda row: (
                int(row.get("quality_score") or 0)
                + cls.connectivity_match_score(features.extracted_connectivity, row.get("connectivity_type")) * 20
                + cls.material_match_score(features.extracted_material, row.get("case_material")) * 5,
                int(row.get("is_canonical") or 0),
                int(row.get("id") or 0),
            ),
            reverse=True,
        )
        return ranked[0]

    @classmethod
    def connectivity_match_score(cls, wanted: str | None, actual: str | None) -> int:
        wanted_norm = cls.normalize_variant_name(wanted)
        actual_norm = cls.normalize_variant_name(actual)

        if not wanted_norm or not actual_norm:
            return 0

        if wanted_norm == actual_norm:
            return 4

        if wanted_norm in {"lte", "cellular"}:
            return 3 if "lte" in actual_norm or "cellular" in actual_norm else 0

        if wanted_norm == "gps":
            if "lte" in actual_norm or "cellular" in actual_norm:
                return 1
            return 3 if "gps" in actual_norm else 0

        if wanted_norm in {"bluetooth", "wifi"}:
            return 3 if wanted_norm in actual_norm else 0

        return 1 if wanted_norm in actual_norm else 0

    @classmethod
    def material_match_score(cls, wanted: str | None, actual: str | None) -> int:
        wanted_norm = cls.normalize_variant_name(wanted)
        actual_norm = cls.normalize_variant_name(actual)

        if not wanted_norm or not actual_norm:
            return 0

        if wanted_norm == actual_norm:
            return 3

        return 1 if wanted_norm in actual_norm or actual_norm in wanted_norm else 0

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
            ("galaxywatch", "galaxy watch"),
            ("redmiwatch", "redmi watch"),
            ("miwatch", "mi watch"),
            ("pocowatch", "poco watch"),
            ("applewatch", "apple watch"),
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

            # watch5active / watch6classic -> watch 5 active / watch 6 classic
            step7 = re.sub(r"(?<=[a-z])(?=\d)|(?<=\d)(?=[a-z])", " ", value)
            step7 = re.sub(r"\s+", " ", step7).strip()
            expanded.add(step7)

        return {v.strip() for v in expanded if v.strip()}
