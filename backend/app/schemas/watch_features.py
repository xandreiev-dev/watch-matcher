from pydantic import BaseModel
from typing import Optional


class WatchFeatures(BaseModel):
    product_name: str
    normalized_title: str

    brand: str
    family: Optional[str] = None
    generation: Optional[str] = None
    variant: Optional[str] = None
    size_mm: Optional[int] = None

    color: Optional[str] = None
    warranty_period: Optional[str] = None

    is_accessory: bool = False
    is_multi_model: bool = False