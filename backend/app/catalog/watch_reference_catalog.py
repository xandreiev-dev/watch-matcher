from app.repositories.watch_reference_repository import WatchReferenceRepository
from app.normalizers.watch_reference_normalizer import WatchReferenceNormalizer


class WatchReferenceCatalog:
    @classmethod
    def load_models(cls, brand: str | None = None) -> list[dict]:
        if brand:
            rows = WatchReferenceRepository.fetch_models_by_brand(brand)
        else:
            rows = WatchReferenceRepository.fetch_all_models()

        result = []
        for row in rows:
            parsed = WatchReferenceNormalizer.extract_family_generation_variant(
                row.get("model_name", ""),
                row.get("brand"),
            )

            result.append(
                {
                    "id": row.get("id"),
                    "brand": row.get("brand"),
                    "model_name": row.get("model_name"),
                    "normalized_name": row.get("normalized_name"),
                    "case_size_mm": row.get("case_size_mm"),
                    "family": parsed.get("family"),
                    "generation": parsed.get("generation"),
                    "variant": parsed.get("variant"),
                }
            )

        return result