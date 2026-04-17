from pydantic import BaseModel
from typing import Optional


class WatchMatchResult(BaseModel):
    match_status: str
    matched_model_id: int | None = None
    matched_model_name: str | None = None
    matched_variant_id: int | None = None
    matched_variant_name: str | None = None
    match_method: str
    confidence: float
    needs_manual_review: bool