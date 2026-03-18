from pydantic import BaseModel
from typing import Any

class PreviewResponse(BaseModel):
    filename: str
    total_rows: int
    columns: list[str]
    preview: list[dict[str, Any]]

    