from pydantic import BaseModel
from typing import Optional


class WatchMatchResult(BaseModel):
    match_status: str
    matched_model_id: Optional[int] = None
    matched_model_name: Optional[str] = None
    match_method: Optional[str] = None
    confidence: float = 0.0
    needs_manual_review: bool = False