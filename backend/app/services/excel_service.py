from io import BytesIO

import pandas as pd
from fastapi import UploadFile

from app.core.constants import REQUIRED_COLUMNS, PREVIEW_ROWS_COUNT

class ExcelService:
    @staticmethod
    async def read_excel_file(file: UploadFile) -> pd.DataFrame:
        contents = await file.read()
        dataframe = pd.read_excel(BytesIO(contents))
        return dataframe
    
    @staticmethod
    def validate_columns(dataframe: pd.DataFrame) -> None:
        missing_columns = [col for col in REQUIRED_COLUMNS if col not in dataframe.columns]
        if missing_columns:
            raise ValueError(f"Missing required columns: {', '.join(missing_columns)}")
        
    @staticmethod
    def build_preview(dataframe: pd.DataFrame) -> list[dict]:
        preview_df = dataframe.head(PREVIEW_ROWS_COUNT).copy()
        preview_df = preview_df.fillna("")
        return preview_df.to_dict(orient="records")
        