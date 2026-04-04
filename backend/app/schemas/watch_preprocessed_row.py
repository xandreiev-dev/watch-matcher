from pydantic import BaseModel
from typing import Optional


class WatchPreprocessedRow(BaseModel):
    product_name: str
    description: str = ""
    product_url: str
    image_url: Optional[str] = None

    brand: str = "Unknown"
    brand_from_url: Optional[str] = None
    brand_match: Optional[bool] = None

    article: Optional[str] = None
    shop_rating: Optional[float] = None
    price: Optional[float] = None

    normalized_title: str

    size_mm: Optional[int] = None
    all_sizes_mm: list[int] = []
    is_accessory: bool = False
    is_multi_model: bool = False
    