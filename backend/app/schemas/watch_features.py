from pydantic import BaseModel, Field
from typing import Optional


class WatchFeatures(BaseModel):
    product_name: str
    normalized_title: str
    brand: str = "Unknown"

    color: Optional[str] = None
    warranty_period: Optional[str] = None

    size_mm: Optional[int] = None
    all_sizes_mm: list[int] = Field(default_factory=list)

    is_accessory: bool = False
    is_multi_model: bool = False

    # старые поля пока оставляем, чтобы не ломать текущий пайплайн и preview
    family: Optional[str] = None
    generation: Optional[str] = None
    variant: Optional[str] = None

    # новое под strict matcher
    model_candidates: list[str] = Field(default_factory=list)
    extracted_material: Optional[str] = None
    extracted_connectivity: Optional[str] = None
    extracted_variant_name: Optional[str] = None